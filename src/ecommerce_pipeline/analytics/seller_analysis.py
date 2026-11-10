"""Seller analytics.

Use ``gold.vw_seller_performance``.
"""

from __future__ import annotations

import pandas as pd


def top_sellers(seller_performance: pd.DataFrame, limit: int = 20) -> pd.DataFrame:
    """Return the top sellers by revenue."""
    return seller_performance.sort_values("revenue", ascending=False).head(limit).reset_index(drop=True)
