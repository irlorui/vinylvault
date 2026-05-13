"""CSV reader utilities for VinylVault."""

import csv
from pathlib import Path


def read_playlist_ids(csv_path: Path) -> list[str]:
    """Read playlist IDs from a CSV file.

    Args:
        csv_path: Path to a CSV file with a `playlist_id` column.

    Returns:
        Deduplicated list of playlist IDs, preserving order.

    Raises:
        FileNotFoundError: If the CSV file does not exist.
        KeyError: If the CSV has no `playlist_id` column.
    """
    if not csv_path.exists():
        raise FileNotFoundError(f"Playlist CSV not found: {csv_path}")
    seen: set[str] = set()
    ids: list[str] = []
    with csv_path.open(newline="", encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        for row in reader:
            pid = row["playlist_id"].strip()
            if pid and pid not in seen:
                seen.add(pid)
                ids.append(pid)
    return ids
