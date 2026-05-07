"""FastAPI application entry point for VinylVault."""

import random
from contextlib import asynccontextmanager
from datetime import datetime

from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from starlette.concurrency import run_in_threadpool

from src.backend.config import PLAYLIST_ID
from src.backend.models import ReferenceYearResponse, ScoreResponse, TrackResponse
from src.backend.score import GameScore
from src.backend.spotify import (
    get_random_track,
    get_spotify_client,
    pause_track,
    play_track,
    resume_track,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize Spotify client and score tracker on startup."""
    app.state.sp = await run_in_threadpool(get_spotify_client)
    app.state.score = GameScore()
    yield


app = FastAPI(title="VinylVault", lifespan=lifespan)


@app.get("/api/reference-year", response_model=ReferenceYearResponse)
async def get_reference_year() -> ReferenceYearResponse:
    """Return a random year between 1950 and the current year as the timeline anchor."""
    return ReferenceYearResponse(year=random.randint(1950, datetime.now().year))


@app.post("/api/score/reset", response_model=ScoreResponse)
async def reset_score(request: Request) -> ScoreResponse:
    """Reset score to 1 (reference card counts as first point) and return it."""
    request.app.state.score.reset()
    s = request.app.state.score
    return ScoreResponse(score=s.value, won=s.won)


@app.post("/api/score/add", response_model=ScoreResponse)
async def add_score(request: Request) -> ScoreResponse:
    """Add one point for a correct placement and return the updated score."""
    request.app.state.score.add()
    s = request.app.state.score
    return ScoreResponse(score=s.value, won=s.won)


@app.get("/api/song", response_model=TrackResponse)
async def get_song(request: Request) -> TrackResponse:
    """Return a random track from the configured playlist."""
    return await run_in_threadpool(get_random_track, request.app.state.sp, PLAYLIST_ID)


@app.post("/api/play/{track_id}", status_code=204)
async def play_song(track_id: str, request: Request) -> None:
    """Trigger playback of the given track on the active Spotify device."""
    await run_in_threadpool(play_track, request.app.state.sp, track_id)


@app.post("/api/pause", status_code=204)
async def pause_song(request: Request) -> None:
    """Pause playback on the active Spotify device."""
    await run_in_threadpool(pause_track, request.app.state.sp)


@app.post("/api/resume", status_code=204)
async def resume_song(request: Request) -> None:
    """Resume playback on the active Spotify device."""
    await run_in_threadpool(resume_track, request.app.state.sp)


app.mount("/", StaticFiles(directory="src/frontend", html=True), name="frontend")
