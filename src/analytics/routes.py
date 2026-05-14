"""FastAPI router for analytics endpoints."""

from fastapi import APIRouter, Request
from starlette.concurrency import run_in_threadpool

from src.analytics.models import (
    ArtistInfo,
    DBPlaylistInfo,
    GenreBucket,
    SongsResponse,
    StatsResponse,
    TrackRow,
    YearBucket,
)
from src.analytics.queries import get_db_playlists, get_stats, get_tracks
from src.etl.db import get_db_client

router = APIRouter(prefix="/api/analytics", tags=["analytics"])


@router.get("/songs", response_model=SongsResponse)
async def list_songs(
    request: Request,
    playlist_id: str | None = None,
    genre: str | None = None,
    year_from: int | None = None,
    year_to: int | None = None,
    limit: int = 50,
    offset: int = 0,
) -> SongsResponse:
    """Return a paginated, filtered list of songs from DuckDB."""
    limit = min(max(1, limit), 500)
    active_ids = {t["id"] for t in request.app.state.tracks}
    db = get_db_client()
    total, items = await run_in_threadpool(
        get_tracks,
        db,
        active_ids,
        playlist_id,
        genre,
        year_from,
        year_to,
        limit,
        offset,
    )
    return SongsResponse(
        total=total,
        items=[
            TrackRow(
                track_id=row["track_id"],
                name=row["name"],
                artists=[ArtistInfo(**a) for a in row["artists"]],
                album_name=row.get("album_name"),
                release_year=row.get("release_year"),
                is_active=row["is_active"],
            )
            for row in items
        ],
    )


@router.get("/stats", response_model=StatsResponse)
async def get_analytics_stats(playlist_id: str | None = None) -> StatsResponse:
    """Return year and genre distributions from DuckDB."""
    db = get_db_client()
    data = await run_in_threadpool(get_stats, db, playlist_id)
    return StatsResponse(
        total_tracks=data["total_tracks"],
        year_distribution=[YearBucket(**b) for b in data["year_distribution"]],
        genre_distribution=[GenreBucket(**b) for b in data["genre_distribution"]],
        playlists=[DBPlaylistInfo(**p) for p in data["playlists"]],
    )


@router.get("/playlists", response_model=list[DBPlaylistInfo])
async def list_db_playlists() -> list[DBPlaylistInfo]:
    """Return playlists available in DuckDB."""
    db = get_db_client()
    playlists = await run_in_threadpool(get_db_playlists, db)
    return [DBPlaylistInfo(**p) for p in playlists]
