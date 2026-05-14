# API Reference

Base URL: `http://127.0.0.1:8000`

All endpoints return JSON unless the response is `204 No Content`. Error bodies follow FastAPI's default shape: `{"detail": "<message>"}`.

---

## Endpoints

### GET /api/reference-year

**Description:** Return a random anchor year for the game timeline.

**Response:** `200` — `ReferenceYearResponse`

#### Response body
| Field | Type | Description |
|-------|------|-------------|
| `year` | `int` | Random integer in `[1960, current_year]` |

---

### POST /api/players/init

**Description:** Initialise 1–4 named players, reset all scores and wildcards, and clear the server-side played-track set for a new game.

#### Request body
| Field | Type | Description |
|-------|------|-------------|
| `names` | `list[str]` | 1–4 non-empty player names |

**Response:** `200` — `PlayersResponse`

#### Response body
| Field | Type | Description |
|-------|------|-------------|
| `players` | `list[PlayerState]` | Ordered list of all players |
| `current_player_index` | `int` | Index of the player whose turn it is |

**`PlayerState`**
| Field | Type | Description |
|-------|------|-------------|
| `name` | `str` | Player name |
| `score` | `int` | Current score (starts at 1 — reference card) |
| `wildcards` | `int` | Available wildcards (starts at 0) |

#### Errors
| Status | Meaning |
|--------|---------|
| `422` | `names` is empty, contains more than 4 entries, or any name is blank |

---

### POST /api/turn/next

**Description:** Advance to the next player's turn (wraps around).

**Response:** `200` — `PlayersResponse` (see above)

---

### POST /api/score/add

**Description:** Add one point to the current player's score.

**Response:** `200` — `PlayersResponse`

---

### GET /api/playlists

**Description:** Return all playlists currently loaded in the active game pool.

**Response:** `200` — `list[PlaylistInfo]`

#### Response body (each item)
| Field | Type | Description |
|-------|------|-------------|
| `playlist_id` | `str` | Spotify playlist ID |
| `name` | `str` | Playlist display name |

---

### GET /api/song

**Description:** Return a random track from the active pool, excluding tracks already served in the current game. The served track ID is recorded server-side so it will not be returned again until `POST /api/players/init` resets the game.

#### Query parameters
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `playlists` | `str` | `""` | Comma-separated playlist IDs to restrict the pool |

**Response:** `200` — `TrackResponse`

#### Response body
| Field | Type | Description |
|-------|------|-------------|
| `track_id` | `str` | Spotify track ID |
| `name` | `str` | Track title |
| `artist` | `str` | Comma-separated artist names |
| `year` | `str` | 4-digit release year |

#### Errors
| Status | Meaning |
|--------|---------|
| `404` | No playable tracks remain in the pool (all played, pool is empty, or no tracks have a valid year) |

---

### GET /api/devices

**Description:** Return all available Spotify playback devices.

**Response:** `200` — `list[DeviceResponse]`

#### Response body (each item)
| Field | Type | Description |
|-------|------|-------------|
| `device_id` | `str` | Spotify device ID |
| `name` | `str` | Device display name |
| `is_active` | `bool` | Whether the device is currently active in Spotify |

#### Errors
| Status | Meaning |
|--------|---------|
| `403` | Spotify Premium required |
| `502` | Unexpected Spotify API error |

---

### PUT /api/device/{device_id}

**Description:** Pin a Spotify device for all subsequent playback calls.

**Response:** `204 No Content`

---

### POST /api/play/{track_id}

**Description:** Start playback of the given track on the pinned device.

**Response:** `204 No Content`

#### Errors
| Status | Meaning |
|--------|---------|
| `404` | `track_id` not in the active track pool |
| `503` | No device pinned — call `PUT /api/device/{device_id}` first |
| `403` | Spotify Premium required |
| `502` | Unexpected Spotify API error |

---

### POST /api/pause

**Description:** Pause playback on the active Spotify device.

**Response:** `204 No Content`

#### Errors
| Status | Meaning |
|--------|---------|
| `403` | Spotify Premium required |
| `502` | Unexpected Spotify API error |

---

### POST /api/resume

**Description:** Resume playback on the active Spotify device.

**Response:** `204 No Content`

#### Errors
| Status | Meaning |
|--------|---------|
| `403` | Spotify Premium required |
| `502` | Unexpected Spotify API error |

---

### POST /api/wildcard/add

**Description:** Award one wildcard to the current player.

**Response:** `200` — `PlayersResponse`

---

### POST /api/wildcard/use

**Description:** Spend one of the current player's wildcards.

**Response:** `200` — `PlayersResponse`

#### Errors
| Status | Meaning |
|--------|---------|
| `409` | Current player has no wildcards available |

---

### POST /api/etl/run

**Description:** Trigger an ETL run for a list of Spotify playlist URIs. Accepts full URIs (`spotify:playlist:<id>`), share URLs, or bare IDs. Returns immediately with `202 Accepted`; poll `GET /api/etl/status` for progress.

