---
name: project-etl-analytics
description: ETL + Analytics feature design context — playlist ingestion to DuckDB, genre enrichment, analytics API, and game integration
metadata:
  type: project
---

ETL + Analytics feature is in design phase (2026-05-13). The directories `src/etl/`, `src/analytics/`, and `src/utils/` already exist (empty — only __pycache__). `data/vinylvault.duckdb` already exists. No ETL or analytics code has been written yet.

**Why:** User wants to ingest arbitrary playlists via UI, store enriched track metadata in DuckDB (genres via artist lookup, available_markets for country proxy), and display an analytics tab with year/genre distributions and game-filter capability.

**Key decisions made in design:**
- Genres come from `sp.artists()` batched at 50 IDs — not from track or album objects (Spotify does not return genres on tracks)
- `available_markets` stored as JSON array; no country-of-origin inference (out of scope for v1)
- ETL runs async via `BackgroundTasks` — route returns 202 Accepted immediately, status polled via `GET /api/etl/status`
- Game integration via Option A: ETL writes to DB only; `POST /api/playlists/activate` loads from DB into `app.state.tracks` (no Spotify call at activate time)
- `DuckDBClient` lives in `src/etl/db.py` as a FastAPI dependency singleton; analytics queries go through same client
- `fetch_all_tracks` in `src/backend/spotify.py` is extended (fields parameter widened) rather than forked — ETL uses it with added `album.id, artists.id` fields
- Schema: `raw.tracks` (one row per track, JSON arrays for artists/genres/markets), `raw.playlist_tracks` join table, `raw.artists` cache table

**How to apply:** When implementation begins, validate these decisions against the actual Spotify API field names and DuckDB JSON function syntax before writing code.
