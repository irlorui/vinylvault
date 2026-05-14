"""Pydantic response models for analytics routes."""

from datetime import datetime

from pydantic import BaseModel


class ArtistInfo(BaseModel):
    """Minimal artist representation in analytics responses."""

    name: str


class TrackRow(BaseModel):
    """One track in the analytics song listing."""

    track_id: str
    name: str
    artists: list[ArtistInfo]
    album_name: str | None
    release_year: int | None
    is_active: bool


class SongsResponse(BaseModel):
    """Paginated track listing from DuckDB."""

    total: int
    items: list[TrackRow]


class YearBucket(BaseModel):
    """Count of tracks for a given year."""

    year: int
    count: int


class GenreBucket(BaseModel):
    """Count of tracks for a given genre."""

    genre: str
    count: int


class DBPlaylistInfo(BaseModel):
    """A playlist stored in DuckDB via ETL."""

    playlist_id: str
    name: str
    etl_run_at: datetime | None = None


class StatsResponse(BaseModel):
    """Year and genre distributions for the analytics view."""

    total_tracks: int
    year_distribution: list[YearBucket]
    genre_distribution: list[GenreBucket]
    playlists: list[DBPlaylistInfo]
