"""Duplicate analysis."""

from __future__ import annotations

import pandas as pd


def duplicate_row_count(df: pd.DataFrame) -> int:
    """Return the number of exact duplicate rows beyond the first."""
    return int(df.duplicated().sum())


def duplicate_key_count(df: pd.DataFrame, keys: list[str]) -> int:
    """Return the number of rows beyond the first for a candidate key."""
    return int(df.duplicated(subset=keys).sum())


def duplicate_summary(df: pd.DataFrame, keys: list[str] | None = None) -> dict:
    """Return row and key duplicate counts."""
    result = {"rows": len(df), "duplicate_rows": duplicate_row_count(df)}
    if keys:
        result["key"] = keys
        result["duplicate_keys"] = duplicate_key_count(df, keys)
    return result
