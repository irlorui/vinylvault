"""Artist genre enrichment: batched Spotify API calls with DuckDB caching."""

import logging
import time
from datetime import datetime, timezone

import spotipy
from spotipy.exceptions import SpotifyException

from src.etl.db import DuckDBClient

logger = logging.getLogger(__name__)

_BATCH_SIZE = 50
_MAX_RETRIES = 3
_BASE_DELAY = 1.0


def enrich_genres(
    sp: spotipy.Spotify,
    artist_uris: list[str],
    db: DuckDBClient,
) -> dict[str, list[str]]:
    """Return a mapping of artist_uri → genres, using DB cache then Spotify.

    Also populates raw.genres and raw.artists_genres for uncached artists.
    Batches uncached IDs into groups of 50 with exponential backoff on 429s.
    """
    if not artist_uris:
        return {}
    unique_ids = list(set(artist_uris))
    cached = _load_cached(db, unique_ids)
    uncached = [aid for aid in unique_ids if aid not in cached]
    fresh = _fetch_from_spotify(sp, uncached, db) if uncached else {}
    return {**cached, **fresh}


def _load_cached(db: DuckDBClient, artist_uris: list[str]) -> dict[str, list[str]]:
    """Load artist genres already stored via raw.artists_genres join."""
    if not artist_uris:
        return {}
    try:
        placeholders = ",".join(f"'{aid}'" for aid in artist_uris)
        rows = (
            db.connection.execute(
                f"SELECT a.artist_uri, g.name AS genre "
                f"FROM raw.artists a "
                f"LEFT JOIN raw.artists_genres ag ON a.id = ag.artist_uri "
                f"LEFT JOIN raw.genres g ON ag.genre_id = g.id "
                f"WHERE a.artist_uri IN ({placeholders})"  # noqa: E501
            )
            .fetchdf()
            .to_dict("records")
        )
        result: dict[str, list[str]] = {}
        for r in rows:
            aid = r["artist_uri"]
            if aid not in result:
                result[aid] = []
            if r["genre"] is not None:
                result[aid].append(r["genre"])
        return result
    except Exception:
        return {}


def _fetch_from_spotify(
    sp: spotipy.Spotify, artist_uris: list[str], db: DuckDBClient
) -> dict[str, list[str]]:
    """Fetch and cache genres for artist IDs not yet in the DB."""
    result: dict[str, list[str]] = {}
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S")
    batches = [
        artist_uris[i : i + _BATCH_SIZE]
        for i in range(0, len(artist_uris), _BATCH_SIZE)
    ]
    for batch in batches:
        artists_data = _spotify_artists_with_retry(sp, batch)
        for artist in artists_data:
            if artist is None:
                continue
            aid = artist["id"]
            genres = artist.get("genres") or []
            result[aid] = genres

            db.connection.execute(
                "INSERT INTO raw.artists (artist_uri, name, fetched_at)"
                " VALUES (?, ?, ?)"
                " ON CONFLICT (artist_uri) DO UPDATE SET"
                " name = excluded.name, fetched_at = excluded.fetched_at",
                [aid, artist.get("name", ""), now],
            )
            artist_row = db.connection.execute(
                "SELECT id FROM raw.artists WHERE artist_uri = ?", [aid]
            ).fetchone()
            if artist_row is None:
                continue
            artist_int_id = artist_row[0]

            for genre in genres:
                db.connection.execute(
                    "INSERT INTO raw.genres (name) VALUES (?)"
                    " ON CONFLICT (name) DO NOTHING",
                    [genre],
                )
                genre_row = db.connection.execute(
                    "SELECT id FROM raw.genres WHERE name = ?", [genre]
                ).fetchone()
                if genre_row is None:
                    continue
                db.connection.execute(
                    "INSERT INTO raw.artists_genres (artist_id, genre_id)"
                    " VALUES (?, ?) ON CONFLICT (artist_id, genre_id) DO NOTHING",
                    [artist_int_id, genre_row[0]],
                )
    return result


def _spotify_artists_with_retry(
    sp: spotipy.Spotify, artist_uris: list[str]
) -> list[dict]:
    """Call sp.artists() with exponential backoff on 429 rate-limit errors."""
    delay = _BASE_DELAY
    for attempt in range(_MAX_RETRIES):
        try:
            response = sp.artists(artist_uris)
            return (response or {}).get("artists") or []
        except SpotifyException as e:
            if e.http_status == 429 and attempt < _MAX_RETRIES - 1:
                retry_after = float(getattr(e, "headers", {}).get("Retry-After", delay))
                logger.warning("Spotify rate limit. Retrying in %.1fs.", retry_after)
                time.sleep(retry_after)
                delay *= 2
            else:
                raise
    return []
