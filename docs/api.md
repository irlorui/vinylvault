# API Reference

Base URL: `http://127.0.0.1:8000`

All endpoints return JSON unless the response is `204 No Content`. Error bodies follow FastAPI's default shape: `{"detail": "<message>"}`.

---

## Endpoints

### GET /api/reference-year

**Description:** Returns a random year between 1960 and the current year to use as the timeline anchor card.

**Response:** `200` — `ReferenceYearResponse`

#### Response body
| Field | Type | Description |
|-------|------|-------------|
| `year` | `int` | Random anchor year in the range [1960, current year] |

---

### POST /api/players/init

**Description:** Initialises all players for a new game. Resets every player's score to 1 (the reference card counts as the first point) and wildcards to 0. Sets the current player to index 0.

**Request body:** `InitPlayersRequest`

| Field | Type | Description |
|-------|------|-------------|
| `names` | `list[str]` | Player names, 1–4 entries required |

**Response:** `200` — `PlayersResponse`

#### Response body
| Field | Type | Description |
|-------|------|-------------|
| `players` | `list[PlayerState]` | All players in order; see schema below |
| `current_player_index` | `int` | Index into `players` of the player whose turn it is (always `0` after init) |

**`PlayerState` schema**
| Field | Type | Description |
|-------|------|-------------|
| `name` | `str` | Player name |
| `score` | `int` | Current score |
| `wildcards` | `int` | Available wildcards |

#### Errors
| Status | Meaning |
|--------|---------|
| `422` | `names` list is empty or has more than 4 entries |

---

### POST /api/turn/next

**Description:** Advances to the next player's turn, wrapping around to the first player after the last.

**Response:** `200` — `PlayersResponse` (see schema above)

---

### POST /api/score/add

**Description:** Adds one point to the current player's score and returns the updated state for all players.

**Response:** `200` — `PlayersResponse` (see schema above)

---

### GET /api/song

**Description:** Returns a random track from the playlist cached at startup. Tracks with malformed Spotify metadata (missing artists, invalid release date, `null` album) are automatically skipped. No Spotify API call is made per request.

**Query parameter:** `exclude` — comma-separated Spotify track IDs to exclude (e.g. `?exclude=id1,id2`). Used to prevent the same track from appearing twice in one player's timeline.

**Response:** `200` — `TrackResponse`

#### Response body
| Field | Type | Description |
|-------|------|-------------|
| `track_id` | `str` | Spotify track ID |
| `name` | `str` | Track title |
| `artist` | `str` | Primary artist name |
| `year` | `str` | 4-digit release year extracted from the album's `release_date` |

#### Errors
| Status | Meaning |
|--------|---------|
| `404` | No playable tracks remain after applying the exclude filter and skipping malformed entries |

---

### GET /api/devices

**Description:** Returns all Spotify playback devices currently available to the authenticated user. Returns an empty list if no devices are open.

**Response:** `200` — `list[DeviceResponse]`

#### Response body (each item)
| Field | Type | Description |
|-------|------|-------------|
| `device_id` | `str` | Spotify device ID |
| `name` | `str` | Human-readable device name |
| `is_active` | `bool` | Whether Spotify is currently playing on this device |

---

### PUT /api/device/{device_id}

**Description:** Pins a Spotify device to use for all subsequent playback calls. Must be called before `POST /api/play/{track_id}`.

**Path parameter:** `device_id` — Spotify device ID (from `GET /api/devices`)

**Response:** `204 No Content`

---

### POST /api/play/{track_id}

**Description:** Starts playback of the given track on the pinned device.

**Path parameter:** `track_id` — Spotify track ID (from `GET /api/song`)

**Response:** `204 No Content`

#### Errors
| Status | Meaning |
|--------|---------|
| `503` | No device pinned — call `PUT /api/device/{device_id}` first |
| `403` | Spotify Premium is required for playback |

---

### POST /api/pause

**Description:** Pauses playback on the active Spotify device.

**Response:** `204 No Content`

#### Errors
| Status | Meaning |
|--------|---------|
| `403` | Spotify Premium is required |

---

### POST /api/resume

**Description:** Resumes playback on the active Spotify device.

**Response:** `204 No Content`

#### Errors
| Status | Meaning |
|--------|---------|
| `403` | Spotify Premium is required |

---

### POST /api/wildcard/add

**Description:** Awards one wildcard to the current player. Called after a correct song-name guess during the REVEAL phase.

**Response:** `200` — `PlayersResponse` (see schema above)

---

### POST /api/wildcard/use

**Description:** Spends one of the current player's wildcards to skip the current song and draw a new one.

**Response:** `200` — `PlayersResponse` (see schema above)

#### Errors
| Status | Meaning |
|--------|---------|
| `409` | Current player has no wildcards available |

---

## Win threshold

The win threshold is **frontend-only**. The backend never compares scores against a threshold or signals a win — it only increments per-player `score` values. The frontend reads `game.winScore` (default `10`, configurable in the CONFIG panel before the game starts) and transitions to the `won` phase when `currentPlayer().score >= game.winScore`.
