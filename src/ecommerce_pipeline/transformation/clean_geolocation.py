"""Clean the geolocation table.

The raw file is point-level and contains exact duplicates and coordinate
outliers. This module casts numeric values, normalises city text, removes
exact duplicates, and optionally filters to a Brazil bounding box.
"""

from __future__ import annotations

import pandas as pd

LAT_BOUNDS = (-34.0, 6.0)
LNG_BOUNDS = (-74.0, -34.0)


def clean_geolocation(df: pd.DataFrame, drop_outliers: bool = True) -> pd.DataFrame:
    """Cast, deduplicate, and optionally filter geolocation points."""
    out = df.copy()
    out["geolocation_zip_code_prefix"] = (
        out["geolocation_zip_code_prefix"]
        .astype(str)
        .str.replace(r"\D", "", regex=True)
        .str.zfill(5)
    )
    out["geolocation_lat"] = pd.to_numeric(out["geolocation_lat"], errors="coerce")
    out["geolocation_lng"] = pd.to_numeric(out["geolocation_lng"], errors="coerce")
    out["geolocation_city"] = out["geolocation_city"].astype(str).str.strip().str.lower()
    out["geolocation_state"] = (
        out["geolocation_state"].astype(str).str.strip().str.upper()
    )

    if drop_outliers:
        out = out[
            out["geolocation_lat"].between(*LAT_BOUNDS)
            & out["geolocation_lng"].between(*LNG_BOUNDS)
        ]

    return out.drop_duplicates().reset_index(drop=True)
