# Add Tests Skill

Add or extend tests for a VinylVault backend component.

## Usage
```
/add-tests [source_file_or_component]
```

Examples:
- `/add-tests src/backend/spotify.py`
- `/add-tests the score reset endpoint`

## Behavior

1. **Identify the target** — use the argument if provided; otherwise infer from `git diff HEAD` which files changed and need new/updated tests.

2. **Read the source file** to understand all functions, classes, and error cases.

3. **Read existing test patterns** — read `tests/conftest.py` for available fixtures (`client`, `mock_sp`, `SAMPLE_TRACKS`) and scan existing `tests/test_*.py` files for naming conventions and mocking style.

4. **Write tests** — add to the matching `tests/test_<module>.py` (create it if it does not exist). Follow these rules:
   - Use the `client` fixture for endpoint tests; use raw `MagicMock(spec=spotipy.Spotify)` for unit tests on spotify.py functions.
   - Mock Spotify at the import site: `patch("src.backend.main.get_spotify_client", ...)`.
   - Test both happy paths and all documented error codes (404, 503, 403).
   - Name tests `test_<what>_<expected_outcome>`, e.g. `test_play_returns_503_without_device`.
   - No docstrings on test functions — the name is the doc.

5. **Run `make test`** — iterate until all tests pass. Fix failures before moving on.

6. **Run `make pre-commit`** — fix any ruff lint or format issues.

## Key fixtures (from `tests/conftest.py`)

| Fixture | Scope | What it provides |
|---------|-------|-----------------|
| `mock_sp` | function | `MagicMock(spec=spotipy.Spotify)` with one active device |
| `client` | function | `TestClient(app)` with mocked lifespan — fresh state per test |
| `SAMPLE_TRACKS` | module | Two sample track dicts matching Spotify's API shape |

## Mocking SpotifyException

```python
from spotipy.exceptions import SpotifyException
exc = SpotifyException(http_status=403, code=-1, msg="Premium required")
mock_sp.pause_playback.side_effect = exc
```

## Adding a custom client fixture for edge cases

When a test needs different app state (e.g. empty tracks, no device), create a local client instead of using the shared fixture:

```python
def test_get_song_404_when_no_tracks(mock_sp):
    with (
        patch("src.backend.main.get_spotify_client", return_value=mock_sp),
        patch("src.backend.main.fetch_all_tracks", return_value=[]),
    ):
        with TestClient(app) as c:
            res = c.get("/api/song")
    assert res.status_code == 404
```
