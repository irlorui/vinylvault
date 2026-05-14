# ETL Pipeline

VinylVault's ETL pipeline fetches track and artist metadata from the Spotify API and stores it in a local DuckDB database (`data/vinylvault.duckdb`). The backend loads all game data from DuckDB at startup — Spotipy is used only for playback, not track retrieval.

---

## Running the pipeline

### Via make

```bash
make etl              # run ETL using data/playlists.csv
make migrate          # apply DB migrations only (no playlist fetch)
```

### Via CLI

```bash
uv run python -m src.cli.run_etl [playlist_uri ...]
```

Playlist identifiers are accepted in any Spotify format:

```bash
# Bare ID
uv run python -m src.cli.run_etl 37i9dQZF1DXcBWIGoYBM5M

# URI
uv run python -m src.cli.run_etl spotify:playlist:37i9dQZF1DXcBWIGoYBM5M

# Share URL
uv run python -m src.cli.run_etl https://open.spotify.com/playlist/37i9dQZF1DXcBWIGoYBM5M
```

When no arguments are given, the CLI reads from `data/playlists.csv` (see [CSV format](#csv-format)).

**Flags**

| Flag | Description |
|------|-------------|
| `--migrate` | Apply DB migrations only; skip all playlist processing |
| `--csv PATH` | Use a different CSV file (default: `data/playlists.csv`) |

### Via HTTP API

`POST /api/etl/run` triggers the pipeline as a background task and returns `202 Accepted` immediately. Poll `GET /api/etl/status` to track progress. See [API Reference](api.md#post-apietlrun) for the full contract.

---

## CSV format

`data/playlists.csv` must have a `playlist_id` column. Additional columns are ignored.

```csv
playlist_id,label
37i9dQZF1DXcBWIGoYBM5M,Today's Top Hits
spotify:playlist:3cEYpjA9oz9GiPac4AsH4n,Rock Classics
```

---

## Pipeline phases

For each playlist the pipeline runs the following phases in order:

```
1. Skip check   →   2. Fetch   →   3. Upsert playlists
                                          ↓
                              4. Enrich genres (all playlists batched)
                                          ↓
                              5. Transform + upsert tracks
                                          ↓
                              6. Populate tracks_artists
                                          ↓
                              7. Replace playlist_tracks
```

### 1. Skip check

Before fetching a playlist, the pipeline queries `metadata.etl_log` for the most recent successful run (`status = 'done'`). If the watermark (`last_track_added_at`) is ≥ the current playlist's most recent `added_at` timestamp, the playlist is skipped — no API calls are made for track metadata.

### 2. Fetch (`src/etl/pipeline.py` → `fetch_all_tracks_enriched`)

Paginates through the Spotify playlist API (100 tracks/page) collecting:
- Track ID, name, URI
- Album ID, name, release date
- Artist IDs and names
- `added_at` timestamp (used for watermarking)

### 3. Upsert playlists

Upserts one row into `raw.playlists` (keyed on `playlist_uri`) and logs a row to `metadata.etl_log` with the run outcome.

### 4. Enrich genres (`src/etl/enricher.py`)

After all playlists are fetched, unique artist IDs are batched into groups of 50 and sent to `sp.artists()`. Artists already cached in `raw.artists` (with their genres) are skipped. Results are written to `raw.artists`, `raw.genres`, and `raw.artists_genres`. Exponential backoff handles Spotify 429 rate-limit responses (up to 3 retries).

### 5. Transform + upsert tracks (`src/etl/transformer.py`)

`transform_tracks` converts raw Spotify dicts to `raw.tracks` rows, deduplicating by track ID. Artists and genres are stored in separate linking tables, not in the tracks table.

### 6. Populate tracks_artists

Resolves integer PKs for all tracks and artists, then bulk-inserts into `raw.tracks_artists` using `ON CONFLICT DO NOTHING`.

### 7. Replace playlist_tracks

For each playlist, deletes existing `raw.playlist_tracks` rows and re-inserts them with the current track order (position index). Deduplicates tracks that appear multiple times in the same playlist (first occurrence wins).

---

## Database schema

The database lives at `data/vinylvault.duckdb`. Migrations are in `src/etl/migrations/` and run automatically at the start of each ETL run (or on `make migrate`).

### `raw` schema

#### `raw.playlists`

| Column | Type | Notes |
|--------|------|-------|
| `id` | `INTEGER` | Auto-increment PK |
| `playlist_uri` | `VARCHAR` | Spotify playlist ID — UNIQUE |
| `name` | `VARCHAR` | Display name |
| `etl_run_at` | `TIMESTAMP` | When the last ETL run started |

#### `raw.tracks`

| Column | Type | Notes |
|--------|------|-------|
| `id` | `INTEGER` | Auto-increment PK |
| `track_uri` | `VARCHAR` | Spotify track ID — UNIQUE |
| `name` | `VARCHAR` | Track title |
| `release_year` | `INTEGER` | Extracted from album release date |
| `album_name` | `VARCHAR` | Album title |
| `album_id` | `VARCHAR` | Spotify album ID |
| `inserted_at` | `TIMESTAMP` | First inserted |
| `updated_at` | `TIMESTAMP` | Last upserted |

#### `raw.artists`

| Column | Type | Notes |
|--------|------|-------|
| `id` | `INTEGER` | Auto-increment PK |
| `artist_uri` | `VARCHAR` | Spotify artist ID — UNIQUE |
| `name` | `VARCHAR` | Artist display name |
| `fetched_at` | `TIMESTAMP` | When genres were last fetched |

#### `raw.genres`

| Column | Type | Notes |
|--------|------|-------|
| `id` | `INTEGER` | Auto-increment PK |
| `name` | `VARCHAR` | Genre name — UNIQUE |

#### `raw.playlist_tracks` (linking)

| Column | Type | Notes |
|--------|------|-------|
| `playlist_id` | `INTEGER` | FK → `raw.playlists.id` |
| `track_id` | `INTEGER` | FK → `raw.tracks.id` |
| `position` | `INTEGER` | 0-based order within the playlist |

PK: `(playlist_id, track_id)`

#### `raw.tracks_artists` (linking)

| Column | Type | Notes |
|--------|------|-------|
| `track_id` | `INTEGER` | FK → `raw.tracks.id` |
| `artist_id` | `INTEGER` | FK → `raw.artists.id` |

PK: `(track_id, artist_id)`

#### `raw.artists_genres` (linking)

| Column | Type | Notes |
|--------|------|-------|
| `artist_id` | `INTEGER` | FK → `raw.artists.id` |
| `genre_id` | `INTEGER` | FK → `raw.genres.id` |

PK: `(artist_id, genre_id)`

---

### `metadata` schema

#### `metadata.etl_log`

One row per playlist per ETL run.

| Column | Type | Notes |
|--------|------|-------|
| `id` | `INTEGER` | Auto-increment PK |
| `playlist_id` | `VARCHAR` | Spotify playlist ID |
| `status` | `VARCHAR` | `'done'` or `'error'` |
| `tracks_processed` | `INTEGER` | Tracks fetched for this playlist |
| `error` | `VARCHAR` | Error message if status is `'error'` |
| `started_at` | `TIMESTAMPTZ` | Run start time (UTC) |
| `finished_at` | `TIMESTAMPTZ` | Run end time (UTC) |
| `last_track_added_at` | `TIMESTAMP` | Max `added_at` across all tracks (watermark) |

---

## Source files

| File | Responsibility |
|------|---------------|
| `src/cli/run_etl.py` | CLI entry point (`python -m src.cli.run_etl`) |
| `src/etl/pipeline.py` | Orchestrator: coordinates all phases, mutates status dict |
| `src/etl/db.py` | `DuckDBClient` wrapper + `get_db_client()` singleton |
| `src/etl/enricher.py` | Genre enrichment: batched `sp.artists()` with DB cache |
| `src/etl/transformer.py` | `transform_tracks` (Spotify dicts → DB rows), `db_row_to_game_track` (DB row → game format) |
| `src/etl/models.py` | `ETLRunRequest` (validates/normalises URIs), `ETLStatusResponse` |
| `src/utils/csv_reader.py` | `read_playlist_ids(path)` — reads `playlist_id` column from CSV |
| `src/etl/migrations/` | SQL scripts applied by `DuckDBClient.run_migrations()` |
