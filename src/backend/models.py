"""Pydantic response models for the VinylVault API."""

from pydantic import BaseModel, field_validator


class TrackResponse(BaseModel):
    """API response model for a Spotify track."""

    track_id: str
    name: str
    artist: str
    year: str  # Spotify returns "YYYY-MM-DD"; we slice to 4 chars in get_random_track


class ReferenceYearResponse(BaseModel):
    """A randomly selected anchor year for the game timeline."""

    year: int


class DeviceResponse(BaseModel):
    """A Spotify playback device."""

    device_id: str
    name: str
    is_active: bool


class PlayerState(BaseModel):
    """Score and wildcard state for one player."""

    name: str
    score: int
    wildcards: int


class PlayersResponse(BaseModel):
    """Full multi-player state returned by all player-mutating routes."""

    players: list[PlayerState]
    current_player_index: int


class InitPlayersRequest(BaseModel):
    """Request body for POST /api/players/init."""

    names: list[str]

    @field_validator("names")
    @classmethod
    def validate_player_count(cls, v: list[str]) -> list[str]:
        """Enforce 1–4 players."""
        if not 1 <= len(v) <= 4:
            raise ValueError("Player count must be between 1 and 4.")
        return v
