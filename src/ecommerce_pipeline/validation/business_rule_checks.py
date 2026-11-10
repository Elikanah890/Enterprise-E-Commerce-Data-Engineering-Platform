"""Business-rule checks derived from the profiling report."""

from __future__ import annotations

import pandas as pd


def check_non_negative(df: pd.DataFrame, columns: list[str]) -> dict:
    """Return counts of negative values per column."""
    return {
        column: int((pd.to_numeric(df[column], errors="coerce") < 0).sum())
        for column in columns
    }


def check_date_order(
    df: pd.DataFrame,
    earlier: str,
    later: str,
) -> int:
    """Count rows where ``earlier`` is after ``later``."""
    left = pd.to_datetime(df[earlier], errors="coerce")
    right = pd.to_datetime(df[later], errors="coerce")
    return int((left > right).sum())


def check_domain(df: pd.DataFrame, column: str, allowed: set[str]) -> list[str]:
    """Return values outside an allowed domain."""
    values = set(df[column].dropna().astype(str).unique())
    return sorted(values - allowed)
