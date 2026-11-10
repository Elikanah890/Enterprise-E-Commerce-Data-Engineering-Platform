"""Null checks."""

from __future__ import annotations

import pandas as pd


def null_summary(df: pd.DataFrame) -> pd.DataFrame:
    """Return null/empty counts and percentages per column."""
    rows = []
    total = len(df)
    for column in df.columns:
        series = df[column]
        missing = series.isna() | (series.astype(str).str.strip() == "")
        count = int(missing.sum())
        rows.append(
            {
                "column": column,
                "nulls": count,
                "null_pct": round(count / total * 100, 4) if total else 0.0,
            }
        )
    return pd.DataFrame(rows)


def assert_no_nulls(df: pd.DataFrame, columns: list[str]) -> None:
    """Raise ValueError when any required column contains a null."""
    for column in columns:
        missing = df[column].isna() | (df[column].astype(str).str.strip() == "")
        if missing.any():
            raise ValueError(f"Required column {column!r} has {int(missing.sum())} nulls")
