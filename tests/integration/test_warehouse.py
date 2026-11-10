"""End-to-end PostgreSQL warehouse integration tests.

These tests execute against the live ``ecommerce_dw`` database. They assert the
actual counts produced by the Bronze, Silver, and Gold build.
"""

from __future__ import annotations

import pytest
from sqlalchemy import text

from ecommerce_pipeline.config.settings import EXPECTED_ROWS, POSTGRES_DB
from ecommerce_pipeline.loading.load_bronze import load_bronze
from ecommerce_pipeline.loading.postgres_connection import get_engine


@pytest.fixture(scope="session")
def engine():
    return get_engine()


def scalar(engine, sql: str, params: dict | None = None):
    with engine.connect() as connection:
        return connection.execute(text(sql), params or {}).scalar_one()


def duplicate_count(engine, table: str, columns: list[str]) -> int:
    cols = ", ".join(columns)
    return scalar(
        engine,
        f"SELECT count(*) FROM (SELECT {cols} FROM {table} "
        f"GROUP BY {cols} HAVING count(*) > 1) d",
    )


def orphan_count(
    engine, child: str, child_col: str, parent: str, parent_col: str
) -> int:
    return scalar(
        engine,
        f"SELECT count(*) FROM {child} c LEFT JOIN {parent} p "
        f"ON c.{child_col} = p.{parent_col} WHERE p.{parent_col} IS NULL",
    )


def test_database_and_schemas(engine) -> None:
    assert scalar(engine, "SELECT current_database()") == POSTGRES_DB
    schemas = {
        row[0]
        for row in engine.connect().execute(
            text(
                "SELECT schema_name FROM information_schema.schemata "
                "WHERE schema_name IN ('bronze','silver','gold')"
            )
        )
    }
    assert schemas == {"bronze", "silver", "gold"}


def test_expected_tables_exist(engine) -> None:
    tables = {
        (row[0], row[1])
        for row in engine.connect().execute(
            text(
                "SELECT table_schema, table_name FROM information_schema.tables "
                "WHERE table_schema IN ('bronze','silver','gold')"
            )
        )
    }
    expected_bronze = {
        "customers",
        "geolocation",
        "order_items",
        "order_payments",
        "order_reviews",
        "orders",
        "products",
        "sellers",
        "category_translation",
        "load_batches",
        "rejected_rows",
    }
    expected_silver = {
        "customers",
        "sellers",
        "products",
        "geolocation",
        "orders",
        "order_items",
        "order_payments",
        "order_reviews",
        "category_translation",
        "rejected_rows",
    }
    expected_gold = {
        "dim_date",
        "dim_category",
        "dim_geolocation",
        "dim_customers",
        "dim_sellers",
        "dim_products",
        "fact_orders",
        "fact_order_items",
        "fact_payments",
        "fact_reviews",
    }
    for table in expected_bronze:
        assert ("bronze", table) in tables
    for table in expected_silver:
        assert ("silver", table) in tables
    for table in expected_gold:
        assert ("gold", table) in tables


def test_source_to_bronze_counts(engine) -> None:
    for entity, expected in EXPECTED_ROWS.items():
        actual = scalar(engine, f"SELECT count(*) FROM bronze.{entity}")
        assert actual == expected, f"bronze.{entity}: {actual} != {expected}"


def test_bronze_load_metadata(engine) -> None:
    asserting = scalar(
        engine,
        "SELECT count(*) FROM bronze.load_batches WHERE status = 'success'",
    )
    assert asserting == 9
    assert scalar(
        engine,
        "SELECT count(*) FROM bronze.load_batches WHERE status <> 'success'",
    ) == 0
    assert scalar(engine, "SELECT count(*) FROM bronze.rejected_rows") == 0
    assert scalar(
        engine,
        "SELECT count(*) FROM ("
        "SELECT file_sha256 FROM bronze.load_batches GROUP BY 1 HAVING count(*) > 1"
        ") d",
    ) == 0


