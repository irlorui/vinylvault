# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
make setup        # create venv and install all dependencies (uv venv && uv sync)
make run          # start the FastAPI dev server with hot-reload
make pre-commit   # run pre-commit hooks + ruff lint + ruff format check
make ruff-format  # auto-format code with ruff
```

Run lint and format individually:
```bash
uv run ruff check .       # lint
uv run ruff format .      # format
uv run ruff format --check .  # check formatting without writing
```

## Architecture

VinylVault is a music guessing game: a FastAPI backend fetches a random track from a Spotify playlist and can trigger playback on a connected Spotify device. A plain HTML/CSS/JS frontend is served as static files by the same FastAPI app.

```
src/
  backend/
    config.py     # loads .config/.env; exports CLIENT_ID, CLIENT_SECRET, REDIRECT_URI, PLAYLIST_ID, CACHE_PATH
    models.py     # Pydantic response models (TrackResponse)
    spotify.py    # spotipy client factory, get_random_track, play_track
    main.py       # FastAPI app: lifespan initializes sp on app.state, two API routes + static mount
  frontend/
    index.html / script.js / styles.css  # served at "/" by StaticFiles
```

**Key architectural detail:** the `spotipy.Spotify` client is blocking, so all calls go through `run_in_threadpool`. The client is created once during the FastAPI `lifespan` and stored at `app.state.sp`.

**Spotify OAuth:** uses `SpotifyOAuth` with `scope = "user-read-playback-state user-modify-playback-state"`. The token cache lives at `.config/.cache`. Playback requires Spotify Premium and an active device.

## Environment

Copy `.config/.env.example` to `.config/.env`:
```
SPOTIPY_CLIENT_ID=
SPOTIPY_CLIENT_SECRET=
SPOTIPY_REDIRECT_URI=https://localhost:8888/callback
PLAYLIST_ID=
```

## Code standards

- **Dependencies:** always `uv add <package>`, never `pip install`.
- **Docstrings:** Google style; one-liners are fine for simple functions.
- **Ruff lint rules:** E, F, I, D (pydocstyle with Google convention).

## Commits

Use the `/commit` skill to automate this: it runs `make pre-commit`, analyzes staged changes, and creates a properly formatted conventional commit.
