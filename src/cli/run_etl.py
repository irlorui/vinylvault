"""CLI runner for the VinylVault ETL pipeline."""

import argparse
import logging
import sys
from pathlib import Path

from src.etl.db import DuckDBClient
from src.etl.models import ETLRunRequest

logging.basicConfig(level=logging.INFO, format="%(levelname)s  %(message)s")

_DEFAULT_CSV = Path("data/playlists.csv")


def main() -> None:
    """Run the ETL pipeline for one or more Spotify playlists.

    Pass --migrate to only apply DB migrations without processing any playlists.
    """
    parser = argparse.ArgumentParser(
        description="Run VinylVault ETL for one or more Spotify playlists."
    )
    parser.add_argument(
        "playlist_uris",
        nargs="*",
        help="Spotify playlist URI (spotify:playlist:ID), URL, or bare ID. "
        "If omitted, reads from --csv (default: data/playlists.csv).",
    )
    parser.add_argument(
        "--migrate",
        action="store_true",
        help="Run DB migrations only, without fetching any playlists",
    )
    parser.add_argument(
        "--csv",
        metavar="PATH",
        type=Path,
        default=_DEFAULT_CSV,
        help="CSV file with a playlist_id column (default: data/playlists.csv)",
    )
    args = parser.parse_args()

    db = DuckDBClient()

    if args.migrate:
        db.run_migrations()
        print("Migrations applied successfully.")
        return

    playlist_uris = list(args.playlist_uris)

    if not playlist_uris:
        from src.utils.csv_reader import read_playlist_ids

        try:
            playlist_uris = read_playlist_ids(args.csv)
        except FileNotFoundError as e:
            print(f"Error: {e}", file=sys.stderr)
            print(
                "Provide playlist URIs as arguments or create data/playlists.csv.",
                file=sys.stderr,
            )
            sys.exit(1)
        except KeyError:
            print(
                f"Error: CSV at {args.csv} has no 'playlist_id' column.",
                file=sys.stderr,
            )
            sys.exit(1)

        if not playlist_uris:
            print("No playlist IDs found in CSV.", file=sys.stderr)
            sys.exit(1)

    try:
        req = ETLRunRequest(playlist_uris=playlist_uris)
    except Exception as e:
        print(f"Invalid playlist URI: {e}", file=sys.stderr)
        sys.exit(1)

    from src.backend.spotify import get_spotify_client
    from src.etl.pipeline import run_etl

    sp = get_spotify_client()
    status: dict = {
        "status": "running",
        "playlists_processed": 0,
        "tracks_upserted": 0,
        "error": None,
        "started_at": None,
        "finished_at": None,
    }

    run_etl(req.playlist_uris, sp, db, status)

    if status["status"] == "error":
        print(f"\nETL failed: {status['error']}", file=sys.stderr)
        sys.exit(1)

    print(
        f"\nDone — {status['playlists_processed']} playlist(s), "
        f"{status['tracks_upserted']} tracks upserted."
    )


if __name__ == "__main__":
    main()
