# 🎵 VinylVault

A party game for music nerds. 

Fun game to guess name, year and artist for random played songs from a provided Spotify playlist.

Built with Spotify, FastAPI.

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

Open [http://localhost:8000](http://localhost:8000) in your browser. On first run, Spotify will open a browser tab asking you to authorise the app — follow the prompt and you're good to go.

> **Note:** playback requires Spotify Premium and an active device (desktop app, phone, etc.).

---

## 🎮 How to play

1. Click **Get Song** — a random track from your playlist starts playing on your active Spotify device.
2. Guess the **song name**, **artist**, and **year**.
3. Reveal the answer and see how you did!

---

## 🏗️ Architecture

```
src/
  backend/
    config.py     # loads .config/.env credentials
    models.py     # Pydantic response models
    spotify.py    # spotipy client, get_random_track, play_track
    main.py       # FastAPI app + static file serving
  frontend/
    index.html / script.js / styles.css
```

**API endpoints:**

| Method | Path | Description |
|--------|------|-------------|
| `GET`  | `/api/song` | Returns a random track from the playlist |
| `POST` | `/api/play/{track_id}` | Triggers playback on the active device |

---

## 🧑‍💻 Development

```bash
make pre-commit   # run pre-commit hooks + ruff lint + format check
make ruff-format  # auto-format code with ruff
```

Commits follow [Conventional Commits](https://www.conventionalcommits.org/).