# Changelog

All notable changes to VinylVault are documented here.
Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

---

## [1.2.1] — 2026-05-11

### Fixed
- Enforce loopback binding (`--host 127.0.0.1`) in `make run` to prevent accidental network exposure of unauthenticated Spotify endpoints
- Validate `track_id` in `POST /api/play/{track_id}` against cached playlist tracks — returns 404 for IDs not in the configured playlists
- Suppress Spotify API error messages from 502 responses to avoid leaking internal API details to clients
- Add `@lru_cache` to `get_settings` to avoid re-reading `.env` on every call
- Reject empty and whitespace-only player names in `POST /api/players/init` (422)
- Guard `get_playlist_name` against `None` result from `sp.playlist()`
- Apply track-validity filter before exclude filter in `get_random_track`; `exclude=set()` now correctly excludes nothing
- Filter empty segments from `?playlists=` query parameter
- Fix skip-duplicate bug: current track ID is excluded when fetching the replacement song so the same track cannot be re-drawn

---

## [1.2.0] — 2026-05-11

### Added
- Multi-player support (1–4 players): each player has an independent timeline, score, and wildcard pool; players take turns in CONFIG order with score chips in the topbar showing `current/target`; NEXT TURN button appears after a correct reveal; wrong-reveal popup for 3+ players announces the next player by name; new routes `POST /api/players/init` and `POST /api/turn/next` manage turn state
- Multi-playlist support: define multiple Spotify playlists via `PLAYLIST_IDS` (comma-separated) in `.config/.env`; tracks are merged into a deduped pool at startup; new `GET /api/playlists` endpoint returns playlist IDs and names; `GET /api/song` accepts an optional `?playlists=` filter; CONFIG panel shows a checkbox per playlist so players can include/exclude playlists before a game
- Playlist warning in docs (README and game_rules.md) about compilation albums and classical music producing incorrect release years, with fix guidance
- GitHub issue templates (bug report and feature request) with Impact & Priority checkboxes and acceptance criteria section

### Changed
- Score and wildcard routes (`/api/score/add`, `/api/wildcard/add`, `/api/wildcard/use`) now return `PlayersResponse` (all players' state + current player index) instead of single-player `ScoreResponse`/`WildcardResponse`
- `PLAYLIST_ID` env var renamed to `PLAYLIST_IDS` (comma-separated list)

### Removed
- `POST /api/score/reset` and `POST /api/wildcard/reset` — superseded by `POST /api/players/init`

### Fixed
- Accessibility improvements: focus rings, `aria-label` and `aria-live` attributes, `role="alert"` on error messages
- Replaced biased `sort(() => Math.random() - 0.5)` card colour shuffle with Fisher-Yates algorithm

## [1.1.0] — 2026-05-11

### Added
- CONFIG panel — win score selector (configurable 4–20) and Spotify device selector, accessible before starting a game
- Player name input — displayed in the topbar throughout the game

### Changed
- Full Vinyl Vault design system: new typography, card colours, topbar redesign, and layout polish
- REVEAL button colour changed to green-lime for clearer visual affordance
- Improved placed-card colours and win screen layout

### Fixed
- Duplicate songs: `GET /api/song` now accepts an `?exclude=` query param; the frontend passes already-placed track IDs so the same song can never repeat in one game
- Removed `won` field from `POST /api/score/add` response (win logic moved entirely to frontend)
- Win score initialisation now reads the CONFIG panel value correctly on game start

---

## [1.0.0] — 2026-05-08

### Added
- **Wildcard / joker mechanic** — players earn wildcards by correctly naming a song's title and artist before REVEAL; wildcards can be spent to skip an unwanted song and draw a fresh one
- `GameWildcard` class (`score.py`) with `add()`, `use()`, and `reset()` methods
- Three new API routes: `POST /api/wildcard/reset`, `/add`, `/use` (returns `WildcardResponse`; `/use` responds 409 when empty)
- Wildcard counter display, SKIP button, and ADD WILDCARD button in the game UI
- Hover tooltips on SKIP, REVEAL, and ADD WILDCARD buttons
- Device selection UI — lists available Spotify devices via `GET /api/devices` and pins one with `PUT /api/device/{device_id}`; START is disabled until a device is chosen
- Full backend test suite with 98% coverage across `test_routes.py`, `test_score.py`, `test_spotify.py`, and `test_models.py`
- `docs/api.md` — full API reference
- `docs/how_to_setup_spotify_app.md` — step-by-step Spotify Developer app setup guide
- `CONTRIBUTING.md` — contributing guide
- Pull request template with test coverage checklist

### Changed
- App configuration now loaded at startup via `pydantic-settings` (`Settings` class + `@lru_cache get_settings()`); settings no longer read per-request

### Fixed
- XSS vulnerability in timeline card rendering — song names and artist values are now set via `textContent` instead of `innerHTML`
- API error responses now consistently propagate Spotify error details to the client

---

## [0.1.0] — 2026-05-07

### Added
- FastAPI backend with Spotify OAuth (`SpotifyOAuth`) and full playlist caching at startup via paginated `fetch_all_tracks`
- `GET /api/reference-year` — random anchor year 1960–present
- `GET /api/song` — random track from cached playlist (`TrackResponse`)
- `POST /api/play/{track_id}`, `POST /api/pause`, `POST /api/resume` — Spotify playback control (Premium required)
- `POST /api/score/reset` and `POST /api/score/add` — score tracking; `GameScore` with `WIN_SCORE = 4`
- Plain HTML/CSS/JS frontend served as static files by the same FastAPI app
- Timeline drag-and-drop — staging card draggable to any gap; re-draggable before REVEAL
- REVEAL — validates placement against neighbours, animates correct (green) and wrong (red shake + fade) outcomes
- Score pip display, full-screen win overlay, and PLAY AGAIN flow
- `_spotify_op` context manager — converts Spotify 403s to `HTTPException(403)`
- Pre-commit hooks with ruff lint/format and conventional commits enforcement
- `Makefile` with `setup`, `run`, `test`, `test-cov`, `pre-commit`, `ruff-format` targets
- `CLAUDE.md` with architecture, API reference, and project skills