def test_bronze_to_silver_counts(engine) -> None:
    expected = {
        "customers": 99_441,
        "sellers": 3_095,
        "products": 32_951,
        "geolocation": 738_300,
        "orders": 99_441,
        "order_items": 112_650,
        "order_payments": 103_886,
        "order_reviews": 99_224,
        "category_translation": 74,
    }
    for table, count in expected.items():
        actual = scalar(engine, f"SELECT count(*) FROM silver.{table}")
        assert actual == count, f"silver.{table}: {actual} != {count}"
    assert scalar(engine, "SELECT count(*) FROM silver.rejected_rows") == 0


def test_primary_keys_are_unique(engine) -> None:
    checks = [
        ("silver.customers", ["customer_id"]),
        ("silver.sellers", ["seller_id"]),
        ("silver.products", ["product_id"]),
        ("silver.orders", ["order_id"]),
        ("silver.order_items", ["order_id", "order_item_id"]),
        ("silver.order_payments", ["order_id", "payment_sequential"]),
        ("silver.order_reviews", ["review_id", "order_id"]),
        ("silver.geolocation", ["zip_code_prefix", "lat", "lng", "city", "state"]),
        ("gold.dim_date", ["date_key"]),
        ("gold.dim_category", ["category_key"]),
        ("gold.dim_geolocation", ["zip_code_prefix"]),
        ("gold.dim_customers", ["customer_id"]),
        ("gold.dim_sellers", ["seller_id"]),
        ("gold.dim_products", ["product_id"]),
        ("gold.fact_orders", ["order_id"]),
        ("gold.fact_order_items", ["order_id", "order_item_id"]),
        ("gold.fact_payments", ["order_id", "payment_sequential"]),
        ("gold.fact_reviews", ["review_sk"]),
        ("gold.fact_reviews", ["review_id", "order_id"]),
    ]
    for table, columns in checks:
        assert duplicate_count(engine, table, columns) == 0, f"{table} {columns}"


def test_foreign_keys_and_orphans(engine) -> None:
    checks = [
        ("silver.orders", "customer_id", "silver.customers", "customer_id"),
        ("silver.order_items", "order_id", "silver.orders", "order_id"),
        ("silver.order_items", "product_id", "silver.products", "product_id"),
        ("silver.order_items", "seller_id", "silver.sellers", "seller_id"),
        ("silver.order_payments", "order_id", "silver.orders", "order_id"),
        ("silver.order_reviews", "order_id", "silver.orders", "order_id"),
        (
            "silver.products",
            "product_category_name",
            "silver.category_translation",
            "product_category_name",
        ),
        (
            "gold.fact_orders",
            "customer_id",
            "gold.dim_customers",
            "customer_id",
        ),
        (
            "gold.fact_order_items",
            "product_id",
            "gold.dim_products",
            "product_id",
        ),
        (
            "gold.fact_order_items",
            "seller_id",
            "gold.dim_sellers",
            "seller_id",
        ),
        ("gold.fact_reviews", "order_id", "gold.fact_orders", "order_id"),
    ]
    for child, child_col, parent, parent_col in checks:
        assert (
            orphan_count(engine, child, child_col, parent, parent_col) == 0
        ), f"{child}.{child_col} -> {parent}.{parent_col}"
    assert scalar(
        engine,
        "SELECT count(*) FROM pg_constraint WHERE contype = 'f' AND NOT convalidated",
    ) == 0


def test_required_columns_have_no_nulls(engine) -> None:
    required = [
        ("silver.customers", "customer_id"),
        ("silver.customers", "customer_unique_id"),
        ("silver.customers", "customer_zip_code_prefix"),
        ("silver.orders", "order_id"),
        ("silver.orders", "customer_id"),
        ("silver.orders", "order_purchase_timestamp"),
        ("silver.order_items", "order_id"),
        ("silver.order_items", "product_id"),
        ("silver.order_items", "seller_id"),
        ("silver.order_items", "price"),
        ("silver.order_items", "freight_value"),
        ("silver.order_payments", "order_id"),
        ("silver.order_payments", "payment_value"),
        ("silver.order_reviews", "review_id"),
        ("silver.order_reviews", "order_id"),
        ("silver.order_reviews", "review_score"),
        ("silver.products", "product_id"),
        ("silver.products", "product_category_name"),
        ("silver.geolocation", "zip_code_prefix"),
        ("silver.geolocation", "lat"),
        ("silver.geolocation", "lng"),
    ]
    for table, column in required:
        nulls = scalar(engine, f"SELECT count(*) FROM {table} WHERE {column} IS NULL")
        assert nulls == 0, f"{table}.{column} has {nulls} nulls"


