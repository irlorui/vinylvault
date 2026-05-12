"""FastAPI application entry point for VinylVault."""

import random
from contextlib import asynccontextmanager
from datetime import datetime

import spotipy
from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.staticfiles import StaticFiles
from starlette.concurrency import run_in_threadpool

from src.backend.config import get_settings
from src.backend.models import (
    DeviceResponse,
    InitPlayersRequest,
    PlayersResponse,
    PlayerState,
    PlaylistInfo,
    ReferenceYearResponse,
    TrackResponse,
)
from src.backend.score import GamePlayers
from src.backend.spotify import (
    fetch_all_tracks,
    get_devices,
    get_playlist_name,
    get_random_track,
    get_spotify_client,
    pause_track,
    play_track,
    resume_track,
)

_CURRENT_YEAR = datetime.now().year
_EARLIEST_YEAR = 1960


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize Spotify client, per-playlist tracks, and player state on startup."""
    settings = get_settings()
    app.state.sp = await run_in_threadpool(get_spotify_client)

    tracks_by_playlist: dict[str, list] = {}
    playlists: list[PlaylistInfo] = []
    for pid in settings.playlist_id_list():
        t = await run_in_threadpool(fetch_all_tracks, app.state.sp, pid)
        name = await run_in_threadpool(get_playlist_name, app.state.sp, pid)
        tracks_by_playlist[pid] = t
        playlists.append(PlaylistInfo(playlist_id=pid, name=name))

    seen: set[str] = set()
    all_tracks: list[dict] = []
    for t_list in tracks_by_playlist.values():
        for t in t_list:
            if t["id"] not in seen:
                seen.add(t["id"])
                all_tracks.append(t)

    app.state.tracks = all_tracks
    app.state.tracks_by_playlist = tracks_by_playlist
    app.state.playlists = playlists
    app.state.players = GamePlayers()
    app.state.device_id = None
    yield


app = FastAPI(title="VinylVault", lifespan=lifespan)


# ─── Response helpers ──────────────────────────────────────────────────────


def _players_response(gp: GamePlayers) -> PlayersResponse:
    return PlayersResponse(
        players=[
            PlayerState(name=p.name, score=p.score.value, wildcards=p.wildcards.value)
            for p in gp.players
        ],
        current_player_index=gp.current_index,
    )


# ─── Dependency functions ──────────────────────────────────────────────────


def get_players(request: Request) -> GamePlayers:
    """Inject the shared GamePlayers from app state."""
    return request.app.state.players


def get_sp(request: Request) -> spotipy.Spotify:
    """Inject the Spotify client from app state."""
    return request.app.state.sp


def get_tracks(request: Request) -> list[dict]:
    """Inject the cached track list from app state."""
    return request.app.state.tracks


def get_tracks_by_playlist(request: Request) -> dict[str, list[dict]]:
    """Inject the per-playlist track mapping from app state."""
    return request.app.state.tracks_by_playlist


def get_device_id(request: Request) -> str | None:
    """Inject the pinned device ID from app state."""
    return request.app.state.device_id


# ─── Routes ────────────────────────────────────────────────────────────────


@app.get("/api/reference-year", response_model=ReferenceYearResponse)
async def get_reference_year() -> ReferenceYearResponse:
    """Return a random year between 1960 and the current year as the timeline anchor."""
    return ReferenceYearResponse(year=random.randint(_EARLIEST_YEAR, _CURRENT_YEAR))


@app.post("/api/players/init", response_model=PlayersResponse)
async def init_players(
    body: InitPlayersRequest,
    gp: GamePlayers = Depends(get_players),
) -> PlayersResponse:
    """Initialise all players and reset scores and wildcards for a new game."""
    gp.init(body.names)
    return _players_response(gp)


@app.post("/api/turn/next", response_model=PlayersResponse)
async def next_turn(gp: GamePlayers = Depends(get_players)) -> PlayersResponse:
    """Advance to the next player's turn."""
    gp.next_turn()
    return _players_response(gp)


@app.post("/api/score/add", response_model=PlayersResponse)
async def add_score(gp: GamePlayers = Depends(get_players)) -> PlayersResponse:
    """Add one point for the current player's correct placement."""
    gp.current.score.add()
    return _players_response(gp)


@app.get("/api/playlists", response_model=list[PlaylistInfo])
async def get_playlists(request: Request) -> list[PlaylistInfo]:
    """Return all configured playlists available for the game."""
    return request.app.state.playlists


@app.get("/api/song", response_model=TrackResponse)
async def get_song(
    tracks: list[dict] = Depends(get_tracks),
    tracks_by_playlist: dict[str, list[dict]] = Depends(get_tracks_by_playlist),
    exclude: str = "",
    playlists: str = "",
) -> TrackResponse:
    """Return a random track, optionally filtered to a subset of playlists."""
    if playlists:
        selected = {p for p in playlists.split(",") if p}
        seen: set[str] = set()
        pool: list[dict] = []
        for pid in selected:
            for t in tracks_by_playlist.get(pid, []):
                if t["id"] not in seen:
                    seen.add(t["id"])
                    pool.append(t)
    else:
        pool = tracks
    exclude_ids = set(filter(None, exclude.split(","))) if exclude else None
    return get_random_track(pool, exclude_ids)


@app.get("/api/devices", response_model=list[DeviceResponse])
async def get_devices_endpoint(
    sp: spotipy.Spotify = Depends(get_sp),
) -> list[DeviceResponse]:
    """Return all available Spotify playback devices."""
    return await run_in_threadpool(get_devices, sp)


@app.put("/api/device/{device_id}", status_code=204)
async def set_device(device_id: str, request: Request) -> None:
    """Pin a Spotify device to use for playback."""
    request.app.state.device_id = device_id


@app.post("/api/play/{track_id}", status_code=204)
async def play_song(
    track_id: str,
    tracks: list[dict] = Depends(get_tracks),
    sp: spotipy.Spotify = Depends(get_sp),
    device_id: str | None = Depends(get_device_id),
) -> None:
    """Trigger playback of the given track on the pinned Spotify device."""
    if track_id not in {t["id"] for t in tracks}:
        raise HTTPException(status_code=404, detail="Track not in playlist.")
    await run_in_threadpool(play_track, sp, track_id, device_id)


@app.post("/api/pause", status_code=204)
async def pause_song(sp: spotipy.Spotify = Depends(get_sp)) -> None:
    """Pause playback on the active Spotify device."""
    await run_in_threadpool(pause_track, sp)


@app.post("/api/resume", status_code=204)
async def resume_song(sp: spotipy.Spotify = Depends(get_sp)) -> None:
    """Resume playback on the active Spotify device."""
    await run_in_threadpool(resume_track, sp)


@app.post("/api/wildcard/add", response_model=PlayersResponse)
async def add_wildcard(gp: GamePlayers = Depends(get_players)) -> PlayersResponse:
    """Award one wildcard to the current player after a correct song name guess."""
    gp.current.wildcards.add()
    return _players_response(gp)


@app.post("/api/wildcard/use", response_model=PlayersResponse)
async def use_wildcard(gp: GamePlayers = Depends(get_players)) -> PlayersResponse:
    """Spend one of the current player's wildcards to skip the current song."""
    try:
        gp.current.wildcards.use()
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e)) from e
    return _players_response(gp)


app.mount("/", StaticFiles(directory="src/frontend", html=True), name="frontend")
