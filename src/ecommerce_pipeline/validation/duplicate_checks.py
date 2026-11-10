"""Duplicate checks."""

from __future__ import annotations

import pandas as pd


def duplicate_row_count(df: pd.DataFrame) -> int:
    """Return exact duplicate row count beyond the first."""
    return int(df.duplicated().sum())


def assert_no_duplicate_rows(df: pd.DataFrame, table: str = "table") -> None:
    """Raise ValueError when exact duplicate rows exist."""
    count = duplicate_row_count(df)
    if count:
        raise ValueError(f"{table}: {count} exact duplicate rows")
