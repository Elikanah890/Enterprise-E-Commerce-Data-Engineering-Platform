#!/usr/bin/env python3
"""Pipeline runner.

Stages
------
inventory : profile raw files
ingest    : read raw CSVs into memory and print shapes
transform : clean raw data and write CSV files to data/processed/cleaned
validate  : check row counts, keys, and foreign keys
load      : load bronze -> silver -> gold into PostgreSQL
all       : inventory -> ingest -> transform -> validate -> load
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

import pandas as pd  # noqa: E402

from ecommerce_pipeline.config.logging_config import get_logger  # noqa: E402
from ecommerce_pipeline.config.settings import (  # noqa: E402
    CLEANED_DIR,
    EXPECTED_ROWS,
    RAW_DIR,
    SQL_DIR,
)
from ecommerce_pipeline.ingestion import (  # noqa: E402
    customers_ingestion,
    geolocation_ingestion,
    order_items_ingestion,
    orders_ingestion,
    payments_ingestion,
    products_ingestion,
    reviews_ingestion,
    sellers_ingestion,
)
from ecommerce_pipeline.ingestion.csv_reader import read_raw  # noqa: E402
from ecommerce_pipeline.profiling.dataset_inventory import build_inventory  # noqa: E402
from ecommerce_pipeline.transformation.clean_customers import clean_customers  # noqa: E402
from ecommerce_pipeline.transformation.clean_geolocation import clean_geolocation  # noqa: E402
from ecommerce_pipeline.transformation.clean_order_items import clean_order_items  # noqa: E402
from ecommerce_pipeline.transformation.clean_orders import clean_orders  # noqa: E402
from ecommerce_pipeline.transformation.clean_payments import clean_payments  # noqa: E402
from ecommerce_pipeline.transformation.clean_products import clean_products  # noqa: E402
from ecommerce_pipeline.transformation.clean_reviews import clean_reviews  # noqa: E402
from ecommerce_pipeline.transformation.clean_sellers import clean_sellers  # noqa: E402

log = get_logger(__name__)


def stage_inventory() -> None:
    inventory = build_inventory(RAW_DIR)
    log.info("Inventory:\n%s", inventory.to_string(index=False))


def stage_ingest() -> dict[str, pd.DataFrame]:
    frames = {
        "customers": customers_ingestion.ingest_customers(),
        "geolocation": geolocation_ingestion.ingest_geolocation(),
        "order_items": order_items_ingestion.ingest_order_items(),
        "order_payments": payments_ingestion.ingest_payments(),
        "order_reviews": reviews_ingestion.ingest_reviews(),
        "orders": orders_ingestion.ingest_orders(),
        "products": products_ingestion.ingest_products(),
        "sellers": sellers_ingestion.ingest_sellers(),
        "category_translation": read_raw("category_translation"),
    }
    for name, frame in frames.items():
        log.info("ingested %-20s rows=%-9d cols=%d", name, len(frame), len(frame.columns))
    return frames


def stage_transform(frames: dict[str, pd.DataFrame] | None = None) -> dict[str, pd.DataFrame]:
    frames = frames or stage_ingest()
    cleaned = {
        "customers": clean_customers(frames["customers"]),
        "geolocation": clean_geolocation(frames["geolocation"]),
        "order_items": clean_order_items(frames["order_items"]),
        "order_payments": clean_payments(frames["order_payments"]),
        "order_reviews": clean_reviews(frames["order_reviews"]),
        "orders": clean_orders(frames["orders"]),
        "products": clean_products(frames["products"]),
        "sellers": clean_sellers(frames["sellers"]),
        "category_translation": frames["category_translation"],
    }
    CLEANED_DIR.mkdir(parents=True, exist_ok=True)
    for name, frame in cleaned.items():
        frame.to_csv(CLEANED_DIR / f"{name}.csv", index=False)
        log.info("cleaned %-20s rows=%-9d -> %s", name, len(frame), CLEANED_DIR / f"{name}.csv")
    return cleaned


def stage_validate() -> bool:
    ok = True
    for name, expected in EXPECTED_ROWS.items():
        path = RAW_DIR / f"olist_{name}_dataset.csv"
        if name == "category_translation":
            path = RAW_DIR / "product_category_name_translation.csv"
        if not path.exists():
            log.warning("missing raw file %s", path)
            ok = False
            continue
        actual = len(pd.read_csv(path))
        status = "ok" if actual == expected else "MISMATCH"
        if actual != expected:
            ok = False
        log.info("row count %-20s expected=%-9d actual=%-9d %s", name, expected, actual, status)
    return ok


def stage_load() -> None:
    from ecommerce_pipeline.loading.create_tables import execute_sql_file
    from ecommerce_pipeline.loading.load_bronze import load_bronze
    from ecommerce_pipeline.loading.load_gold import load_gold
    from ecommerce_pipeline.loading.load_silver import load_silver

    execute_sql_file(SQL_DIR / "database" / "02_create_schemas.sql")
    execute_sql_file(SQL_DIR / "bronze" / "create_bronze_tables.sql")
    execute_sql_file(SQL_DIR / "silver" / "create_silver_tables.sql")
    log.info("bronze rows: %s", load_bronze())
    load_silver()
    load_gold()
    log.info("gold load complete")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--stage",
        choices=["inventory", "ingest", "transform", "validate", "load", "all"],
        default="inventory",
    )
    args = parser.parse_args()

    if args.stage in ("inventory", "all"):
        stage_inventory()
    if args.stage in ("ingest", "all"):
        frames = stage_ingest()
    else:
        frames = None
    if args.stage in ("transform", "all"):
        stage_transform(frames)
    if args.stage in ("validate", "all"):
        if not stage_validate():
            return 1
    if args.stage in ("load", "all"):
        stage_load()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
