"""Reviews ingestion."""

from __future__ import annotations

import pandas as pd

from .csv_reader import read_raw


def ingest_reviews() -> pd.DataFrame:
    """Return the raw reviews CSV as strings."""
    return read_raw("order_reviews")
