"""Pure transformation functions: Spotify dicts → DB row dicts and back."""

import json
from datetime import datetime, timezone


def transform_tracks(
    raw_tracks: list[dict],
    genres_by_artist: dict[str, list[str]],
) -> list[dict]:
    """Convert raw Spotify track dicts to DB row dicts for raw.tracks.

    Genres are the union of all genres across all of the track's artists.
    Deduplicates tracks by track_id.
    """
    seen: set[str] = set()
    rows = []
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S")
    for track in raw_tracks:
        track_id = track.get("id")
        if not track_id or track_id in seen:
            continue
        seen.add(track_id)
        artists = track.get("artists") or []
        all_genres: set[str] = set()
        for artist in artists:
            all_genres.update(genres_by_artist.get(artist.get("id", ""), []))
        album = track.get("album") or {}
        rows.append(
            {
                "track_id": track_id,
                "name": track.get("name", ""),
                "release_year": _parse_year(album.get("release_date", "")),
                "album_name": album.get("name", ""),
                "album_id": album.get("id", ""),
                "artists": json.dumps(
                    [
                        {"id": a.get("id", ""), "name": a.get("name", "")}
                        for a in artists
                    ]
                ),
                "genres": json.dumps(sorted(all_genres)),
                "inserted_at": now,
                "updated_at": now,
            }
        )
    return rows


def db_row_to_game_track(row: dict) -> dict:
    """Convert a raw.tracks row to the game's expected track dict format.

    The game expects: {id, name, artists: [{name}], album: {release_date}}.
    """
    artists_raw = row.get("artists") or "[]"
    if isinstance(artists_raw, str):
        artists_data = json.loads(artists_raw)
    else:
        artists_data = list(artists_raw)
    release_year = row.get("release_year")
    return {
        "id": row["track_id"],
        "name": row["name"],
        "artists": [{"name": a.get("name", "")} for a in artists_data],
        "album": {"release_date": f"{release_year}-01-01" if release_year else ""},
    }


def _parse_year(release_date: str) -> int | None:
    """Extract the 4-digit year from a Spotify release_date string."""
    try:
        return int(str(release_date)[:4])
    except (ValueError, TypeError):
        return None
