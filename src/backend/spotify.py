"""Spotify client factory and playback helpers."""

import random

import spotipy
from fastapi import HTTPException
from spotipy.exceptions import SpotifyException
from spotipy.oauth2 import SpotifyOAuth

from src.backend.config import (
    CACHE_PATH,
    CLIENT_ID,
    CLIENT_SECRET,
    PLAYLIST_ID,
    REDIRECT_URI,
)
from src.backend.models import TrackResponse

SCOPE = "user-read-playback-state user-modify-playback-state"


def get_spotify_client() -> spotipy.Spotify:
    """Create and return an authenticated Spotify client."""
    auth_manager = SpotifyOAuth(
        client_id=CLIENT_ID,
        client_secret=CLIENT_SECRET,
        redirect_uri=REDIRECT_URI,
        scope=SCOPE,
        cache_path=CACHE_PATH,
    )
    return spotipy.Spotify(auth_manager=auth_manager)


def get_random_track(
    sp: spotipy.Spotify, playlist_id: str = PLAYLIST_ID
) -> TrackResponse:
    """Return a random track from the given playlist."""
    result = sp.playlist_tracks(
        playlist_id,
        fields="items(track(id,name,artists,album(release_date)))",
        limit=100,
    )
    if not result:
        raise HTTPException(status_code=500, detail="Failed to fetch playlist tracks.")
    items = [i for i in result["items"] if i.get("track") is not None]

    if not items:
        raise HTTPException(status_code=404, detail="No playable tracks in playlist.")

    track = random.choice(items)["track"]
    return TrackResponse(
        track_id=track["id"],
        name=track["name"],
        artist=track["artists"][0]["name"],
        year=track["album"]["release_date"][:4],
    )


def play_track(sp: spotipy.Spotify, track_id: str) -> None:
    """Start playback of a track on the active or first available Spotify device."""
    devices = sp.devices()
    available = (devices or {}).get("devices", [])
    if not available:
        raise HTTPException(
            status_code=503,
            detail="No Spotify device found. Open Spotify on any device first.",
        )

    device_id = next((d["id"] for d in available if d["is_active"]), available[0]["id"])

    try:
        sp.start_playback(device_id=device_id, uris=[f"spotify:track:{track_id}"])
    except SpotifyException as e:
        if e.http_status == 403:
            raise HTTPException(status_code=403, detail="Spotify Premium required.")
        raise


def pause_track(sp: spotipy.Spotify) -> None:
    """Pause playback on the active Spotify device."""
    try:
        sp.pause_playback()
    except SpotifyException as e:
        if e.http_status == 403:
            raise HTTPException(status_code=403, detail="Spotify Premium required.")
        raise


def resume_track(sp: spotipy.Spotify) -> None:
    """Resume playback on the active Spotify device."""
    try:
        sp.start_playback()
    except SpotifyException as e:
        if e.http_status == 403:
            raise HTTPException(status_code=403, detail="Spotify Premium required.")
        raise
