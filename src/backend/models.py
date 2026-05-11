"""Pydantic response models."""

from pydantic import BaseModel


class TrackResponse(BaseModel):
    """API response model for a Spotify track."""

    track_id: str
    name: str
    artist: str
    year: str


class ReferenceYearResponse(BaseModel):
    """A randomly selected anchor year for the game timeline."""

    year: int


class ScoreResponse(BaseModel):
    """Current game score."""

    score: int


class DeviceResponse(BaseModel):
    """A Spotify playback device."""

    device_id: str
    name: str
    is_active: bool


class WildcardResponse(BaseModel):
    """Current wildcard count for the active game session."""

    wildcards: int
