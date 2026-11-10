"""Geolocation ingestion."""

from __future__ import annotations

import pandas as pd

from .csv_reader import read_raw


def ingest_geolocation() -> pd.DataFrame:
    """Return the raw geolocation CSV as strings."""
    return read_raw("geolocation")
