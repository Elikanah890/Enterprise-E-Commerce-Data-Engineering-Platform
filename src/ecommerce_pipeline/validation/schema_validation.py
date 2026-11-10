"""Schema validation helpers."""

from __future__ import annotations

import pandas as pd


def missing_columns(df: pd.DataFrame, expected: list[str]) -> list[str]:
    """Return expected columns that are absent from the DataFrame."""
    return [column for column in expected if column not in df.columns]


def unexpected_columns(df: pd.DataFrame, expected: list[str]) -> list[str]:
    """Return DataFrame columns that are not in the expected schema."""
    return [column for column in df.columns if column not in expected]


def validate_schema(df: pd.DataFrame, expected: list[str]) -> dict:
    """Return a schema validation result."""
    missing = missing_columns(df, expected)
    unexpected = unexpected_columns(df, expected)
    return {
        "valid": not missing and not unexpected,
        "missing": missing,
        "unexpected": unexpected,
        "rows": len(df),
    }
