"""Clean the sellers table."""

from __future__ import annotations

import pandas as pd


def clean_sellers(df: pd.DataFrame) -> pd.DataFrame:
    """Normalise seller geography."""
    out = df.copy()
    out["seller_zip_code_prefix"] = (
        out["seller_zip_code_prefix"].astype(str).str.replace(r"\D", "", regex=True).str.zfill(5)
    )
    out["seller_city"] = out["seller_city"].astype(str).str.strip().str.lower()
    out["seller_state"] = out["seller_state"].astype(str).str.strip().str.upper()
    return out