def test_monetary_reconciliation(engine) -> None:
    assert float(
        scalar(engine, "SELECT sum(item_revenue) FROM gold.fact_orders")
    ) == pytest.approx(13_591_643.70)
    assert float(
        scalar(engine, "SELECT sum(freight_revenue) FROM gold.fact_orders")
    ) == pytest.approx(2_251_909.54)
    assert float(
        scalar(engine, "SELECT sum(payment_total) FROM gold.fact_orders")
    ) == pytest.approx(16_008_872.12)

    # Exact NUMERIC arithmetic in PostgreSQL yields 304 item-order mismatches.
    assert scalar(
        engine,
        "SELECT count(*) FROM gold.fact_orders WHERE has_items AND payment_mismatch",
    ) == 304
    # 775 itemless orders have a payment row; 772 of those have a positive total.
    assert scalar(
        engine,
        "SELECT count(*) FROM gold.fact_orders WHERE NOT has_items AND has_payment",
    ) == 775
    assert scalar(
        engine,
        "SELECT count(*) FROM gold.fact_orders WHERE NOT has_items AND payment_total > 0",
    ) == 772
    assert scalar(
        engine,
        "SELECT count(*) FROM gold.fact_orders WHERE payment_mismatch",
    ) == 1_076
    # A mismatch flag must always correspond to an amount outside the tolerance.
    assert scalar(
        engine,
        "SELECT count(*) FROM gold.fact_orders "
        "WHERE payment_mismatch AND abs(payment_mismatch_amount) <= 0.01",
    ) == 0


def test_fact_grain(engine) -> None:
    assert scalar(engine, "SELECT count(*) FROM gold.fact_orders") == scalar(
        engine, "SELECT count(DISTINCT order_id) FROM gold.fact_orders"
    )
    assert scalar(engine, "SELECT count(*) FROM gold.fact_order_items") == scalar(
        engine,
        "SELECT count(*) FROM (SELECT order_id, order_item_id "
        "FROM gold.fact_order_items GROUP BY 1,2) d",
    )
    assert scalar(engine, "SELECT count(*) FROM gold.fact_payments") == scalar(
        engine,
        "SELECT count(*) FROM (SELECT order_id, payment_sequential "
        "FROM gold.fact_payments GROUP BY 1,2) d",
    )
    assert scalar(engine, "SELECT count(*) FROM gold.fact_reviews") == scalar(
        engine,
        "SELECT count(*) FROM (SELECT review_id, order_id "
        "FROM gold.fact_reviews GROUP BY 1,2) d",
    )


def test_data_quality_flags(engine) -> None:
    assert scalar(
        engine, "SELECT count(*) FROM silver.geolocation WHERE is_outlier"
    ) == 33
    assert scalar(
        engine, "SELECT sum(outlier_count) FROM gold.dim_geolocation"
    ) == 33
    assert scalar(
        engine, "SELECT count(*) FROM silver.products WHERE category_missing"
    ) == 610
    assert scalar(
        engine, "SELECT count(*) FROM silver.products WHERE product_category_name = 'unknown'"
    ) == 610
    assert scalar(
        engine, "SELECT count(*) FROM silver.orders WHERE NOT has_approved"
    ) == 160
    assert scalar(
        engine, "SELECT count(*) FROM silver.orders WHERE NOT has_carrier_date"
    ) == 1_783
    assert scalar(
        engine, "SELECT count(*) FROM silver.orders WHERE NOT has_delivery_date"
    ) == 2_965
    assert scalar(
        engine, "SELECT count(*) FROM silver.orders WHERE delivery_anomaly"
    ) == 1_382
    assert scalar(
        engine, "SELECT count(*) FROM silver.order_items WHERE is_zero_freight"
    ) == 383
    assert scalar(
        engine, "SELECT count(*) FROM silver.order_payments WHERE is_zero_value"
    ) == 9
    assert scalar(
        engine,
        "SELECT count(*) FROM silver.order_payments WHERE is_zero_installments",
    ) == 2
    assert scalar(
        engine, "SELECT count(*) FROM silver.order_payments WHERE is_not_defined"
    ) == 3
    assert scalar(
        engine, "SELECT count(*) FROM silver.order_reviews WHERE has_title"
    ) == 11_566
    assert scalar(
        engine, "SELECT count(*) FROM silver.order_reviews WHERE has_message"
    ) == 40_968
    assert scalar(
        engine, "SELECT count(*) FROM silver.order_reviews WHERE is_before_purchase"
    ) == 74


