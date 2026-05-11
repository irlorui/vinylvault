"""Spotify client factory and playback helpers."""

import random
from contextlib import contextmanager

import spotipy
from fastapi import HTTPException
from spotipy.exceptions import SpotifyException
from spotipy.oauth2 import SpotifyOAuth

from src.backend.config import get_settings
from src.backend.models import DeviceResponse, TrackResponse

SCOPE = "user-read-playback-state user-modify-playback-state"


@contextmanager
def _spotify_op():
    """Wrap a Spotify call, converting 403s to HTTPException."""
    try:
        yield
    except SpotifyException as e:
        if e.http_status == 403:
            raise HTTPException(status_code=403, detail="Spotify Premium required.")
        raise


def get_spotify_client() -> spotipy.Spotify:
    """Create and return an authenticated Spotify client."""
    settings = get_settings()
    auth_manager = SpotifyOAuth(
        client_id=settings.spotipy_client_id,
        client_secret=settings.spotipy_client_secret,
        redirect_uri=settings.spotipy_redirect_uri,
        scope=SCOPE,
        cache_path=settings.cache_path,
    )
    return spotipy.Spotify(auth_manager=auth_manager)


def fetch_all_tracks(sp: spotipy.Spotify, playlist_id: str) -> list[dict]:
    """Fetch every track from a playlist, following pagination."""
    tracks = []
    result = sp.playlist_tracks(
        playlist_id,
        fields="items(track(id,name,artists,album(release_date))),next",
        limit=100,
    )
    while result:
        tracks.extend(i["track"] for i in result["items"] if i.get("track") is not None)
        result = sp.next(result) if result.get("next") else None
    return tracks


def get_random_track(
    tracks: list[dict], exclude: set[str] | None = None
) -> TrackResponse:
    """Return a random track from a pre-fetched list, skipping any excluded IDs."""
    available = [t for t in tracks if t["id"] not in exclude] if exclude else tracks
    available = [
        t
        for t in available
        if t.get("artists")
        and (t.get("album") or {}).get("release_date", "")[:4].isdigit()
    ]
    if not available:
        raise HTTPException(status_code=404, detail="No playable tracks in playlist.")
    track = random.choice(available)
    return TrackResponse(
        track_id=track["id"],
        name=track["name"],
        artist=track["artists"][0]["name"],
        year=track["album"]["release_date"][:4],
    )


def get_devices(sp: spotipy.Spotify) -> list[DeviceResponse]:
    """Return all available Spotify playback devices."""
    result = sp.devices()
    return [
        DeviceResponse(
            device_id=d["id"],
            name=d["name"],
            is_active=d["is_active"],
        )
        for d in (result or {}).get("devices", [])
    ]


def play_track(
    sp: spotipy.Spotify, track_id: str, device_id: str | None = None
) -> None:
    """Start playback of a track on the pinned Spotify device."""
    if device_id is None:
        raise HTTPException(
            status_code=503,
            detail="No device selected. Choose a device first.",
        )
    with _spotify_op():
        sp.start_playback(device_id=device_id, uris=[f"spotify:track:{track_id}"])


def pause_track(sp: spotipy.Spotify) -> None:
    """Pause playback on the active Spotify device."""
    with _spotify_op():
        sp.pause_playback()


def resume_track(sp: spotipy.Spotify) -> None:
    """Resume playback on the active Spotify device."""
    with _spotify_op():
        sp.start_playback()
