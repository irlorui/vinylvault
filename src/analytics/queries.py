"""DuckDB query functions for the analytics layer."""

import logging

from src.etl.db import DuckDBClient

logger = logging.getLogger(__name__)


def get_tracks(
    db: DuckDBClient,
    active_ids: set[str],
    playlist_id: str | None = None,
    genre: str | None = None,
    year_from: int | None = None,
    year_to: int | None = None,
    limit: int = 50,
    offset: int = 0,
) -> tuple[int, list[dict]]:
    """Return (total, items) for a filtered, paginated track listing."""
    try:
        joins, where, params = _build_query_parts(
            playlist_id, genre, year_from, year_to
        )

        count_sql = (
            f"SELECT COUNT(DISTINCT t.track_uri) FROM raw.tracks t{joins}{where}"
        )
        count_result = db.connection.execute(
            count_sql, params if params else None
        ).fetchone()
        total = int(count_result[0]) if count_result else 0

        sql = (
            f"SELECT t.track_uri AS track_id, t.name, t.release_year, t.album_name, "
            f"list(ar.name) FILTER (WHERE ar.name IS NOT NULL) AS artists "
            f"FROM raw.tracks t{joins} "
            f"LEFT JOIN raw.tracks_artists ta ON t.id = ta.track_id "
            f"LEFT JOIN raw.artists ar ON ta.artist_id = ar.id "
            f"{where} "
            f"GROUP BY t.track_uri, t.name, t.release_year, t.album_name "
            f"ORDER BY t.release_year NULLS LAST, t.name "
            f"LIMIT {int(limit)} OFFSET {int(offset)}"
        )
        rows = (
            db.connection.execute(sql, params if params else None)
            .fetchdf()
            .to_dict("records")
        )

        items = []
        for row in rows:
            artists = row.get("artists") or []
            items.append(
                {
                    "track_id": row["track_id"],
                    "name": row["name"],
                    "artists": [{"name": n} for n in artists],
                    "album_name": row.get("album_name"),
                    "release_year": row.get("release_year"),
                    "is_active": row["track_id"] in active_ids,
                }
            )
        return total, items
    except Exception as e:
        logger.warning("get_tracks query failed: %s", e)
        return 0, []


def get_stats(db: DuckDBClient, playlist_uri: str | None = None) -> dict:
    """Return year distribution, genre distribution, total, and playlist list."""
    try:
        joins = _playlist_joins(playlist_uri)
        base_params = [playlist_uri] if playlist_uri else []
        playlist_cond = "p.playlist_uri = ? AND " if playlist_uri else ""
        filter_where = "WHERE p.playlist_uri = ?" if playlist_uri else ""

        year_sql = (
            f"SELECT release_year, COUNT(*) as count "
            f"FROM raw.tracks t{joins} "
            f"WHERE {playlist_cond}t.release_year IS NOT NULL "
            f"GROUP BY release_year ORDER BY release_year"
        )
        year_rows = (
            db.connection.execute(year_sql, base_params if base_params else None)
            .fetchdf()
            .to_dict("records")
        )

        genre_sql = (
            f"SELECT g.name, COUNT(DISTINCT ta.track_id) AS count "
            f"FROM raw.genres g "
            f"JOIN raw.artists_genres ag ON g.id = ag.genre_id "
            f"JOIN raw.tracks_artists ta ON ag.artist_id = ta.artist_id "
            f"JOIN raw.tracks t ON ta.track_id = t.id "
            f"{joins} "
            f"{filter_where} "
            f"GROUP BY g.name ORDER BY count DESC LIMIT 50"
        )
        genre_rows = (
            db.connection.execute(genre_sql, base_params if base_params else None)
            .fetchdf()
            .to_dict("records")
        )

        total_sql = (
            f"SELECT COUNT(DISTINCT t.track_uri)"
            f" FROM raw.tracks t{joins} {filter_where}"
        )
        total_result = db.connection.execute(
            total_sql, base_params if base_params else None
        ).fetchone()
        total = int(total_result[0]) if total_result else 0

        try:
            playlist_rows = (
                db.connection.execute(
                    "SELECT playlist_uri AS playlist_id, name, etl_run_at"
                    " FROM raw.playlists ORDER BY etl_run_at DESC"
                )
                .fetchdf()
                .to_dict("records")
            )
        except Exception:
            playlist_rows = []

        return {
            "total_tracks": total,
            "year_distribution": [
                {"year": int(r["release_year"]), "count": int(r["count"])}
                for r in year_rows
            ],
            "genre_distribution": [
                {"genre": r["name"], "count": int(r["count"])} for r in genre_rows
            ],
            "playlists": playlist_rows,
        }
    except Exception as e:
        logger.warning("get_stats query failed: %s", e)
        return {
            "total_tracks": 0,
            "year_distribution": [],
            "genre_distribution": [],
            "playlists": [],
        }


