"""Clean the order_items table."""

from __future__ import annotations

import pandas as pd


def clean_order_items(df: pd.DataFrame) -> pd.DataFrame:
    """Cast identifiers, dates, and monetary measures."""
    out = df.copy()
    out["order_item_id"] = pd.to_numeric(out["order_item_id"], errors="coerce").astype("Int64")
    out["shipping_limit_date"] = pd.to_datetime(
        out["shipping_limit_date"].replace("", None), errors="coerce"
    )
    out["price"] = pd.to_numeric(out["price"].replace("", None), errors="coerce")
    out["freight_value"] = pd.to_numeric(
        out["freight_value"].replace("", None), errors="coerce"
    )
    return out
