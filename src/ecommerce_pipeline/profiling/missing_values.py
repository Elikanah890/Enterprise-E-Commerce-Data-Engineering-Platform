"""Missing-value profiling."""

from __future__ import annotations

import pandas as pd


def missing_summary(df: pd.DataFrame) -> pd.DataFrame:
    """Summarise null/empty values per column.

    Empty strings are counted as missing in addition to ``NaN`` so that the
    report matches the raw CSV profile.
    """
    rows = []
    total = len(df)
    for column in df.columns:
        series = df[column]
        missing = series.isna() | (series.astype(str).str.strip() == "")
        count = int(missing.sum())
        rows.append(
            {
                "column": column,
                "missing": count,
                "missing_pct": round(count / total * 100, 4) if total else 0.0,
            }
        )
    return pd.DataFrame(rows).sort_values("missing", ascending=False)