def test_geolocation_deduplication(engine) -> None:
    assert duplicate_count(
        engine,
        "silver.geolocation",
        ["zip_code_prefix", "lat", "lng", "city", "state"],
    ) == 0
    assert scalar(
        engine, "SELECT count(DISTINCT zip_code_prefix) FROM silver.geolocation"
    ) == 19_015


def test_bronze_row_identity_is_unique(engine) -> None:
    tables = [
        "customers",
        "geolocation",
        "order_items",
        "order_payments",
        "order_reviews",
        "orders",
        "products",
        "sellers",
        "category_translation",
    ]
    for table in tables:
        assert duplicate_count(
            engine, f"bronze.{table}", ["_load_id", "_source_row_number"]
        ) == 0, table


def test_analytical_views(engine) -> None:
    assert scalar(engine, "SELECT sum(orders) FROM gold.vw_sales_daily") == 98_207
    assert scalar(engine, "SELECT sum(delivered_orders) FROM gold.vw_delivery_performance") == 96_478
    assert scalar(engine, "SELECT sum(late_orders) FROM gold.vw_delivery_performance") == 7_827
    assert float(
        scalar(engine, "SELECT sum(revenue) FROM gold.vw_category_performance")
    ) == pytest.approx(13_591_643.70)
    assert scalar(engine, "SELECT count(*) FROM gold.vw_category_performance") == 74
    assert scalar(engine, "SELECT sum(mismatch_orders) FROM gold.vw_payment_reconciliation") == 1_076
    assert scalar(engine, "SELECT sum(reviews) FROM gold.vw_review_summary") == 99_224
    assert scalar(engine, "SELECT count(*) FROM gold.vw_seller_performance") == 3_095
    assert scalar(engine, "SELECT count(*) FROM gold.vw_customer_rfm") == 94_990

    flags = dict(
        engine.connect()
        .execute(text("SELECT flag, rows FROM gold.vw_data_quality_flags"))
        .all()
    )
    assert flags == {
        "orders_without_items": 775,
        "orders_without_payments": 1,
        "orders_without_reviews": 768,
        "payment_mismatches": 1_076,
        "delivery_anomalies": 1_382,
        "products_missing_category": 610,
        "reviews_before_purchase": 74,
        "zero_value_payments": 9,
    }


def test_repeated_load_is_idempotent(engine) -> None:
    before = {
        entity: scalar(engine, f"SELECT count(*) FROM bronze.{entity}")
        for entity in EXPECTED_ROWS
    }
    counts = load_bronze(engine)
    after = {
        entity: scalar(engine, f"SELECT count(*) FROM bronze.{entity}")
        for entity in EXPECTED_ROWS
    }
    assert counts == {f"bronze.{entity}": value for entity, value in EXPECTED_ROWS.items()}
    assert before == after
    assert scalar(
        engine, "SELECT count(*) FROM bronze.load_batches WHERE status = 'success'"
    ) == 9


def test_unknown_category_exists(engine) -> None:
    assert scalar(
        engine,
        "SELECT count(*) FROM gold.dim_category WHERE product_category_name = 'unknown'",
    ) == 1
    assert scalar(engine, "SELECT count(*) FROM gold.dim_products WHERE category_missing") == 610
