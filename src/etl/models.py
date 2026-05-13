"""Pydantic request/response models for ETL and playlist-activation routes."""

import re
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, field_validator


class ETLRunRequest(BaseModel):
    """Request body for POST /api/etl/run."""

    playlist_uris: list[str]

    @field_validator("playlist_uris")
    @classmethod
    def normalize_uris(cls, v: list[str]) -> list[str]:
        """Normalize and validate playlist URIs, accepting various Spotify formats."""
        if not v:
            raise ValueError("At least one playlist URI is required.")
        if len(v) > 20:
            raise ValueError("Maximum 20 playlists per ETL run.")
        normalized = []
        for raw in v:
            pid = raw.strip()
            if pid.startswith("spotify:playlist:"):
                pid = pid[len("spotify:playlist:") :]
            else:
                m = re.search(r"playlist/([A-Za-z0-9]+)", pid)
                if m:
                    pid = m.group(1)
            if not re.match(r"^[A-Za-z0-9]{10,30}$", pid):
                raise ValueError(f"Invalid Spotify playlist identifier: {raw!r}")
            normalized.append(pid)
        return list(dict.fromkeys(normalized))


class ETLStatusResponse(BaseModel):
    """Current ETL pipeline status returned by GET /api/etl/status."""

    status: Literal["idle", "running", "done", "error"]
    playlists_processed: int
    tracks_upserted: int
    error: str | None
    started_at: datetime | None
    finished_at: datetime | None


class ActivatePlaylistRequest(BaseModel):
    """Request body for POST /api/playlists/activate."""

    playlist_id: str


class ActivatePlaylistResponse(BaseModel):
    """Result of activating a DB playlist into the active game track pool."""

    tracks_added: int
    total_active_tracks: int
