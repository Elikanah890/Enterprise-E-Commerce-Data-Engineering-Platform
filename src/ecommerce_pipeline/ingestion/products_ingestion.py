"""Products ingestion."""

from __future__ import annotations

import pandas as pd

from .csv_reader import read_raw


def ingest_products() -> pd.DataFrame:
    """Return the raw products CSV as strings."""
    return read_raw("products")
