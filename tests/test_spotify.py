"""Unit tests for spotify.py helper functions."""

from unittest.mock import MagicMock

import pytest
import spotipy
from fastapi import HTTPException
from spotipy.exceptions import SpotifyException

from src.backend.models import DeviceResponse, TrackResponse
from src.backend.spotify import (
    _spotify_op,
    fetch_all_tracks,
    get_devices,
    get_random_track,
    pause_track,
    play_track,
    resume_track,
)

# ─── _spotify_op ────────────────────────────────────────────────────────────


def test_spotify_op_passes_through():
    with _spotify_op():
        pass  # no exception — should be silent


def test_spotify_op_converts_403():
    exc = SpotifyException(http_status=403, code=-1, msg="Premium required")
    with pytest.raises(HTTPException) as exc_info:
        with _spotify_op():
            raise exc
    assert exc_info.value.status_code == 403
    assert "Premium" in exc_info.value.detail


def test_spotify_op_reraises_other_spotify_exceptions():
    exc = SpotifyException(http_status=500, code=-1, msg="Server error")
    with pytest.raises(SpotifyException):
        with _spotify_op():
            raise exc


# ─── fetch_all_tracks ────────────────────────────────────────────────────────


def _make_track(track_id: str, name: str, year: str) -> dict:
    return {
        "id": track_id,
        "name": name,
        "artists": [{"name": "Artist"}],
        "album": {"release_date": f"{year}-01-01"},
    }


def test_fetch_all_tracks_single_page():
    sp = MagicMock(spec=spotipy.Spotify)
    sp.playlist_tracks.return_value = {
        "items": [{"track": _make_track("t1", "Song A", "1980")}],
        "next": None,
    }
    tracks = fetch_all_tracks(sp, "playlist123")
    assert len(tracks) == 1
    assert tracks[0]["id"] == "t1"


def test_fetch_all_tracks_pagination():
    sp = MagicMock(spec=spotipy.Spotify)
    page1 = {
        "items": [{"track": _make_track("t1", "Song A", "1980")}],
        "next": "page2_url",
    }
    page2 = {
        "items": [{"track": _make_track("t2", "Song B", "1990")}],
        "next": None,
    }
    sp.playlist_tracks.return_value = page1
    sp.next.return_value = page2

    tracks = fetch_all_tracks(sp, "playlist123")
    assert len(tracks) == 2
    assert tracks[0]["id"] == "t1"
    assert tracks[1]["id"] == "t2"
    sp.next.assert_called_once_with(page1)


def test_fetch_all_tracks_skips_none_tracks():
    sp = MagicMock(spec=spotipy.Spotify)
    sp.playlist_tracks.return_value = {
        "items": [{"track": None}, {"track": _make_track("t1", "Song A", "1980")}],
        "next": None,
    }
    tracks = fetch_all_tracks(sp, "playlist123")
    assert len(tracks) == 1
    assert tracks[0]["id"] == "t1"


# ─── get_random_track ────────────────────────────────────────────────────────


def test_get_random_track_empty_list():
    with pytest.raises(HTTPException) as exc_info:
        get_random_track([])
    assert exc_info.value.status_code == 404


def test_get_random_track_returns_track_response():
    track = _make_track("t1", "Bohemian Rhapsody", "1975")
    result = get_random_track([track])
    assert isinstance(result, TrackResponse)
    assert result.track_id == "t1"
    assert result.name == "Bohemian Rhapsody"
    assert result.year == "1975"


def test_get_random_track_extracts_year_from_release_date():
    track = _make_track("t1", "Song", "1991")
    track["album"]["release_date"] = "1991-09-10"
    result = get_random_track([track])
    assert result.year == "1991"


def test_get_random_track_all_excluded_raises_404():
    track = _make_track("t1", "Song", "1985")
    with pytest.raises(HTTPException) as exc_info:
        get_random_track([track], exclude={"t1"})
    assert exc_info.value.status_code == 404


def test_get_random_track_exclude_returns_only_non_excluded():
    t1 = _make_track("t1", "Song A", "1980")
    t2 = _make_track("t2", "Song B", "1991")
    result = get_random_track([t1, t2], exclude={"t1"})
    assert result.track_id == "t2"


def test_get_random_track_skips_malformed_tracks():
    malformed = [
        {"id": "bad1", "artists": [], "album": {"release_date": "unknown"}},
        {
            "id": "good",
            "name": "Song",
            "artists": [{"name": "A"}],
            "album": {"release_date": "2000-01-01"},
        },
    ]
    result = get_random_track(malformed)
    assert result.track_id == "good"


def test_get_random_track_skips_none_album():
    none_album = {
        "id": "bad",
        "name": "Bad Track",
        "artists": [{"name": "Artist"}],
        "album": None,
    }
    good = _make_track("good", "Good Song", "1990")
    result = get_random_track([none_album, good])
    assert result.track_id == "good"


# ─── get_devices ─────────────────────────────────────────────────────────────


def test_get_devices_maps_to_response():
    sp = MagicMock(spec=spotipy.Spotify)
    sp.devices.return_value = {
        "devices": [{"id": "dev1", "name": "Speaker", "is_active": True}]
    }
    devices = get_devices(sp)
    assert len(devices) == 1
    assert isinstance(devices[0], DeviceResponse)
    assert devices[0].device_id == "dev1"
    assert devices[0].is_active is True


def test_get_devices_empty():
    sp = MagicMock(spec=spotipy.Spotify)
    sp.devices.return_value = {"devices": []}
    assert get_devices(sp) == []


# ─── play_track ──────────────────────────────────────────────────────────────


def test_play_track_raises_503_without_device():
    sp = MagicMock(spec=spotipy.Spotify)
    with pytest.raises(HTTPException) as exc_info:
        play_track(sp, "track1", device_id=None)
    assert exc_info.value.status_code == 503


def test_play_track_calls_start_playback():
    sp = MagicMock(spec=spotipy.Spotify)
    play_track(sp, "track1", device_id="dev1")
    sp.start_playback.assert_called_once_with(
        device_id="dev1", uris=["spotify:track:track1"]
    )


# ─── pause_track ─────────────────────────────────────────────────────────────


def test_pause_track_calls_pause_playback():
    sp = MagicMock(spec=spotipy.Spotify)
    pause_track(sp)
    sp.pause_playback.assert_called_once()


def test_pause_track_converts_403():
    sp = MagicMock(spec=spotipy.Spotify)
    sp.pause_playback.side_effect = SpotifyException(
        http_status=403, code=-1, msg="Premium required"
    )
    with pytest.raises(HTTPException) as exc_info:
        pause_track(sp)
    assert exc_info.value.status_code == 403


# ─── resume_track ────────────────────────────────────────────────────────────


def test_resume_track_calls_start_playback():
    sp = MagicMock(spec=spotipy.Spotify)
    resume_track(sp)
    sp.start_playback.assert_called_once_with()


def test_resume_track_converts_403():
    sp = MagicMock(spec=spotipy.Spotify)
    sp.start_playback.side_effect = SpotifyException(
        http_status=403, code=-1, msg="Premium required"
    )
    with pytest.raises(HTTPException) as exc_info:
        resume_track(sp)
    assert exc_info.value.status_code == 403
