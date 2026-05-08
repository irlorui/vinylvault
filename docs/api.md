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

### POST /api/score/reset

**Description:** Resets the session score to 1. The reference card counts as the first point, so a fresh game always starts at 1.

**Response:** `200` — `ScoreResponse`

#### Response body
| Field | Type | Description |
|-------|------|-------------|
| `score` | `int` | Current score (always `1` after reset) |
| `won` | `bool` | Whether the win threshold has been reached (always `false` after reset) |

---

### POST /api/score/add

**Description:** Adds one point for a correct card placement and returns the updated score. Sets `won` to `true` when `score` reaches `WIN_SCORE`.

**Response:** `200` — `ScoreResponse`

#### Response body
| Field | Type | Description |
|-------|------|-------------|
| `score` | `int` | Updated score |
| `won` | `bool` | `true` if `score >= WIN_SCORE` (see [Game constants](#game-constants)) |

---

### GET /api/song

**Description:** Returns a random track from the playlist that was loaded at startup. The track list is cached in memory — no Spotify API call is made per request.

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
| `404` | Playlist contains no playable tracks |

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

**Description:** Starts playback of the given track on the pinned device. A device must have been pinned via `PUT /api/device/{device_id}` first.

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

## Game constants

| Constant | Value | Effect |
|----------|-------|--------|
| `WIN_SCORE` | `4` | `POST /api/score/add` returns `won: true` when `score >= 4`. Defined in `src/backend/score.py`. |

The score starts at `1` after `POST /api/score/reset` (the reference card). Each correct placement adds `1`. At `score == 4` the game is over.
