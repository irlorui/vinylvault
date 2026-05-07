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

VinylVault is a music timeline game: players listen to random tracks from a Spotify playlist and drag cards onto a chronological timeline. A FastAPI backend handles Spotify playback and game state; a plain HTML/CSS/JS frontend is served as static files by the same app.

```
src/
  backend/
    config.py     # loads .config/.env via pydantic-settings; exports Settings class and get_settings() factory
    models.py     # Pydantic response models: TrackResponse, ReferenceYearResponse, ScoreResponse
    score.py      # GameScore class: reset(), add(), won property; WIN_SCORE constant
    spotify.py    # spotipy client factory, get_random_track, play_track, pause_track, resume_track
    main.py       # FastAPI app: lifespan initializes sp + score on app.state; all API routes + static mount
  frontend/
    index.html / script.js / styles.css   # served at "/" by StaticFiles
docs/
  game-mechanics.md   # full game rules and flow diagrams
```

**Key architectural detail:** the `spotipy.Spotify` client is blocking, so all calls go through `run_in_threadpool`. Both the client (`app.state.sp`) and the score tracker (`app.state.score`) are created once in the FastAPI `lifespan`.

**Spotify OAuth:** uses `SpotifyOAuth` with `scope = "user-read-playback-state user-modify-playback-state"`. The token cache lives at `.config/.cache`. Playback requires Spotify Premium and an active device.

## API routes

| Method | Path | Description |
|--------|------|-------------|
| `GET`  | `/api/reference-year` | Random anchor year 1950–now (`ReferenceYearResponse`) |
| `GET`  | `/api/song` | Random track from the playlist (`TrackResponse`) |
| `POST` | `/api/play/{track_id}` | Start playback on the active Spotify device |
| `POST` | `/api/pause` | Pause playback |
| `POST` | `/api/resume` | Resume playback |
| `POST` | `/api/score/reset` | Reset score to 1 (reference card) → `ScoreResponse` |
| `POST` | `/api/score/add` | Add 1 point → `ScoreResponse(score, won)` |

## Game state machine (frontend)

`game.phase` drives all UI visibility in `script.js`:

```
idle → started → placing → placed → started  (correct reveal)
                                  → wrong → started  (wrong reveal, 1.5 s timeout)
                          → won  (score reaches WIN_SCORE)
```

- **`idle`**: only START button shown
- **`started`**: timeline visible, NEW SONG button shown
- **`placing`**: staging card (face-down, draggable) + drop zones in timeline
- **`placed`**: card moved into timeline (still draggable to change position), REVEAL enabled
- **`wrong`**: pending card animates red then disappears
- **`won`**: full-screen congratulations overlay; PLAY AGAIN resets to `idle`

`render()` calls `renderTimeline()` + `renderScore()` + `updateUI()` on every state change.

## Score

`GameScore` (in `score.py`) lives on `app.state.score`. `WIN_SCORE` controls the win threshold (currently `4` for testing). Reference card counts as 1 point on START; each correct REVEAL adds 1. Wrong placements do not score.

## Frontend drag-and-drop

- Staging card is draggable only in `placing` phase.
- In `placed` phase the pending card inside the timeline is also draggable (re-placement before REVEAL).
- Drop zones appear between all timeline cards in `placing` phase, and at all positions *except* the pending card's current slot in `placed` phase.

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
