"""Date utilities."""

from __future__ import annotations

import pandas as pd


def parse_datetime(series: pd.Series) -> pd.Series:
    """Parse a date-like series, turning empty strings into nulls."""
    return pd.to_datetime(series.replace("", None), errors="coerce")


def days_between(start: pd.Series, end: pd.Series) -> pd.Series:
    """Return whole days from ``start`` to ``end``."""
    return (end - start).dt.days
