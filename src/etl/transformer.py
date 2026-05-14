"""Pure transformation functions: Spotify dicts → DB row dicts and back."""

from datetime import datetime, timezone


def transform_tracks(raw_tracks: list[dict]) -> list[dict]:
    """Convert raw Spotify track dicts to DB row dicts for raw.tracks.

    Deduplicates by track_id. Artists and genres are stored in separate
    linking tables (tracks_artists, artists_genres) and not included here.
    """
    seen: set[str] = set()
    rows = []
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S")
    for track in raw_tracks:
        track_id = track.get("id")
        if not track_id or track_id in seen:
            continue
        seen.add(track_id)
        album = track.get("album") or {}
        rows.append(
            {
                "track_uri": track_id,
                "name": track.get("name", ""),
                "release_year": _parse_year(album.get("release_date", "")),
                "album_name": album.get("name", ""),
                "album_id": album.get("id", ""),
                "inserted_at": now,
                "updated_at": now,
            }
        )
    return rows


def db_row_to_game_track(row: dict) -> dict:
    """Convert a raw.tracks row (with joined artists list) to game track format.

    The game expects: {id, name, artists: [{name}], album: {release_date}}.
    The `artists` field may be a Python list (from DuckDB list() aggregate)
    or a JSON string from older callers.
    """
    import json

    artists_raw = row.get("artists")
    if artists_raw is None:
        artists_data = []
    elif isinstance(artists_raw, str):
        try:
            artists_data = json.loads(artists_raw)
        except (json.JSONDecodeError, TypeError):
            artists_data = []
    else:
        artists_data = list(artists_raw)

    release_year = row.get("release_year")
    return {
        "id": row.get("track_id") or row.get("track_uri", ""),
        "name": row["name"],
        "artists": [
            {"name": a if isinstance(a, str) else a.get("name", "")}
            for a in artists_data
        ],
        "album": {"release_date": f"{release_year}-01-01" if release_year else ""},
    }


def _parse_year(release_date: str) -> int | None:
    """Extract the 4-digit year from a Spotify release_date string."""
    try:
        return int(str(release_date)[:4])
    except (ValueError, TypeError):
        return None