**Response:** `202` — `ETLStatusResponse`

#### Request body
| Field | Type | Description |
|-------|------|-------------|
| `playlist_uris` | `list[str]` | 1–20 Spotify playlist URIs, URLs, or IDs |

#### Response body
| Field | Type | Description |
|-------|------|-------------|
| `status` | `"idle"\|"running"\|"done"\|"error"` | Current pipeline state |
| `playlists_processed` | `int` | Number of playlists completed so far |
| `tracks_upserted` | `int` | Total tracks written to DuckDB |
| `error` | `str\|null` | Error message if status is `"error"` |
| `started_at` | `datetime\|null` | UTC timestamp when the run started |
| `finished_at` | `datetime\|null` | UTC timestamp when the run finished |

#### Errors
| Status | Meaning |
|--------|---------|
| `409` | An ETL run is already in progress |
| `422` | `playlist_uris` is empty, contains more than 20 entries, or contains an invalid identifier |

---

### GET /api/etl/status

**Description:** Return the current ETL pipeline status.

**Response:** `200` — `ETLStatusResponse` (see above)

---

### POST /api/playlists/activate

**Description:** Load a DuckDB-stored playlist into the active game track pool and register it in the playlist list. Tracks already in the pool are not duplicated. Does not reset `played_ids`.

#### Request body
| Field | Type | Description |
|-------|------|-------------|
| `playlist_id` | `str` | Spotify playlist ID (must exist in DuckDB) |

**Response:** `200` — `ActivatePlaylistResponse`

#### Response body
| Field | Type | Description |
|-------|------|-------------|
| `tracks_added` | `int` | New tracks merged into the active pool |
| `total_active_tracks` | `int` | Total tracks in the pool after activation |

#### Errors
| Status | Meaning |
|--------|---------|
| `404` | Playlist not found in DuckDB — run ETL first |

---

### GET /api/analytics/songs

**Description:** Return a paginated, filtered list of tracks from DuckDB. `is_active` reflects whether each track is currently in the game's active pool.

#### Query parameters
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `playlist_id` | `str` | — | Filter to a specific playlist |
| `genre` | `str` | — | Filter by genre name (exact match) |
| `year_from` | `int` | — | Minimum release year (inclusive) |
| `year_to` | `int` | — | Maximum release year (inclusive) |
| `limit` | `int` | `50` | Page size (clamped to 1–500) |
| `offset` | `int` | `0` | Pagination offset |

**Response:** `200` — `SongsResponse`

#### Response body
| Field | Type | Description |
|-------|------|-------------|
| `total` | `int` | Total matching tracks (before pagination) |
| `items` | `list[TrackRow]` | Tracks for the current page |

**`TrackRow`**
| Field | Type | Description |
|-------|------|-------------|
| `track_id` | `str` | Spotify track ID |
| `name` | `str` | Track title |
| `artists` | `list[{name: str}]` | Contributing artists |
| `album_name` | `str\|null` | Album title |
| `release_year` | `int\|null` | 4-digit release year |
| `is_active` | `bool` | Whether this track is in the current active pool |

---

### GET /api/analytics/stats

**Description:** Return year and genre distributions plus total track count for the DuckDB library. Optionally filter to a single playlist.

#### Query parameters
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `playlist_id` | `str` | — | Restrict stats to this playlist |

**Response:** `200` — `StatsResponse`

#### Response body
| Field | Type | Description |
|-------|------|-------------|
| `total_tracks` | `int` | Total distinct tracks |
| `year_distribution` | `list[{year: int, count: int}]` | Track count per release year, ascending |
| `genre_distribution` | `list[{genre: str, count: int}]` | Track count per genre, top 50 descending |
| `playlists` | `list[DBPlaylistInfo]` | All playlists in DuckDB, newest first |

**`DBPlaylistInfo`**
| Field | Type | Description |
|-------|------|-------------|
| `playlist_id` | `str` | Spotify playlist ID |
| `name` | `str` | Playlist display name |
| `etl_run_at` | `datetime\|null` | UTC timestamp of the last ETL run |

---

### GET /api/analytics/playlists

**Description:** Return all playlists stored in DuckDB.

**Response:** `200` — `list[DBPlaylistInfo]` (see above)

---

## Game constants

| Constant | Value | Effect |
|----------|-------|--------|
| Starting score | `1` | `POST /api/players/init` calls `GameScore.reset()` which sets `score = 1` — the reference card counts as the first point |
| Starting wildcards | `0` | Each player starts with zero wildcards |
| Earliest reference year | `1960` | `GET /api/reference-year` never returns a year before 1960 |
| Played-track reset | on `POST /api/players/init` | `app.state.played_ids` is cleared; all tracks become eligible again |

The win threshold is configured in the frontend only (`#win-score-select`, default 10). The backend tracks scores but has no win condition — it is up to the client to detect victory.
