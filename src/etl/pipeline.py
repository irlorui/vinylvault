"""ETL pipeline orchestrator: fetch → enrich → transform → upsert."""

import logging
from datetime import datetime, timezone

import spotipy

from src.backend.spotify import fetch_all_tracks_enriched, get_playlist_name
from src.etl.db import DuckDBClient
from src.etl.enricher import enrich_genres
from src.etl.transformer import transform_tracks

logger = logging.getLogger(__name__)

_EPOCH = datetime(1970, 1, 1, tzinfo=timezone.utc)


def _parse_added_at(ts: str | None) -> datetime | None:
    """Parse a Spotify added_at ISO timestamp to a timezone-aware datetime."""
    if not ts:
        return None
    try:
        return datetime.fromisoformat(ts.replace("Z", "+00:00"))
    except ValueError:
        return None


def _fetch_max_added_at(sp: spotipy.Spotify, playlist_uri: str) -> datetime | None:
    """Return the most recent added_at across all items in a playlist.

    Uses a lightweight fields-only fetch (no track metadata) to minimise API cost.
    """
    result = sp.playlist_tracks(
        playlist_uri,
        fields="items(added_at),next",
        limit=100,
    )
    max_dt: datetime | None = None
    while result:
        for item in result.get("items", []):
            dt = _parse_added_at(item.get("added_at"))
            if dt and (max_dt is None or dt > max_dt):
                max_dt = dt
        result = sp.next(result) if result.get("next") else None
    return max_dt


def _log_etl_run(
    db: DuckDBClient,
    playlist_uri: str,
    status: str,
    tracks_processed: int,
    error: str | None,
    started_at: datetime,
    finished_at: datetime,
    last_track_added_at: datetime,
) -> None:
    """Insert one row into metadata.etl_log for a playlist run."""
    cols = (
        "playlist_id, status, tracks_processed, error, "
        "started_at, finished_at, last_track_added_at"
    )
    db.connection.execute(
        f"INSERT INTO metadata.etl_log ({cols}) VALUES (?, ?, ?, ?, ?, ?, ?)",  # noqa: E501
        [
            playlist_uri,
            status,
            tracks_processed,
            error,
            started_at,
            finished_at,
            last_track_added_at.replace(tzinfo=None),
        ],
    )


def run_etl(
    playlist_ids: list[str],
    sp: spotipy.Spotify,
    db: DuckDBClient,
    status: dict,
) -> None:
    """Run the full ETL pipeline for a list of playlist URIs.

    Mutates `status` in-place so GET /api/etl/status reflects live progress.
    """
    db.run_migrations()

    run_started_at = datetime.now(timezone.utc)
    status.update(
        {
            "status": "running",
            "playlists_processed": 0,
            "tracks_upserted": 0,
            "error": None,
            "started_at": run_started_at,
            "finished_at": None,
        }
    )
    try:
        all_tracks: list[dict] = []
        unique_artist_ids: set[str] = set()
        # Tracks per playlist (ordered) — used after all tracks are upserted to
        # populate playlist_tracks with integer FKs.
        playlist_track_map: dict[str, list[dict]] = {}

        for playlist_uri in playlist_ids:
            playlist_name = get_playlist_name(sp, playlist_uri)
            logger.info("Processing playlist: %s (%s)", playlist_name, playlist_uri)

            # --- skip check ---
            try:
                row = db.connection.execute(
                    """
                    SELECT last_track_added_at 
                    FROM metadata.etl_log
                    WHERE playlist_id = ? AND status = 'done'
                    ORDER BY finished_at DESC 
                    LIMIT 1
                    """,
                    [playlist_uri],
                ).fetchone()
                if row is not None:
                    watermark = row[0].replace(tzinfo=timezone.utc)
                    max_added_at = _fetch_max_added_at(sp, playlist_uri)
                    if max_added_at is not None and max_added_at <= watermark:
                        logger.info(
                            "Skipping %s — no new tracks since last run (%s)",
                            playlist_uri,
                            watermark.isoformat(),
                        )
                        status["playlists_processed"] += 1
                        continue
            except Exception as skip_exc:
                logger.warning("Skip check failed for %s: %s", playlist_uri, skip_exc)

            # --- fetch + upsert ---
            try:
                tracks = fetch_all_tracks_enriched(sp, playlist_uri)
                logger.info("Fetched %d tracks from %s", len(tracks), playlist_name)

                playlist_meta = sp.playlist(playlist_uri, fields="name") or {}
                db.upsert_records(
                    "playlists",
                    [
                        {
                            "playlist_uri": playlist_uri,
                            "name": playlist_meta.get("name", playlist_uri),
                            "etl_run_at": run_started_at.strftime("%Y-%m-%dT%H:%M:%S"),
                        }
                    ],
                    primary_key="playlist_uri",
                )

                playlist_track_map[playlist_uri] = tracks

                for track in tracks:
                    for artist in track.get("artists") or []:
                        if artist.get("id"):
                            unique_artist_ids.add(artist["id"])
                all_tracks.extend(tracks)

                added_ats = [_parse_added_at(t.get("added_at")) for t in tracks]
                last_track_added_at = max(
                    (dt for dt in added_ats if dt), default=_EPOCH
                )

                _log_etl_run(
                    db,
                    playlist_uri,
                    status="done",
                    tracks_processed=len(tracks),
                    error=None,
                    started_at=run_started_at,
                    finished_at=datetime.now(timezone.utc),
                    last_track_added_at=last_track_added_at,
                )
                status["playlists_processed"] += 1
                logger.info(
                    "Playlist %s: %d tracks, last added %s",
                    playlist_uri,
                    len(tracks),
                    last_track_added_at.isoformat(),
                )

            except Exception as playlist_exc:
                logger.error(
                    "Failed to process playlist %s: %s", playlist_uri, playlist_exc
                )
                _log_etl_run(
                    db,
                    playlist_uri,
                    status="error",
                    tracks_processed=0,
                    error=str(playlist_exc),
                    started_at=run_started_at,
                    finished_at=datetime.now(timezone.utc),
                    last_track_added_at=_EPOCH,
                )

        logger.info("Enriching genres for %d unique artists", len(unique_artist_ids))
        enrich_genres(sp, list(unique_artist_ids), db)

        track_rows = transform_tracks(all_tracks)
        if track_rows:
            result = db.upsert_records("tracks", track_rows, primary_key="track_uri")
            status["tracks_upserted"] = result.get("inserted", 0) + result.get(
                "updated", 0
            )
            _populate_tracks_artists(db, all_tracks)
            for playlist_uri, tracks in playlist_track_map.items():
                _replace_playlist_tracks(db, playlist_uri, tracks)

        status.update({"status": "done", "finished_at": datetime.now(timezone.utc)})
        logger.info("ETL complete: %d tracks upserted", status["tracks_upserted"])

    except Exception as exc:
        logger.error("ETL pipeline failed: %s", exc)
        status.update(
            {
                "status": "error",
                "error": str(exc),
                "finished_at": datetime.now(timezone.utc),
            }
        )


