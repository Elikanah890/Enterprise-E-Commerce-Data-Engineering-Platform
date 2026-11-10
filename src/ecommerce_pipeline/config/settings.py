"""Central project settings and path constants."""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

# project root = .../enterprise-ecommerce-data-platform
BASE_DIR = Path(__file__).resolve().parents[3]
load_dotenv(BASE_DIR / ".env")

DATA_DIR = Path(os.getenv("DATA_DIR", BASE_DIR / "data"))
RAW_DIR = Path(os.getenv("RAW_DIR", DATA_DIR / "raw"))
PROCESSED_DIR = Path(os.getenv("PROCESSED_DIR", DATA_DIR / "processed"))
CLEANED_DIR = PROCESSED_DIR / "cleaned"
VALIDATED_DIR = PROCESSED_DIR / "validated"
WAREHOUSE_DIR = Path(os.getenv("WAREHOUSE_DIR", DATA_DIR / "warehouse"))
BRONZE_DIR = WAREHOUSE_DIR / "bronze"
SILVER_DIR = WAREHOUSE_DIR / "silver"
GOLD_DIR = WAREHOUSE_DIR / "gold"
SAMPLE_DIR = DATA_DIR / "sample"
LOG_DIR = BASE_DIR / "logs"
SQL_DIR = BASE_DIR / "sql"

RAW_FILES = {
    "customers": "olist_customers_dataset.csv",
    "geolocation": "olist_geolocation_dataset.csv",
    "order_items": "olist_order_items_dataset.csv",
    "order_payments": "olist_order_payments_dataset.csv",
    "order_reviews": "olist_order_reviews_dataset.csv",
    "orders": "olist_orders_dataset.csv",
    "products": "olist_products_dataset.csv",
    "sellers": "olist_sellers_dataset.csv",
    "category_translation": "product_category_name_translation.csv",
}

# Database settings
POSTGRES_HOST = os.getenv("POSTGRES_HOST", "localhost")
POSTGRES_PORT = int(os.getenv("POSTGRES_PORT", "5432"))
POSTGRES_DB = os.getenv("POSTGRES_DB", "ecommerce_dw")
POSTGRES_USER = os.getenv("POSTGRES_USER", "ecommerce_etl")
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD", "")
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    f"postgresql+psycopg2://{POSTGRES_USER}:{POSTGRES_PASSWORD}"
    f"@{POSTGRES_HOST}:{POSTGRES_PORT}/{POSTGRES_DB}",
)

LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
ENVIRONMENT = os.getenv("ENVIRONMENT", "local")

# Business rules discovered during profiling
EXPECTED_ROWS = {
    "customers": 99_441,
    "geolocation": 1_000_163,
    "order_items": 112_650,
    "order_payments": 103_886,
    "order_reviews": 99_224,
    "orders": 99_441,
    "products": 32_951,
    "sellers": 3_095,
    "category_translation": 71,
}
