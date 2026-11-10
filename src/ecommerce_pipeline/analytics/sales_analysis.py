"""Sales analytics.

Implement analysis against gold views:

- ``gold.vw_sales_daily``
- ``gold.vw_category_performance``

Typical questions: monthly revenue, AOV, top categories, freight burden.
"""

from __future__ import annotations

import pandas as pd


def monthly_revenue(sales_daily: pd.DataFrame) -> pd.DataFrame:
    """Aggregate daily sales to month-level revenue and order counts."""
    frame = sales_daily.copy()
    frame["month"] = pd.to_datetime(frame["order_date"]).dt.to_period("M").astype(str)
    return (
        frame.groupby("month", as_index=False)
        .agg(orders=("orders", "sum"), revenue=("revenue", "sum"), freight=("freight", "sum"))
        .sort_values("month")
    )
