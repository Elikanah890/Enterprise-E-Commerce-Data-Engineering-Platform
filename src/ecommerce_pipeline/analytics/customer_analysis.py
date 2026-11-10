"""Customer analytics.

Use ``gold.vw_customer_rfm`` for segmentation and retention analysis.
"""

from __future__ import annotations

import pandas as pd


def segment_summary(rfm: pd.DataFrame) -> pd.DataFrame:
    """Summarise customer count and monetary value by RFM segment."""
    return (
        rfm.groupby("segment", as_index=False)
        .agg(customers=("customer_unique_id", "nunique"), monetary=("monetary", "sum"))
        .sort_values("monetary", ascending=False)
    )
