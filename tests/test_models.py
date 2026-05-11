"""Unit tests for Pydantic response models."""

import pytest

from src.backend.models import (
    DeviceResponse,
    InitPlayersRequest,
    PlayersResponse,
    PlayerState,
    ReferenceYearResponse,
    TrackResponse,
)


def test_track_response_fields():
    track = TrackResponse(track_id="abc", name="Song", artist="Artist", year="1985")
    assert track.track_id == "abc"
    assert track.name == "Song"
    assert track.artist == "Artist"
    assert track.year == "1985"


def test_track_response_dict():
    track = TrackResponse(track_id="abc", name="Song", artist="Artist", year="1985")
    d = track.model_dump()
    assert d == {"track_id": "abc", "name": "Song", "artist": "Artist", "year": "1985"}


def test_reference_year_response():
    ref = ReferenceYearResponse(year=1990)
    assert ref.year == 1990
    assert ref.model_dump() == {"year": 1990}


def test_device_response_fields():
    d = DeviceResponse(device_id="dev1", name="Speaker", is_active=True)
    assert d.device_id == "dev1"
    assert d.name == "Speaker"
    assert d.is_active is True


def test_device_response_inactive():
    d = DeviceResponse(device_id="dev2", name="Phone", is_active=False)
    assert d.is_active is False


def test_track_response_invalid_type():
    with pytest.raises(Exception):
        TrackResponse.model_validate(
            {"track_id": 123, "name": None, "artist": "A", "year": "2000"}
        )


def test_player_state_fields():
    p = PlayerState(name="Alice", score=3, wildcards=1)
    assert p.name == "Alice"
    assert p.score == 3
    assert p.wildcards == 1
    assert p.model_dump() == {"name": "Alice", "score": 3, "wildcards": 1}


def test_players_response_fields():
    pr = PlayersResponse(
        players=[PlayerState(name="Alice", score=1, wildcards=0)],
        current_player_index=0,
    )
    assert pr.current_player_index == 0
    assert len(pr.players) == 1
    assert pr.players[0].name == "Alice"


def test_players_response_multi():
    pr = PlayersResponse(
        players=[
            PlayerState(name="Alice", score=2, wildcards=1),
            PlayerState(name="Bob", score=1, wildcards=0),
        ],
        current_player_index=1,
    )
    assert pr.current_player_index == 1
    assert pr.players[1].name == "Bob"


def test_init_players_request():
    req = InitPlayersRequest(names=["Alice", "Bob"])
    assert req.names == ["Alice", "Bob"]


def test_init_players_request_accepts_one():
    req = InitPlayersRequest(names=["Solo"])
    assert len(req.names) == 1


def test_init_players_request_accepts_four():
    req = InitPlayersRequest(names=["A", "B", "C", "D"])
    assert len(req.names) == 4


def test_init_players_request_rejects_empty():
    with pytest.raises(Exception):
        InitPlayersRequest(names=[])


def test_init_players_request_rejects_five():
    with pytest.raises(Exception):
        InitPlayersRequest(names=["A", "B", "C", "D", "E"])
