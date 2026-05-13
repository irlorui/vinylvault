"""Artist genre enrichment: batched Spotify API calls with DuckDB caching."""

import json
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
    artist_ids: list[str],
    db: DuckDBClient,
) -> dict[str, list[str]]:
    """Return a mapping of artist_id → genres, using DB cache then Spotify.

    Batches uncached artist IDs into groups of 50, with exponential backoff
    for rate-limit (429) responses.
    """
    if not artist_ids:
        return {}
    unique_ids = list(set(artist_ids))
    cached = _load_cached(db, unique_ids)
    uncached = [aid for aid in unique_ids if aid not in cached]
    fresh = _fetch_from_spotify(sp, uncached, db) if uncached else {}
    return {**cached, **fresh}


def _load_cached(db: DuckDBClient, artist_ids: list[str]) -> dict[str, list[str]]:
    """Load artist genres already stored in raw.artists."""
    if not artist_ids:
        return {}
    try:
        placeholders = ",".join(f"'{aid}'" for aid in artist_ids)
        rows = (
            db.connection.execute(
                f"SELECT artist_id, genres FROM raw.artists WHERE artist_id IN ({placeholders})"  # noqa: E501
            )
            .fetchdf()
            .to_dict("records")
        )
        return {r["artist_id"]: json.loads(r["genres"]) for r in rows}
    except Exception:
        return {}


def _fetch_from_spotify(
    sp: spotipy.Spotify, artist_ids: list[str], db: DuckDBClient
) -> dict[str, list[str]]:
    """Fetch and cache genres for artist IDs not yet in the DB."""
    result: dict[str, list[str]] = {}
    batches = [
        artist_ids[i : i + _BATCH_SIZE] for i in range(0, len(artist_ids), _BATCH_SIZE)
    ]
    for batch in batches:
        artists_data = _spotify_artists_with_retry(sp, batch)
        records = []
        for artist in artists_data:
            if artist is None:
                continue
            aid = artist["id"]
            genres = artist.get("genres") or []
            result[aid] = genres
            records.append(
                {
                    "artist_id": aid,
                    "name": artist.get("name", ""),
                    "genres": json.dumps(genres),
                    "fetched_at": datetime.now(timezone.utc).strftime(
                        "%Y-%m-%dT%H:%M:%S"
                    ),
                }
            )
        if records:
            db.upsert_records("artists", records, primary_key="artist_id")
    return result


def _spotify_artists_with_retry(
    sp: spotipy.Spotify, artist_ids: list[str]
) -> list[dict]:
    """Call sp.artists() with exponential backoff on 429 rate-limit errors."""
    delay = _BASE_DELAY
    for attempt in range(_MAX_RETRIES):
        try:
            response = sp.artists(artist_ids)
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
