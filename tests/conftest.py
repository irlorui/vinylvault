"""Shared fixtures for VinylVault tests."""

from unittest.mock import MagicMock, patch

import pytest
import spotipy
from fastapi.testclient import TestClient

from src.backend.main import app

SAMPLE_TRACKS = [
    {
        "id": "track1",
        "name": "Bohemian Rhapsody",
        "artists": [{"name": "Queen"}],
        "album": {"release_date": "1975-10-31"},
    },
    {
        "id": "track2",
        "name": "Smells Like Teen Spirit",
        "artists": [{"name": "Nirvana"}],
        "album": {"release_date": "1991-09-10"},
    },
]

SAMPLE_PLAYLIST_NAME = "Test Playlist"


@pytest.fixture
def mock_sp():
    """Mock spotipy.Spotify with a single active device."""
    sp = MagicMock(spec=spotipy.Spotify)
    sp.devices.return_value = {
        "devices": [{"id": "dev1", "name": "My Speaker", "is_active": True}]
    }
    return sp


@pytest.fixture
def client(mock_sp):
    """TestClient with lifespan mocked — no real Spotify calls."""
    with (
        patch("src.backend.main.get_spotify_client", return_value=mock_sp),
        patch("src.backend.main.fetch_all_tracks", return_value=list(SAMPLE_TRACKS)),
        patch("src.backend.main.get_playlist_name", return_value=SAMPLE_PLAYLIST_NAME),
    ):
        with TestClient(app) as c:
            yield c