def get_playlist_tracks_for_game(db: DuckDBClient, playlist_uri: str) -> list[dict]:
    """Fetch tracks for a playlist from DuckDB in the game's track dict format."""
    return (
        db.connection.execute(
            "SELECT t.track_uri AS track_id, t.name, t.release_year, "
            "list(a.name) FILTER (WHERE a.name IS NOT NULL) AS artists "
            "FROM raw.tracks t "
            "JOIN raw.playlist_tracks pt ON t.id = pt.track_id "
            "JOIN raw.playlists p ON pt.playlist_id = p.id "
            "LEFT JOIN raw.tracks_artists ta ON t.id = ta.track_id "
            "LEFT JOIN raw.artists a ON ta.artist_id = a.id "
            "WHERE p.playlist_uri = ? "
            "GROUP BY t.track_uri, t.name, t.release_year, pt.position "
            "ORDER BY pt.position",
            [playlist_uri],
        )
        .fetchdf()
        .to_dict("records")
    )


def get_db_playlists(db: DuckDBClient) -> list[dict]:
    """Return all playlists stored in DuckDB."""
    try:
        return (
            db.connection.execute(
                "SELECT playlist_uri AS playlist_id, name, etl_run_at"
                " FROM raw.playlists ORDER BY etl_run_at DESC"
            )
            .fetchdf()
            .to_dict("records")
        )
    except Exception as e:
        logger.warning("get_db_playlists failed: %s", e)
        return []


# ─── Helpers ───────────────────────────────────────────────────────────────


def _playlist_joins(playlist_uri: str | None) -> str:
    """Return JOIN clauses to filter by playlist URI via integer PKs."""
    if playlist_uri:
        return (
            " JOIN raw.playlist_tracks pt ON t.id = pt.track_id"
            " JOIN raw.playlists p ON pt.playlist_id = p.id"
        )
    return ""


def _build_query_parts(
    playlist_uri: str | None,
    genre: str | None,
    year_from: int | None,
    year_to: int | None,
) -> tuple[str, str, list]:
    """Return (joins, where_clause, params_list) for a track query."""
    joins = _playlist_joins(playlist_uri)
    conditions = []
    params: list = []

    if playlist_uri:
        conditions.append("p.playlist_uri = ?")
        params.append(playlist_uri)
    if year_from is not None:
        conditions.append("t.release_year >= ?")
        params.append(year_from)
    if year_to is not None:
        conditions.append("t.release_year <= ?")
        params.append(year_to)
    if genre:
        joins += (
            " JOIN raw.tracks_artists ta_g ON t.id = ta_g.track_id"
            " JOIN raw.artists_genres ag_g ON ta_g.artist_id = ag_g.artist_id"
            " JOIN raw.genres g_f ON ag_g.genre_id = g_f.id"
        )
        conditions.append("g_f.name = ?")
        params.append(genre)

    where = (" WHERE " + " AND ".join(conditions)) if conditions else ""
    return joins, where, params
