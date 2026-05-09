# 🎵 VinylVault

A party game for music nerds. 

Listen to a random track from your Spotify playlist and place it in the right spot on a growing timeline — no peeking at the year!

Built with **FastAPI** + **spotipy** on the backend and plain HTML/CSS/JS on the frontend.

**TODO: Add screenshot or gif**

---

## 🛠️ Setup

### 1. Configurate your Spotify app

To run Vinyl Vault you need to set up an app in [developer.spotify.com/dashboard](https://developer.spotify.com/dashboard). This is completely free but requires a Spotify Premium account.

Full How-to guide is available at [docs/how_to_setup_spotify_app.md](docs/how_to_setup_spotify_app.md).

> **Note:** playback requires Spotify Premium and an active device (desktop app, phone, etc.).

### 2. Install dependencies

You need [uv](https://docs.astral.sh/uv/getting-started/installation/) installed.

```bash
make setup
```

### 3. Run the app

```bash
make run
```

Open [http://127.0.0.1:8000](http://127.0.0.1:8000) in your browser. On first run, Spotify will open a browser tab asking you to authorise the app — follow the prompt and you're good to go.

> **Note:** Remember to be logged in either in Web browser or Spotify Desktop in at least one of your devices.

---

## 🎮 How to play

1. Click **START** — a random reference year is placed on your timeline as the anchor card.
2. Click **NEW SONG** — a face-down card appears. Listen to the track and drag the card to where you think it belongs in the timeline.
3. Click **REVEAL** — if your placement is chronologically correct the card stays; if not, it disappears.
4. Reach **4 correct cards** (including the reference) and you win! 🏆

Full rules and a game-flow diagram are in [docs/game_rules.md](docs/game_rules.md).

---

## 🏗️ Architecture

```
src/
  backend/
    config.py     # loads .config/.env credentials
    models.py     # Pydantic response models (TrackResponse, ScoreResponse, …)
    score.py      # GameScore and GameWildcard classes
    spotify.py    # spotipy client, get_random_track, play/pause/resume
    main.py       # FastAPI app + static file serving
  frontend/
    index.html / script.js / styles.css
docs/             # documentation on project
```

**API endpoints** — full reference in [docs/api.md](docs/api.md):

| Method | Path | Description |
|--------|------|-------------|
| `GET`  | `/api/reference-year` | Random anchor year (1960 – now) |
| `POST` | `/api/score/reset` | Reset score to 1 (new game) |
| `POST` | `/api/score/add` | Add a point → `{score, won}` |
| `GET`  | `/api/song` | Random track from the cached playlist |
| `GET`  | `/api/devices` | List available Spotify devices |
| `PUT`  | `/api/device/{device_id}` | Pin a device for playback |
| `POST` | `/api/play/{track_id}` | Start playback on the pinned device |
| `POST` | `/api/pause` | Pause playback |
| `POST` | `/api/resume` | Resume playback |
| `POST` | `/api/wildcard/reset` | Reset wildcard count (new game) |
| `POST` | `/api/wildcard/add` | Award 1 wildcard |
| `POST` | `/api/wildcard/use` | Spend 1 wildcard → 409 if empty |

---

## 🧑‍💻 Contributing

### Before you push

Run the full pre-commit suite and make sure everything passes:

```bash
make pre-commit   # pre-commit hooks + ruff lint + ruff format check
make ruff-format  # auto-format code (run this if format check fails)
```

### Commit messages

This project uses [Conventional Commits](https://www.conventionalcommits.org/) and [Semantic Release](https://semantic-release.gitbook.io/) to automate versioning and changelogs. Your commit message type determines the next version number — use the right type:

| Type | When to use | Version bump |
|------|-------------|--------------|
| `feat` | New feature visible to users | minor (`1.1.0`) |
| `fix` | Bug fix | patch (`1.0.1`) |
| `feat!` / `fix!` | Breaking change (add `!` or `BREAKING CHANGE:` footer) | major (`2.0.0`) |
| `docs` | Documentation only | none |
| `refactor` | Code change with no behaviour change | none |
| `chore` | Tooling, deps, config | none |

**Format:**
```
<type>(<optional scope>): <short description>

[optional body]

[optional footer]
```

**Examples:**
```
feat(api): add /api/devices endpoint for Spotify device selection

fix(frontend): prevent score pips from showing in idle phase

docs: add Spotify app setup guide to docs/

feat!: require device selection before starting game

BREAKING CHANGE: /api/play now returns 503 if no device is pinned
```

### Opening a pull request

1. Create a branch from `main` with a descriptive release name `release/v{semantic_release_version}`:
   ```bash
   git checkout -b feat/my-release-branch
   ```
2. Make your changes, run `make pre-commit`, and commit using the format above.
3. Push your branch and open a PR against `main`.
4. Wait for a review before merging. At least one approval is required. Address any comments and push additional commits to the same branch (do not force-push after review starts).
5. Merge via **Squash and merge** to keep the history clean.
