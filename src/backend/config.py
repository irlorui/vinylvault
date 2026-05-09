"""Load environment configuration for Spotify credentials."""

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Spotify and app configuration loaded from .config/.env."""

    model_config = SettingsConfigDict(
        env_file=".config/.env", env_file_encoding="utf-8"
    )

    spotipy_client_id: str = Field(default="client")
    spotipy_client_secret: str = Field(default="secret")
    spotipy_redirect_uri: str = Field(default="http://127.0.0.1:8888/callback")
    playlist_id: str = Field(default="playlist_id")
    cache_path: str = ".config/.cache"


def get_settings() -> Settings:
    """Get application settings."""
    settings = Settings()

    return settings
