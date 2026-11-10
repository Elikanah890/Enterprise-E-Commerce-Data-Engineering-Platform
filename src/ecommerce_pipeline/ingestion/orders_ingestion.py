"""Orders ingestion."""

from __future__ import annotations

import pandas as pd

from .csv_reader import read_raw


def ingest_orders() -> pd.DataFrame:
    """Return the raw orders CSV as strings."""
    return read_raw("orders")
