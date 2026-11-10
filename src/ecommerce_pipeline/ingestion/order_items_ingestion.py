"""Order items ingestion."""

from __future__ import annotations

import pandas as pd

from .csv_reader import read_raw


def ingest_order_items() -> pd.DataFrame:
    """Return the raw order-items CSV as strings."""
    return read_raw("order_items")
