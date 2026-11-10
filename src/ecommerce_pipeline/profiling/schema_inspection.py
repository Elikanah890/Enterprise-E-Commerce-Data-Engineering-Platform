"""Schema inspection helpers."""

from __future__ import annotations

import pandas as pd


def inspect_schema(df: pd.DataFrame) -> pd.DataFrame:
    """Return column names, dtypes, null counts, and unique counts."""
    return pd.DataFrame(
        {
            "column": df.columns,
            "dtype": [str(t) for t in df.dtypes],
            "nulls": [int(df[c].isna().sum()) for c in df.columns],
            "null_pct": [round(df[c].isna().mean() * 100, 4) for c in df.columns],
            "unique": [int(df[c].nunique(dropna=True)) for c in df.columns],
        }
    )
