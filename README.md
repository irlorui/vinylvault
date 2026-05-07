# 🎵 VinylVault

A party game for music nerds. 

Listen to a random track from your Spotify playlist and place it in the right spot on a growing timeline — no peeking at the year!

Built with **FastAPI** + **spotipy** on the backend and plain HTML/CSS/JS on the frontend.

**TODO: Add screenshot or gif**

---

## 🛠️ Setup

### 1. Get your Spotify credentials

Go to [developer.spotify.com/dashboard](https://developer.spotify.com/dashboard), create an app, and grab your **Client ID** and **Client Secret**.

In your app settings, add this redirect URI:
```
https://localhost:8888/callback
```

### 2. Configure your environment

Copy `.config/.env.example` to `.config/.env` and fill it in:

```env
SPOTIPY_CLIENT_ID=your_client_id_here
SPOTIPY_CLIENT_SECRET=your_client_secret_here
SPOTIPY_REDIRECT_URI=https://localhost:8888/callback
PLAYLIST_ID=your_playlist_id_here
```

Your `PLAYLIST_ID` is the string in a Spotify playlist URL:
`https://open.spotify.com/playlist/`**`AAAAABBBBCCCC12345`**

### 3. Install dependencies

You need [uv](https://docs.astral.sh/uv/getting-started/installation/) installed.

```bash
make setup
```

### 4. Run the app

```bash
make run
```

Open [http://127.0.0.1:8000](http://127.0.0.1:8000) in your browser. On first run, Spotify will open a browser tab asking you to authorise the app — follow the prompt and you're good to go.

> **Note:** playback requires Spotify Premium and an active device (desktop app, phone, etc.).

---

## 🎮 How to play

1. Click **START** — a random reference year is placed on your timeline as the anchor card.
2. Click **NEW SONG** — a face-down card appears. Listen to the track and drag the card to where you think it belongs in the timeline.
3. Click **REVEAL** — if your placement is chronologically correct the card stays; if not, it disappears.
4. Reach **4 correct cards** (including the reference) and you win! 🏆

Full rules and a game-flow diagram are in [docs/game-mechanics.md](docs/game-mechanics.md).

---

## 🏗️ Architecture

```
src/
  backend/
    config.py     # loads .config/.env credentials
    models.py     # Pydantic response models (TrackResponse, ScoreResponse, …)
    score.py      # GameScore class — tracks points and win condition
    spotify.py    # spotipy client, get_random_track, play/pause/resume
    main.py       # FastAPI app + static file serving
  frontend/
    index.html / script.js / styles.css
docs/
  game-mechanics.md   # game rules and flow diagrams
```

**API endpoints:**

| Method | Path | Description |
|--------|------|-------------|
| `GET`  | `/api/song` | Random track from the playlist |
| `GET`  | `/api/reference-year` | Random anchor year (1950 – now) |
| `POST` | `/api/play/{track_id}` | Start playback on the active device |
| `POST` | `/api/pause` | Pause playback |
| `POST` | `/api/resume` | Resume playback |
| `POST` | `/api/score/reset` | Reset score to 1 (new game) |
| `POST` | `/api/score/add` | Add a point and return `{score, won}` |

---

## 🧑‍💻 Development

```bash
make pre-commit   # run pre-commit hooks + ruff lint + format check
make ruff-format  # auto-format code with ruff
```

Commits follow [Conventional Commits](https://www.conventionalcommits.org/).
