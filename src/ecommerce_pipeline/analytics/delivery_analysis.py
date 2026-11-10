"""Delivery analytics.

Use ``gold.vw_delivery_performance`` and ``gold.fact_orders``.
"""

from __future__ import annotations

import pandas as pd


def late_rate_by_state(orders: pd.DataFrame) -> pd.DataFrame:
    """Compute late-delivery rate by customer state."""
    frame = orders.copy()
    frame["is_late"] = frame["is_late"].astype(bool)
    return (
        frame.groupby("customer_state", as_index=False)
        .agg(orders=("order_id", "nunique"), late_rate=("is_late", "mean"))
        .sort_values("late_rate", ascending=False)
    )
