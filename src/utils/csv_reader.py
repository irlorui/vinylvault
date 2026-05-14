"""CSV reader utilities for VinylVault."""

import csv
from pathlib import Path


def read_column(csv_path: Path, column: str) -> list[str]:
    """Read a single column from a CSV file, deduplicated and stripped.

    Args:
        csv_path: Path to the CSV file.
        column: Header name of the column to extract.

    Returns:
        Deduplicated list of non-empty values, preserving order.

    Raises:
        FileNotFoundError: If the CSV file does not exist.
        KeyError: If the CSV has no column with the given name.
    """
    if not csv_path.exists():
        raise FileNotFoundError(f"CSV not found: {csv_path}")
    seen: set[str] = set()
    values: list[str] = []
    with csv_path.open(newline="", encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        for row in reader:
            val = row[column].strip()
            if val and val not in seen:
                seen.add(val)
                values.append(val)
    return values


def read_playlist_ids(csv_path: Path) -> list[str]:
    """Read playlist IDs from the playlist_id column of a CSV file.

    Args:
        csv_path: Path to a CSV file with a `playlist_id` column.

    Returns:
        Deduplicated list of playlist IDs, preserving order.

    Raises:
        FileNotFoundError: If the CSV file does not exist.
        KeyError: If the CSV has no `playlist_id` column.
    """
    return read_column(csv_path, "playlist_id")
