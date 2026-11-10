"""Dataset inventory: file sizes, row counts, and column counts."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from ..config.settings import RAW_DIR, RAW_FILES
from ..ingestion.csv_reader import read_csv


def build_inventory(raw_dir: str | Path | None = None) -> pd.DataFrame:
    """Build an inventory table for all raw CSVs.

    Returns a DataFrame with one row per file and the columns:
    ``file``, ``entity``, ``rows``, ``columns``, ``size_bytes``, ``size_mb``.
    """
    directory = Path(raw_dir or RAW_DIR)
    rows = []
    for entity, filename in RAW_FILES.items():
        path = directory / filename
        if not path.exists():
            rows.append(
                {
                    "file": filename,
                    "entity": entity,
                    "rows": None,
                    "columns": None,
                    "size_bytes": None,
                    "size_mb": None,
                }
            )
            continue
        df = read_csv(path)
        size_bytes = path.stat().st_size
        rows.append(
            {
                "file": filename,
                "entity": entity,
                "rows": len(df),
                "columns": len(df.columns),
                "size_bytes": size_bytes,
                "size_mb": round(size_bytes / 1_000_000, 2),
            }
        )
    return pd.DataFrame(rows)
