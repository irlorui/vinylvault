"""ETL pipeline orchestrator: fetch → enrich → transform → upsert."""

import logging
from datetime import datetime, timezone

import spotipy
from tqdm import tqdm

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


def _fetch_max_added_at(sp: spotipy.Spotify, playlist_id: str) -> datetime | None:
    """Return the most recent added_at across all items in a playlist.

    Uses a lightweight fields-only fetch (no track metadata) to minimise API cost.
    """
    result = sp.playlist_tracks(
        playlist_id,
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
    playlist_id: str,
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
            playlist_id,
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
    """Run the full ETL pipeline for a list of playlist IDs.

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

        for playlist_id in tqdm(playlist_ids, desc="Processing playlists"):
            playlist_name = get_playlist_name(sp, playlist_id)
            logger.info("Processing playlist: %s (%s)", playlist_name, playlist_id)

            # --- skip check ---
            try:
                row = db.connection.execute(
                    """
                    SELECT last_track_added_at FROM metadata.etl_log
                    WHERE playlist_id = ? AND status = 'done'
                    ORDER BY finished_at DESC 
                    LIMIT 1
                    """,
                    [playlist_id],
                ).fetchone()
                if row is not None:
                    watermark = row[0].replace(tzinfo=timezone.utc)
                    max_added_at = _fetch_max_added_at(sp, playlist_id)
                    if max_added_at is not None and max_added_at <= watermark:
                        logger.info(
                            "Skipping playlist %s — no new tracks since last run (%s)",
                            playlist_id,
                            watermark.isoformat(),
                        )
                        status["playlists_processed"] += 1
                        continue
            except Exception as skip_exc:
                logger.warning("Skip check failed for %s: %s", playlist_id, skip_exc)

            # --- fetch + upsert ---
            try:
                tracks = fetch_all_tracks_enriched(sp, playlist_id)
                logger.info("Fetched %d tracks from %s", len(tracks), playlist_name)

                playlist_meta = sp.playlist(playlist_id, fields="name") or {}
                db.upsert_records(
                    "playlists",
                    [
                        {
                            "playlist_id": playlist_id,
                            "name": playlist_meta.get("name", playlist_id),
                        }
                    ],
                    primary_key="playlist_id",
                )

                _replace_playlist_tracks(db, playlist_id, tracks)

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
                    playlist_id,
                    status="done",
                    tracks_processed=len(tracks),
                    error=None,
                    started_at=run_started_at,
                    finished_at=datetime.now(timezone.utc),
                    last_track_added_at=last_track_added_at,
                )
                status["playlists_processed"] += 1
                logger.info(
                    "Playlist %s processed: %d tracks, last added %s",
                    playlist_id,
                    len(tracks),
                    last_track_added_at.isoformat(),
                )

            except Exception as playlist_exc:
                logger.error(
                    "Failed to process playlist %s: %s", playlist_id, playlist_exc
                )
                _log_etl_run(
                    db,
                    playlist_id,
                    status="error",
                    tracks_processed=0,
                    error=str(playlist_exc),
                    started_at=run_started_at,
                    finished_at=datetime.now(timezone.utc),
                    last_track_added_at=_EPOCH,
                )

        logger.info("Enriching genres for %d unique artists", len(unique_artist_ids))
        genres_by_artist = enrich_genres(sp, list(unique_artist_ids), db)

        track_rows = transform_tracks(all_tracks, genres_by_artist)
        if track_rows:
            result = db.upsert_records("tracks", track_rows, primary_key="track_id")
            status["tracks_upserted"] = result.get("inserted", 0) + result.get(
                "updated", 0
            )

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


def _replace_playlist_tracks(
    db: DuckDBClient, playlist_id: str, tracks: list[dict]
) -> None:
    """Delete and re-insert playlist-track associations for this playlist."""
    try:
        db.connection.execute(
            "DELETE FROM raw.playlist_tracks WHERE playlist_id = ?",
            [playlist_id],
        )
    except Exception:
        pass  # table may not exist yet on first run; insert_records creates it

    records = [
        {"playlist_id": playlist_id, "track_id": t["id"], "position": i}
        for i, t in enumerate(tracks)
        if t.get("id")
    ]
    if records:
        db.insert_records("playlist_tracks", records)
