"""Product analytics.

Use ``gold.dim_products`` and ``gold.vw_category_performance``.
"""

from __future__ import annotations

import pandas as pd


def category_revenue(category_performance: pd.DataFrame) -> pd.DataFrame:
    """Return categories ranked by revenue."""
    return category_performance.sort_values("revenue", ascending=False).reset_index(drop=True)
