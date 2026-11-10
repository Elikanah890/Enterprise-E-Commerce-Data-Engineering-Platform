"""Clean the customers table."""

from __future__ import annotations

import pandas as pd


def clean_customers(df: pd.DataFrame) -> pd.DataFrame:
    """Normalise customer keys and geography.

    - Zero-pad zip prefixes to 5 characters.
    - Lowercase/trim city names.
    - Uppercase/trim state codes.
    """
    out = df.copy()
    out["customer_zip_code_prefix"] = (
        out["customer_zip_code_prefix"].astype(str).str.replace(r"\D", "", regex=True).str.zfill(5)
    )
    out["customer_city"] = out["customer_city"].astype(str).str.strip().str.lower()
    out["customer_state"] = out["customer_state"].astype(str).str.strip().str.upper()
    return out
