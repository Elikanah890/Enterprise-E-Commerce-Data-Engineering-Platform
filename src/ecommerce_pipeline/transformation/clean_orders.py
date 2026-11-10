"""Clean the orders table."""

from __future__ import annotations

import pandas as pd

TIMESTAMP_COLUMNS = [
    "order_purchase_timestamp",
    "order_approved_at",
    "order_delivered_carrier_date",
    "order_delivered_customer_date",
    "order_estimated_delivery_date",
]


def clean_orders(df: pd.DataFrame) -> pd.DataFrame:
    """Cast timestamp columns and normalise status text."""
    out = df.copy()
    for column in TIMESTAMP_COLUMNS:
        out[column] = pd.to_datetime(out[column].replace("", None), errors="coerce")
    out["order_status"] = out["order_status"].astype(str).str.strip().str.lower()
    return out
