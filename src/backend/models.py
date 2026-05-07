"""Pydantic response models."""

from pydantic import BaseModel


class TrackResponse(BaseModel):
    """API response model for a Spotify track."""

    track_id: str
    name: str
    artist: str
    year: str
