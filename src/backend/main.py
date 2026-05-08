"""FastAPI application entry point for VinylVault."""

import random
from contextlib import asynccontextmanager
from datetime import datetime

from fastapi import FastAPI, HTTPException, Request
from fastapi.staticfiles import StaticFiles
from starlette.concurrency import run_in_threadpool

from src.backend.config import get_settings
from src.backend.models import (
    DeviceResponse,
    ReferenceYearResponse,
    ScoreResponse,
    TrackResponse,
    WildcardResponse,
)
from src.backend.score import GameScore, GameWildcard
from src.backend.spotify import (
    fetch_all_tracks,
    get_devices,
    get_random_track,
    get_spotify_client,
    pause_track,
    play_track,
    resume_track,
)

_CURRENT_YEAR = datetime.now().year


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize Spotify client, track list, and score tracker on startup."""
    settings = get_settings()
    app.state.sp = await run_in_threadpool(get_spotify_client)
    app.state.tracks = await run_in_threadpool(
        fetch_all_tracks, app.state.sp, settings.playlist_id
    )
    app.state.score = GameScore()
    app.state.wildcards = GameWildcard()
    app.state.device_id = None
    yield


app = FastAPI(title="VinylVault", lifespan=lifespan)


def _score_response(score: GameScore) -> ScoreResponse:
    return ScoreResponse(score=score.value, won=score.won)


def _wildcard_response(wc: GameWildcard) -> WildcardResponse:
    return WildcardResponse(wildcards=wc.value)


@app.get("/api/reference-year", response_model=ReferenceYearResponse)
async def get_reference_year() -> ReferenceYearResponse:
    """Return a random year between 1960 and the current year as the timeline anchor."""
    return ReferenceYearResponse(year=random.randint(1960, _CURRENT_YEAR))


@app.post("/api/score/reset", response_model=ScoreResponse)
async def reset_score(request: Request) -> ScoreResponse:
    """Reset score to 1 (reference card counts as first point) and return it."""
    request.app.state.score.reset()
    return _score_response(request.app.state.score)


@app.post("/api/score/add", response_model=ScoreResponse)
async def add_score(request: Request) -> ScoreResponse:
    """Add one point for a correct placement and return the updated score."""
    request.app.state.score.add()
    return _score_response(request.app.state.score)


@app.get("/api/song", response_model=TrackResponse)
async def get_song(request: Request) -> TrackResponse:
    """Return a random track from the cached playlist."""
    return get_random_track(request.app.state.tracks)


@app.get("/api/devices", response_model=list[DeviceResponse])
async def get_devices_endpoint(request: Request) -> list[DeviceResponse]:
    """Return all available Spotify playback devices."""
    return await run_in_threadpool(get_devices, request.app.state.sp)


@app.put("/api/device/{device_id}", status_code=204)
async def set_device(device_id: str, request: Request) -> None:
    """Pin a Spotify device to use for playback."""
    request.app.state.device_id = device_id


@app.post("/api/play/{track_id}", status_code=204)
async def play_song(track_id: str, request: Request) -> None:
    """Trigger playback of the given track on the pinned Spotify device."""
    await run_in_threadpool(
        play_track, request.app.state.sp, track_id, request.app.state.device_id
    )


@app.post("/api/pause", status_code=204)
async def pause_song(request: Request) -> None:
    """Pause playback on the active Spotify device."""
    await run_in_threadpool(pause_track, request.app.state.sp)


@app.post("/api/resume", status_code=204)
async def resume_song(request: Request) -> None:
    """Resume playback on the active Spotify device."""
    await run_in_threadpool(resume_track, request.app.state.sp)


@app.post("/api/wildcard/reset", response_model=WildcardResponse)
async def reset_wildcards(request: Request) -> WildcardResponse:
    """Reset wildcard count to 0 at game start."""
    request.app.state.wildcards.reset()
    return _wildcard_response(request.app.state.wildcards)


@app.post("/api/wildcard/add", response_model=WildcardResponse)
async def add_wildcard(request: Request) -> WildcardResponse:
    """Award one wildcard after a correct song name guess."""
    request.app.state.wildcards.add()
    return _wildcard_response(request.app.state.wildcards)


@app.post("/api/wildcard/use", response_model=WildcardResponse)
async def use_wildcard(request: Request) -> WildcardResponse:
    """Spend one wildcard to skip the current song."""
    try:
        request.app.state.wildcards.use()
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e)) from e
    return _wildcard_response(request.app.state.wildcards)


app.mount("/", StaticFiles(directory="src/frontend", html=True), name="frontend")
