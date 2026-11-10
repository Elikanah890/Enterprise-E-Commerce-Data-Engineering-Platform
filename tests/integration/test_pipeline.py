"""Pipeline integration smoke test.

The inventory test runs against local raw data when present.
"""

from __future__ import annotations

import pytest

from ecommerce_pipeline.config.settings import RAW_DIR
from ecommerce_pipeline.profiling.dataset_inventory import build_inventory

pytestmark = pytest.mark.skipif(
    not RAW_DIR.exists() or not any(RAW_DIR.glob("*.csv")),
    reason="Raw CSV files are not available",
)


def test_inventory_contains_all_raw_files() -> None:
    inventory = build_inventory(RAW_DIR)

    assert len(inventory) == 9
    assert inventory["rows"].notna().all()
    assert set(inventory["entity"]) == {
        "customers",
        "geolocation",
        "order_items",
        "order_payments",
        "order_reviews",
        "orders",
        "products",
        "sellers",
        "category_translation",
    }
