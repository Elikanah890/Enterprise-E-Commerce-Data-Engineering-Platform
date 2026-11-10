"""Payments ingestion."""

from __future__ import annotations

import pandas as pd

from .csv_reader import read_raw


def ingest_payments() -> pd.DataFrame:
    """Return the raw payments CSV as strings."""
    return read_raw("order_payments")
