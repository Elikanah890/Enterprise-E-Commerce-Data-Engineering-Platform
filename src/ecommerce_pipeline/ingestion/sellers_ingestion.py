"""Sellers ingestion."""

from __future__ import annotations

import pandas as pd

from .csv_reader import read_raw


def ingest_sellers() -> pd.DataFrame:
    """Return the raw sellers CSV as strings."""
    return read_raw("sellers")
