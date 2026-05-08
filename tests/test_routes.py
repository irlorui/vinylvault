"""API endpoint tests for all VinylVault routes."""

from datetime import datetime
from unittest.mock import patch

from fastapi.testclient import TestClient
from spotipy.exceptions import SpotifyException

from src.backend.main import app
from tests.conftest import SAMPLE_TRACKS

# ─── GET /api/reference-year ─────────────────────────────────────────────────


def test_reference_year_status(client):
    res = client.get("/api/reference-year")
    assert res.status_code == 200


def test_reference_year_in_range(client):
    year = client.get("/api/reference-year").json()["year"]
    assert 1960 <= year <= datetime.now().year


# ─── POST /api/score/reset ───────────────────────────────────────────────────


def test_score_reset_returns_one(client):
    res = client.post("/api/score/reset")
    assert res.status_code == 200
    data = res.json()
    assert data["score"] == 1
    assert data["won"] is False


# ─── POST /api/score/add ─────────────────────────────────────────────────────


def test_score_add_increments(client):
    client.post("/api/score/reset")
    res = client.post("/api/score/add")
    assert res.status_code == 200
    assert res.json()["score"] == 2


def test_score_add_won_at_four(client):
    client.post("/api/score/reset")  # score = 1
    client.post("/api/score/add")  # 2
    client.post("/api/score/add")  # 3
    res = client.post("/api/score/add")  # 4
    data = res.json()
    assert data["score"] == 4
    assert data["won"] is True


def test_score_add_not_won_at_three(client):
    client.post("/api/score/reset")  # 1
    client.post("/api/score/add")  # 2
    res = client.post("/api/score/add")  # 3
    assert res.json()["won"] is False


# ─── GET /api/song ───────────────────────────────────────────────────────────


def test_get_song_returns_track(client):
    res = client.get("/api/song")
    assert res.status_code == 200
    data = res.json()
    assert "track_id" in data
    assert "name" in data
    assert "artist" in data
    assert "year" in data


def test_get_song_track_in_sample_list(client):
    res = client.get("/api/song")
    track_ids = {t["id"] for t in SAMPLE_TRACKS}
    assert res.json()["track_id"] in track_ids


def test_get_song_404_when_no_tracks(mock_sp):
    with (
        patch("src.backend.main.get_spotify_client", return_value=mock_sp),
        patch("src.backend.main.fetch_all_tracks", return_value=[]),
    ):
        with TestClient(app) as c:
            res = c.get("/api/song")
    assert res.status_code == 404


# ─── GET /api/devices ────────────────────────────────────────────────────────


def test_get_devices_returns_list(client):
    res = client.get("/api/devices")
    assert res.status_code == 200
    assert isinstance(res.json(), list)


def test_get_devices_fields(client):
    device = client.get("/api/devices").json()[0]
    assert "device_id" in device
    assert "name" in device
    assert "is_active" in device


def test_get_devices_empty(mock_sp):
    mock_sp.devices.return_value = {"devices": []}
    with (
        patch("src.backend.main.get_spotify_client", return_value=mock_sp),
        patch("src.backend.main.fetch_all_tracks", return_value=SAMPLE_TRACKS),
    ):
        with TestClient(app) as c:
            res = c.get("/api/devices")
    assert res.json() == []


# ─── PUT /api/device/{device_id} ─────────────────────────────────────────────


def test_set_device_returns_204(client):
    res = client.put("/api/device/dev1")
    assert res.status_code == 204


def test_set_device_updates_state(client):
    client.put("/api/device/dev42")
    assert client.app.state.device_id == "dev42"


# ─── POST /api/play/{track_id} ───────────────────────────────────────────────


def test_play_returns_503_without_device(client):
    res = client.post("/api/play/track1")
    assert res.status_code == 503


def test_play_returns_204_with_device(client, mock_sp):
    client.put("/api/device/dev1")
    res = client.post("/api/play/track1")
    assert res.status_code == 204
    mock_sp.start_playback.assert_called_once_with(
        device_id="dev1", uris=["spotify:track:track1"]
    )


# ─── POST /api/pause ─────────────────────────────────────────────────────────


def test_pause_returns_204(client):
    res = client.post("/api/pause")
    assert res.status_code == 204


def test_pause_returns_403_on_premium_error(client, mock_sp):
    mock_sp.pause_playback.side_effect = SpotifyException(
        http_status=403, code=-1, msg="Premium required"
    )
    res = client.post("/api/pause")
    assert res.status_code == 403


# ─── POST /api/resume ────────────────────────────────────────────────────────


def test_resume_returns_204(client):
    res = client.post("/api/resume")
    assert res.status_code == 204


def test_resume_returns_403_on_premium_error(client, mock_sp):
    mock_sp.start_playback.side_effect = SpotifyException(
        http_status=403, code=-1, msg="Premium required"
    )
    res = client.post("/api/resume")
    assert res.status_code == 403


# ─── POST /api/wildcard/reset ────────────────────────────────────────────────


def test_wildcard_reset_returns_zero(client):
    client.app.state.wildcards.add()
    res = client.post("/api/wildcard/reset")
    assert res.status_code == 200
    assert res.json()["wildcards"] == 0


# ─── POST /api/wildcard/add ──────────────────────────────────────────────────


def test_wildcard_add_returns_one(client):
    client.post("/api/wildcard/reset")
    res = client.post("/api/wildcard/add")
    assert res.status_code == 200
    assert res.json()["wildcards"] == 1


def test_wildcard_add_increments(client):
    client.post("/api/wildcard/reset")
    client.post("/api/wildcard/add")
    res = client.post("/api/wildcard/add")
    assert res.json()["wildcards"] == 2


# ─── POST /api/wildcard/use ──────────────────────────────────────────────────


def test_wildcard_use_decrements(client):
    client.post("/api/wildcard/reset")
    client.post("/api/wildcard/add")
    res = client.post("/api/wildcard/use")
    assert res.status_code == 200
    assert res.json()["wildcards"] == 0


def test_wildcard_use_returns_409_when_empty(client):
    client.post("/api/wildcard/reset")
    res = client.post("/api/wildcard/use")
    assert res.status_code == 409
