"""Primary-key checks."""

from __future__ import annotations

import pandas as pd


def duplicate_key_count(df: pd.DataFrame, keys: list[str]) -> int:
    """Return the number of rows beyond the first for a candidate key."""
    return int(df.duplicated(subset=keys).sum())


def is_unique_key(df: pd.DataFrame, keys: list[str]) -> bool:
    """Return True when the candidate key has no duplicates and no nulls."""
    if df[keys].isna().any().any():
        return False
    return not df.duplicated(subset=keys).any()
