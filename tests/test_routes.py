"""API endpoint tests for all VinylVault routes."""

from datetime import datetime
from unittest.mock import patch

from fastapi.testclient import TestClient
from spotipy.exceptions import SpotifyException

from src.backend.main import app
from tests.conftest import SAMPLE_PLAYLIST_NAME, SAMPLE_TRACKS

# ─── GET /api/reference-year ─────────────────────────────────────────────────


def test_reference_year_status(client):
    res = client.get("/api/reference-year")
    assert res.status_code == 200


def test_reference_year_in_range(client):
    year = client.get("/api/reference-year").json()["year"]
    assert 1960 <= year <= datetime.now().year


# ─── POST /api/players/init ──────────────────────────────────────────────────


def test_players_init_single(client):
    res = client.post("/api/players/init", json={"names": ["Alice"]})
    assert res.status_code == 200
    data = res.json()
    assert len(data["players"]) == 1
    assert data["players"][0]["name"] == "Alice"
    assert data["players"][0]["score"] == 1
    assert data["players"][0]["wildcards"] == 0
    assert data["current_player_index"] == 0


def test_players_init_multi(client):
    res = client.post("/api/players/init", json={"names": ["Alice", "Bob", "Carol"]})
    assert res.status_code == 200
    data = res.json()
    assert len(data["players"]) == 3
    assert [p["name"] for p in data["players"]] == ["Alice", "Bob", "Carol"]


def test_players_init_resets_index(client):
    client.post("/api/players/init", json={"names": ["Alice", "Bob"]})
    client.post("/api/turn/next")
    res = client.post("/api/players/init", json={"names": ["Alice", "Bob"]})
    assert res.json()["current_player_index"] == 0


# ─── POST /api/turn/next ─────────────────────────────────────────────────────


def test_turn_next_advances(client):
    client.post("/api/players/init", json={"names": ["Alice", "Bob"]})
    res = client.post("/api/turn/next")
    assert res.status_code == 200
    assert res.json()["current_player_index"] == 1


def test_turn_next_wraps(client):
    client.post("/api/players/init", json={"names": ["Alice", "Bob"]})
    client.post("/api/turn/next")
    res = client.post("/api/turn/next")
    assert res.json()["current_player_index"] == 0


# ─── POST /api/score/add ─────────────────────────────────────────────────────


def test_score_add_increments(client):
    client.post("/api/players/init", json={"names": ["Alice"]})
    res = client.post("/api/score/add")
    assert res.status_code == 200
    assert res.json()["players"][0]["score"] == 2


def test_score_add_targets_current_player(client):
    client.post("/api/players/init", json={"names": ["Alice", "Bob"]})
    client.post("/api/turn/next")  # now Bob's turn
    client.post("/api/score/add")
    res = client.post("/api/score/add")
    data = res.json()
    assert data["players"][0]["score"] == 1  # Alice unchanged
    assert data["players"][1]["score"] == 3  # Bob: reset(1) + add + add


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
        patch("src.backend.main.get_playlist_name", return_value=SAMPLE_PLAYLIST_NAME),
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
        patch("src.backend.main.get_playlist_name", return_value=SAMPLE_PLAYLIST_NAME),
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


# ─── POST /api/wildcard/add ──────────────────────────────────────────────────


def test_wildcard_add_returns_one(client):
    client.post("/api/players/init", json={"names": ["Alice"]})
    res = client.post("/api/wildcard/add")
    assert res.status_code == 200
    assert res.json()["players"][0]["wildcards"] == 1


def test_wildcard_add_increments(client):
    client.post("/api/players/init", json={"names": ["Alice"]})
    client.post("/api/wildcard/add")
    res = client.post("/api/wildcard/add")
    assert res.json()["players"][0]["wildcards"] == 2


# ─── POST /api/wildcard/use ──────────────────────────────────────────────────


def test_wildcard_use_decrements(client):
    client.post("/api/players/init", json={"names": ["Alice"]})
    client.post("/api/wildcard/add")
    res = client.post("/api/wildcard/use")
    assert res.status_code == 200
    assert res.json()["players"][0]["wildcards"] == 0


def test_wildcard_use_returns_409_when_empty(client):
    client.post("/api/players/init", json={"names": ["Alice"]})
    res = client.post("/api/wildcard/use")
    assert res.status_code == 409


def test_wildcard_use_409_detail_message(client):
    client.post("/api/players/init", json={"names": ["Alice"]})
    res = client.post("/api/wildcard/use")
    assert res.status_code == 409
    assert res.json()["detail"] == "No wildcards available."


# ─── GET /api/song (exclude) ─────────────────────────────────────────────────


def test_get_song_exclude_filters_track(client):
    res = client.get("/api/song?exclude=track1")
    assert res.status_code == 200
    assert res.json()["track_id"] == "track2"


def test_get_song_exclude_all_tracks_returns_404(client):
    res = client.get("/api/song?exclude=track1,track2")
    assert res.status_code == 404


# ─── POST /api/players/init (additional) ────────────────────────────────────


def test_players_init_four_players(client):
    res = client.post("/api/players/init", json={"names": ["A", "B", "C", "D"]})
    assert res.status_code == 200
    assert len(res.json()["players"]) == 4


def test_players_init_reinit_with_fewer_players(client):
    client.post("/api/players/init", json={"names": ["Alice", "Bob", "Carol"]})
    res = client.post("/api/players/init", json={"names": ["Dave"]})
    data = res.json()
    assert len(data["players"]) == 1
    assert data["players"][0]["name"] == "Dave"
    assert data["current_player_index"] == 0


# ─── GET /api/playlists ──────────────────────────────────────────────────────


def test_get_playlists_returns_list(client):
    res = client.get("/api/playlists")
    assert res.status_code == 200
    assert isinstance(res.json(), list)


def test_get_playlists_fields(client):
    playlist = client.get("/api/playlists").json()[0]
    assert "playlist_id" in playlist
    assert "name" in playlist


def test_get_playlists_name_matches_mock(client):
    playlist = client.get("/api/playlists").json()[0]
    assert playlist["name"] == SAMPLE_PLAYLIST_NAME


# ─── GET /api/song (playlists filter) ────────────────────────────────────────


def test_get_song_with_valid_playlist_filter(client):
    playlist_id = client.get("/api/playlists").json()[0]["playlist_id"]
    res = client.get(f"/api/song?playlists={playlist_id}")
    assert res.status_code == 200
    assert res.json()["track_id"] in {t["id"] for t in SAMPLE_TRACKS}


def test_get_song_with_unknown_playlist_returns_404(client):
    res = client.get("/api/song?playlists=nonexistent_playlist")
    assert res.status_code == 404


# ─── _players_response helper ────────────────────────────────────────────────


def test_players_response_helper_shape():
    from src.backend.main import _players_response
    from src.backend.score import GamePlayers

    gp = GamePlayers()
    gp.init(["Alice", "Bob"])
    gp.next_turn()
    result = _players_response(gp)
    assert result.current_player_index == 1
    assert result.players[0].name == "Alice"
    assert result.players[0].score == 1
    assert result.players[0].wildcards == 0
    assert result.players[1].name == "Bob"
