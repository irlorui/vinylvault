"""Unit tests for Pydantic response models."""

import pytest

from src.backend.models import (
    DeviceResponse,
    ReferenceYearResponse,
    ScoreResponse,
    TrackResponse,
    WildcardResponse,
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


def test_score_response_not_won():
    s = ScoreResponse(score=2, won=False)
    assert s.score == 2
    assert s.won is False


def test_score_response_won():
    s = ScoreResponse(score=4, won=True)
    assert s.won is True


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
        TrackResponse(track_id=123, name=None, artist="A", year="2000")


def test_wildcard_response_fields():
    wc = WildcardResponse(wildcards=3)
    assert wc.wildcards == 3
    assert wc.model_dump() == {"wildcards": 3}
