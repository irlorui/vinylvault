"""Load environment configuration for Spotify credentials."""

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Spotify and app configuration loaded from .config/.env."""

    model_config = SettingsConfigDict(
        env_file=".config/.env", env_file_encoding="utf-8", extra="ignore"
    )

    spotipy_client_id: str = Field(default="client")
    spotipy_client_secret: str = Field(default="secret")
    spotipy_redirect_uri: str = Field(default="http://127.0.0.1:8888/callback")
    playlist_ids: str = Field(default="playlist_id")
    cache_path: str = ".config/.cache"

    def playlist_id_list(self) -> list[str]:
        """Return playlist IDs as a list, split from the comma-separated string."""
        return [p.strip() for p in self.playlist_ids.split(",") if p.strip()]


@lru_cache
def get_settings() -> Settings:
    """Get application settings."""
    return Settings()
