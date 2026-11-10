"""File utilities."""

from __future__ import annotations

from pathlib import Path


def ensure_dir(path: str | Path) -> Path:
    """Create a directory if it does not exist and return it."""
    directory = Path(path)
    directory.mkdir(parents=True, exist_ok=True)
    return directory


def file_size_mb(path: str | Path) -> float:
    """Return file size in decimal megabytes."""
    return round(Path(path).stat().st_size / 1_000_000, 2)


def list_csv_files(directory: str | Path) -> list[Path]:
    """Return CSV files in a directory, sorted by name."""
    return sorted(Path(directory).glob("*.csv"))