def _populate_tracks_artists(db: DuckDBClient, all_tracks: list[dict]) -> None:
    """Populate raw.tracks_artists from the full track list using integer PKs."""
    track_uris = list({t["id"] for t in all_tracks if t.get("id")})
    artist_uris = list(
        {a["id"] for t in all_tracks for a in (t.get("artists") or []) if a.get("id")}
    )
    if not track_uris or not artist_uris:
        return

    ph_t = ",".join(f"'{tid}'" for tid in track_uris)
    track_id_map: dict[str, int] = dict(
        db.connection.execute(
            f"SELECT track_uri, id FROM raw.tracks WHERE track_uri IN ({ph_t})"
        ).fetchall()
    )

    ph_a = ",".join(f"'{aid}'" for aid in artist_uris)
    artist_id_map: dict[str, int] = dict(
        db.connection.execute(
            f"SELECT artist_uri, id FROM raw.artists WHERE artist_uri IN ({ph_a})"
        ).fetchall()
    )

    seen: set[tuple[int, int]] = set()
    for track in all_tracks:
        track_int_id = track_id_map.get(track.get("id", ""))
        if track_int_id is None:
            continue
        for artist in track.get("artists") or []:
            artist_int_id = artist_id_map.get(artist.get("id", ""))
            if artist_int_id is None:
                continue
            pair = (track_int_id, artist_int_id)
            if pair not in seen:
                seen.add(pair)
                db.connection.execute(
                    "INSERT INTO raw.tracks_artists (track_id, artist_id)"
                    " VALUES (?, ?) ON CONFLICT (track_id, artist_id) DO NOTHING",
                    [track_int_id, artist_int_id],
                )
    logger.info("Populated tracks_artists: %d links", len(seen))


def _replace_playlist_tracks(
    db: DuckDBClient, playlist_uri: str, tracks: list[dict]
) -> None:
    """Delete and re-insert playlist-track links using integer PKs for both sides."""
    pl_row = db.connection.execute(
        "SELECT id FROM raw.playlists WHERE playlist_uri = ?", [playlist_uri]
    ).fetchone()
    if pl_row is None:
        logger.warning("Playlist %s not in DB, skipping playlist_tracks", playlist_uri)
        return
    playlist_int_id = pl_row[0]

    track_uris = [t["id"] for t in tracks if t.get("id")]
    if not track_uris:
        db.connection.execute(
            "DELETE FROM raw.playlist_tracks WHERE playlist_id = ?", [playlist_int_id]
        )
        return

    ph = ",".join(f"'{tid}'" for tid in set(track_uris))
    track_id_map: dict[str, int] = dict(
        db.connection.execute(
            f"SELECT track_uri, id FROM raw.tracks WHERE track_uri IN ({ph})"
        ).fetchall()
    )

    db.connection.execute(
        "DELETE FROM raw.playlist_tracks WHERE playlist_id = ?", [playlist_int_id]
    )

    seen: set[str] = set()
    for i, t in enumerate(tracks):
        tid = t.get("id")
        if not tid or tid in seen:
            continue
        seen.add(tid)
        track_int_id = track_id_map.get(tid)
        if track_int_id is None:
            continue
        db.connection.execute(
            "INSERT INTO raw.playlist_tracks (playlist_id, track_id, position)"
            " VALUES (?, ?, ?)",
            [playlist_int_id, track_int_id, i],
        )
