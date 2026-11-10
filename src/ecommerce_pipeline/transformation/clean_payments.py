"""Clean the payments table."""

from __future__ import annotations

import pandas as pd


def clean_payments(df: pd.DataFrame) -> pd.DataFrame:
    """Cast payment counters and monetary measures."""
    out = df.copy()
    out["payment_sequential"] = pd.to_numeric(
        out["payment_sequential"], errors="coerce"
    ).astype("Int64")
    out["payment_installments"] = pd.to_numeric(
        out["payment_installments"], errors="coerce"
    ).astype("Int64")
    out["payment_value"] = pd.to_numeric(
        out["payment_value"].replace("", None), errors="coerce"
    )
    out["payment_type"] = out["payment_type"].astype(str).str.strip().str.lower()
    return out
