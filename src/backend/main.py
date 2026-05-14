"""FastAPI application entry point for VinylVault."""

import logging
import random
from contextlib import asynccontextmanager
from datetime import datetime, timezone

import spotipy
from fastapi import BackgroundTasks, Depends, FastAPI, HTTPException, Request
from fastapi.staticfiles import StaticFiles
from starlette.concurrency import run_in_threadpool

from src.analytics.queries import get_db_playlists, get_playlist_tracks_for_game
from src.analytics.routes import router as analytics_router
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
    get_devices,
    get_random_track,
    get_spotify_client,
    pause_track,
    play_track,
    resume_track,
)
from src.etl.db import close_db_client, get_db_client
from src.etl.models import (
    ActivatePlaylistRequest,
    ActivatePlaylistResponse,
    ETLRunRequest,
    ETLStatusResponse,
)
from src.etl.pipeline import run_etl
from src.etl.transformer import db_row_to_game_track

logger = logging.getLogger(__name__)

_CURRENT_YEAR = datetime.now().year
_EARLIEST_YEAR = 1960


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize Spotify client, track cache, player state, and DuckDB on startup."""
    app.state.sp = await run_in_threadpool(get_spotify_client)

    db = await run_in_threadpool(get_db_client)
    app.state.etl_status = {
        "status": "idle",
        "playlists_processed": 0,
        "tracks_upserted": 0,
        "error": None,
        "started_at": None,
        "finished_at": None,
    }

    tracks_by_playlist: dict[str, list] = {}
    playlists: list[PlaylistInfo] = []

    db_playlists = await run_in_threadpool(get_db_playlists, db)
    if not db_playlists:
        logger.warning("No playlists found in DB. Run ETL first.")
    for pl in db_playlists:
        pid = pl["playlist_id"]
        raw_rows = await run_in_threadpool(get_playlist_tracks_for_game, db, pid)
        tracks = [db_row_to_game_track(row) for row in raw_rows]
        tracks_by_playlist[pid] = tracks
        playlists.append(PlaylistInfo(playlist_id=pid, name=pl["name"]))

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
    app.state.played_ids = set()

    yield

    await run_in_threadpool(close_db_client)


app = FastAPI(title="VinylVault", lifespan=lifespan)
app.include_router(analytics_router)


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


# ─── Game routes ───────────────────────────────────────────────────────────


@app.get("/api/reference-year", response_model=ReferenceYearResponse)
async def get_reference_year() -> ReferenceYearResponse:
    """Return a random year between 1960 and the current year as the timeline anchor."""
    return ReferenceYearResponse(year=random.randint(_EARLIEST_YEAR, _CURRENT_YEAR))


@app.post("/api/players/init", response_model=PlayersResponse)
async def init_players(
    body: InitPlayersRequest,
    request: Request,
    gp: GamePlayers = Depends(get_players),
) -> PlayersResponse:
    """Initialise all players and reset scores and wildcards for a new game."""
    gp.init(body.names)
    request.app.state.played_ids = set()
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
    request: Request,
    tracks: list[dict] = Depends(get_tracks),
    tracks_by_playlist: dict[str, list[dict]] = Depends(get_tracks_by_playlist),
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
    track = get_random_track(pool, request.app.state.played_ids)
    request.app.state.played_ids.add(track.track_id)
    return track


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


# ─── ETL routes ────────────────────────────────────────────────────────────


@app.post("/api/etl/run", status_code=202, response_model=ETLStatusResponse)
async def run_etl_route(
    body: ETLRunRequest,
    background_tasks: BackgroundTasks,
    request: Request,
    sp: spotipy.Spotify = Depends(get_sp),
) -> ETLStatusResponse:
    """Trigger an ETL run for a list of playlist URIs (202 Accepted).

    The pipeline runs in the background; poll GET /api/etl/status for progress.
    """
    status = request.app.state.etl_status
    if status["status"] == "running":
        raise HTTPException(
            status_code=409, detail="An ETL run is already in progress."
        )
    db = get_db_client()
    background_tasks.add_task(run_etl, body.playlist_uris, sp, db, status)
    return ETLStatusResponse(
        status="running",
        playlists_processed=0,
        tracks_upserted=0,
        error=None,
        started_at=datetime.now(timezone.utc),
        finished_at=None,
    )


@app.get("/api/etl/status", response_model=ETLStatusResponse)
async def etl_status(request: Request) -> ETLStatusResponse:
    """Return the current ETL pipeline status."""
    s = request.app.state.etl_status
    return ETLStatusResponse(
        status=s["status"],
        playlists_processed=s["playlists_processed"],
        tracks_upserted=s["tracks_upserted"],
        error=s["error"],
        started_at=s["started_at"],
        finished_at=s["finished_at"],
    )


@app.post("/api/playlists/activate", response_model=ActivatePlaylistResponse)
async def activate_playlist(
    body: ActivatePlaylistRequest,
    request: Request,
) -> ActivatePlaylistResponse:
    """Load a DB-stored playlist into the active game track pool.

    Merges tracks from DuckDB into app.state.tracks and adds the playlist
    to app.state.playlists so the frontend CONFIG checkboxes pick it up.
    """
    db = get_db_client()

    playlists_in_db = await run_in_threadpool(get_db_playlists, db)
    if not any(p["playlist_id"] == body.playlist_id for p in playlists_in_db):
        raise HTTPException(status_code=404, detail="Playlist not found in database.")

    track_rows = await run_in_threadpool(
        get_playlist_tracks_for_game, db, body.playlist_id
    )
    game_tracks = [db_row_to_game_track(row) for row in track_rows]

    request.app.state.tracks_by_playlist[body.playlist_id] = game_tracks
    existing_ids = {t["id"] for t in request.app.state.tracks}
    new_tracks = [t for t in game_tracks if t["id"] not in existing_ids]
    request.app.state.tracks.extend(new_tracks)

    # Also register the playlist in app.state.playlists for game CONFIG panel
    existing_pl_ids = {p.playlist_id for p in request.app.state.playlists}
    if body.playlist_id not in existing_pl_ids:
        pl_name = next(
            (
                p["name"]
                for p in playlists_in_db
                if p["playlist_id"] == body.playlist_id
            ),
            body.playlist_id,
        )
        request.app.state.playlists.append(
            PlaylistInfo(playlist_id=body.playlist_id, name=pl_name)
        )

    return ActivatePlaylistResponse(
        tracks_added=len(new_tracks),
        total_active_tracks=len(request.app.state.tracks),
    )


app.mount("/", StaticFiles(directory="src/frontend", html=True), name="frontend")
