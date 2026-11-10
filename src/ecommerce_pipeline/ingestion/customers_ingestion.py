"""Customers ingestion."""

from __future__ import annotations

import pandas as pd

from .csv_reader import read_raw


def ingest_customers() -> pd.DataFrame:
    """Return the raw customers CSV as strings."""
    return read_raw("customers")
