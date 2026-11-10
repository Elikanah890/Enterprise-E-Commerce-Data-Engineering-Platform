"""Unit tests for transformations."""

from __future__ import annotations

import pandas as pd

from ecommerce_pipeline.transformation.clean_customers import clean_customers
from ecommerce_pipeline.transformation.clean_geolocation import clean_geolocation
from ecommerce_pipeline.transformation.clean_products import clean_products


def test_clean_customers_pads_zip_and_normalises_text() -> None:
    df = pd.DataFrame(
        {
            "customer_id": ["a"],
            "customer_unique_id": ["b"],
            "customer_zip_code_prefix": ["1037"],
            "customer_city": ["  Sao Paulo "],
            "customer_state": ["sp"],
        }
    )

    out = clean_customers(df)

    assert out.loc[0, "customer_zip_code_prefix"] == "01037"
    assert out.loc[0, "customer_city"] == "sao paulo"
    assert out.loc[0, "customer_state"] == "SP"


def test_clean_products_renames_and_fills_category() -> None:
    df = pd.DataFrame(
        {
            "product_id": ["p1"],
            "product_category_name": [""],
            "product_name_lenght": ["40"],
            "product_description_lenght": ["287"],
            "product_photos_qty": ["1"],
            "product_weight_g": ["225"],
            "product_length_cm": ["16"],
            "product_height_cm": ["10"],
            "product_width_cm": ["14"],
        }
    )

    out = clean_products(df)

    assert "product_name_length" in out.columns
    assert "product_name_lenght" not in out.columns
    assert out.loc[0, "product_category_name"] == "unknown"
    assert out.loc[0, "product_weight_g"] == 225


def test_clean_geolocation_deduplicates_and_filters_outliers() -> None:
    df = pd.DataFrame(
        {
            "geolocation_zip_code_prefix": ["01037", "01037", "99999"],
            "geolocation_lat": ["-23.5", "-23.5", "45.0"],
            "geolocation_lng": ["-46.6", "-46.6", "121.0"],
            "geolocation_city": ["sao paulo", "sao paulo", "bad"],
            "geolocation_state": ["SP", "SP", "SP"],
        }
    )

    out = clean_geolocation(df)

    assert len(out) == 1
    assert out.loc[0, "geolocation_lat"] == -23.5
