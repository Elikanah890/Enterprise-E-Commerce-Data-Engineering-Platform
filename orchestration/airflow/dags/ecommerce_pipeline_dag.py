"""Schedule the persisted Olist warehouse pipeline with Airflow.

The DAG deliberately coordinates existing project loaders and SQL rather than
passing data between tasks. Configure the Airflow connection ``ecommerce_postgres``
with access to the warehouse. Set ``ECOMMERCE_AIRFLOW_CONN_ID`` to use a
different connection ID, or ``ECOMMERCE_PIPELINE_SCHEDULE`` to set a cron
expression or Airflow preset. The schedule defaults to manual runs because the
checked-in dataset is static.
"""

from __future__ import annotations

import logging
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from airflow import DAG
from airflow.operators.python import PythonOperator

PROJECT_ROOT = Path(__file__).resolve().parents[3]
SOURCE_ROOT = PROJECT_ROOT / "src"
for import_path in (SOURCE_ROOT, PROJECT_ROOT):
    resolved_import_path = str(import_path)
    if resolved_import_path in sys.path:
        sys.path.remove(resolved_import_path)
    sys.path.insert(0, resolved_import_path)

POSTGRES_CONN_ID = os.getenv("ECOMMERCE_AIRFLOW_CONN_ID", "ecommerce_postgres")
PIPELINE_SCHEDULE = os.getenv("ECOMMERCE_PIPELINE_SCHEDULE") or None
logger = logging.getLogger(__name__)

KEY_CHECKS = (
    ("silver.category_translation", ("product_category_name",)),
    ("silver.customers", ("customer_id",)),
    ("silver.sellers", ("seller_id",)),
    ("silver.products", ("product_id",)),
    ("silver.geolocation", ("geo_id",)),
    (
        "silver.geolocation",
        ("zip_code_prefix", "lat", "lng", "city", "state"),
    ),
    ("silver.orders", ("order_id",)),
    ("silver.order_items", ("order_id", "order_item_id")),
    ("silver.order_payments", ("order_id", "payment_sequential")),
    ("silver.order_reviews", ("review_sk",)),
    ("silver.order_reviews", ("review_id", "order_id")),
)

NOT_NULL_CHECKS = {
    "silver.category_translation": (
        "product_category_name",
        "product_category_name_english",
    ),
    "silver.customers": (
        "customer_id",
        "customer_unique_id",
        "customer_zip_code_prefix",
        "customer_city",
        "customer_state",
    ),
    "silver.sellers": (
        "seller_id",
        "seller_zip_code_prefix",
        "seller_city",
        "seller_state",
    ),
    "silver.products": ("product_id", "product_category_name", "category_missing"),
    "silver.geolocation": (
        "geo_id",
        "zip_code_prefix",
        "lat",
        "lng",
        "city",
        "state",
        "is_outlier",
    ),
    "silver.orders": (
        "order_id",
        "customer_id",
        "order_status",
        "order_purchase_timestamp",
        "order_estimated_delivery_date",
        "has_approved",
        "has_carrier_date",
        "has_delivery_date",
        "delivery_anomaly",
    ),
    "silver.order_items": (
        "order_id",
        "order_item_id",
        "product_id",
        "seller_id",
        "shipping_limit_date",
        "price",
        "freight_value",
        "is_zero_freight",
    ),
    "silver.order_payments": (
        "order_id",
        "payment_sequential",
        "payment_type",
        "payment_installments",
        "payment_value",
        "is_zero_value",
        "is_zero_installments",
        "is_not_defined",
    ),
    "silver.order_reviews": (
        "review_sk",
        "review_id",
        "order_id",
        "review_score",
        "review_creation_date",
        "review_answer_timestamp",
        "has_title",
        "has_message",
        "is_before_purchase",
    ),
}

RELATIONSHIP_CHECKS = (
    (
        "silver.products",
        "product_category_name",
        "silver.category_translation",
        "product_category_name",
    ),
    ("silver.orders", "customer_id", "silver.customers", "customer_id"),
    ("silver.order_items", "order_id", "silver.orders", "order_id"),
    ("silver.order_items", "product_id", "silver.products", "product_id"),
    ("silver.order_items", "seller_id", "silver.sellers", "seller_id"),
    ("silver.order_payments", "order_id", "silver.orders", "order_id"),
    ("silver.order_reviews", "order_id", "silver.orders", "order_id"),
)


def _postgres_hook():
    """Return a hook for the configured Airflow PostgreSQL connection."""
    from airflow.providers.postgres.hooks.postgres import PostgresHook

    return PostgresHook(postgres_conn_id=POSTGRES_CONN_ID)


def _execute_count(cursor: Any, query: str, parameters: tuple[Any, ...] = ()) -> int:
    """Execute a scalar count query and return its integer result."""
    cursor.execute(query, parameters)
    row = cursor.fetchone()
    if row is None:
        raise RuntimeError("Quality check query returned no result")
    return int(row[0])


def load_bronze_layer() -> None:
    """Ensure base warehouse objects exist and load source files into Bronze."""
    from ecommerce_pipeline.config.settings import SQL_DIR
    from ecommerce_pipeline.loading.create_tables import execute_sql_file
    from ecommerce_pipeline.loading.load_bronze import load_bronze

    logger.info("Starting Bronze load using Airflow connection %r", POSTGRES_CONN_ID)
    engine = _postgres_hook().get_sqlalchemy_engine()
    try:
        for sql_file in (
            SQL_DIR / "database" / "02_create_schemas.sql",
            SQL_DIR / "bronze" / "create_bronze_tables.sql",
            SQL_DIR / "silver" / "create_silver_tables.sql",
        ):
            execute_sql_file(sql_file, engine)
        row_counts = load_bronze(engine)
        for table_name, row_count in row_counts.items():
            logger.info("Bronze load complete: %s rows=%d", table_name, row_count)
    finally:
        engine.dispose()


def bronze_quality_gate() -> None:
    """Require each latest successful Bronze batch to match expected input rows."""
    from ecommerce_pipeline.config.settings import EXPECTED_ROWS, RAW_FILES

    logger.info("Starting Bronze quality gate")
    connection = _postgres_hook().get_conn()
    failures: list[str] = []
    try:
        cursor = connection.cursor()
        try:
            for entity, expected_rows in EXPECTED_ROWS.items():
                source_file = RAW_FILES[entity]
                cursor.execute(
                    """
                    SELECT load_id, row_count
                    FROM bronze.load_batches
                    WHERE source_file = %s AND status = 'success'
                    ORDER BY started_at DESC, load_id DESC
                    LIMIT 1
                    """,
                    (source_file,),
                )
                batch = cursor.fetchone()
                if batch is None:
                    failures.append(f"{source_file}: no successful Bronze batch")
                    logger.error(
                        "Bronze quality failure: %s has no successful batch",
                        source_file,
                    )
                    continue

                load_id, recorded_rows = int(batch[0]), int(batch[1])
                actual_rows = _execute_count(
                    cursor,
                    f"SELECT COUNT(*) FROM bronze.{entity} WHERE _load_id = %s",
                    (load_id,),
                )
                rejected_rows = _execute_count(
                    cursor,
                    "SELECT COUNT(*) FROM bronze.rejected_rows WHERE load_id = %s",
                    (load_id,),
                )

                logger.info(
                    "Bronze quality: %s expected=%d recorded=%d actual=%d rejected=%d",
                    source_file,
                    expected_rows,
                    recorded_rows,
                    actual_rows,
                    rejected_rows,
                )
                if recorded_rows != expected_rows or actual_rows != expected_rows:
                    failures.append(
                        f"{source_file}: expected {expected_rows} rows, "
                        f"recorded={recorded_rows}, actual={actual_rows}"
                    )
                if rejected_rows:
                    failures.append(f"{source_file}: {rejected_rows} rows were rejected")
        finally:
            cursor.close()
    finally:
        connection.close()

    if failures:
        raise RuntimeError("Bronze quality gate failed: " + "; ".join(failures))
    logger.info("Bronze quality gate passed for all %d source files", len(EXPECTED_ROWS))


def rebuild_silver_layer() -> None:
    """Rebuild the typed Silver layer from Bronze using the canonical SQL."""
    from ecommerce_pipeline.loading.load_silver import load_silver

    logger.info("Starting Silver rebuild")
    engine = _postgres_hook().get_sqlalchemy_engine()
    try:
        load_silver(engine)
    finally:
        engine.dispose()
    logger.info("Silver rebuild completed")


def silver_quality_gate() -> None:
    """Check Silver key uniqueness, required values, and declared relationships."""
    logger.info("Starting Silver quality gate")
    connection = _postgres_hook().get_conn()
    failures: list[str] = []
    checks_passed = 0
    try:
        cursor = connection.cursor()
        try:
            for table, columns in KEY_CHECKS:
                column_sql = ", ".join(columns)
                duplicate_groups = _execute_count(
                    cursor,
                    f"""
                    SELECT COUNT(*)
                    FROM (
                        SELECT {column_sql}
                        FROM {table}
                        GROUP BY {column_sql}
                        HAVING COUNT(*) > 1
                    ) AS duplicate_keys
                    """,
                )
                logger.info(
                    "Silver key check: %s(%s) duplicate_groups=%d",
                    table,
                    column_sql,
                    duplicate_groups,
                )
                if duplicate_groups:
                    failures.append(
                        f"{table}({column_sql}) has {duplicate_groups} duplicate key groups"
                    )
                else:
                    checks_passed += 1

            for table, columns in NOT_NULL_CHECKS.items():
                missing_condition = " OR ".join(
                    f"{column} IS NULL OR BTRIM({column}::text) = ''"
                    for column in columns
                )
                missing_rows = _execute_count(
                    cursor,
                    f"SELECT COUNT(*) FROM {table} WHERE {missing_condition}",
                )
                logger.info(
                    "Silver required-value check: %s columns=%s rows_with_missing_values=%d",
                    table,
                    ", ".join(columns),
                    missing_rows,
                )
                if missing_rows:
                    failures.append(
                        f"{table} has {missing_rows} rows with missing required values"
                    )
                else:
                    checks_passed += 1

            for child_table, child_column, parent_table, parent_column in RELATIONSHIP_CHECKS:
                orphan_rows = _execute_count(
                    cursor,
                    f"""
                    SELECT COUNT(*)
                    FROM {child_table} AS child
                    LEFT JOIN {parent_table} AS parent
                      ON child.{child_column} = parent.{parent_column}
                    WHERE parent.{parent_column} IS NULL
                    """,
                )
                relationship = (
                    f"{child_table}.{child_column} -> {parent_table}.{parent_column}"
                )
                logger.info(
                    "Silver relationship check: %s orphan_rows=%d",
                    relationship,
                    orphan_rows,
                )
                if orphan_rows:
                    failures.append(f"{relationship} has {orphan_rows} orphan rows")
                else:
                    checks_passed += 1

            rejected_rows = _execute_count(
                cursor, "SELECT COUNT(*) FROM silver.rejected_rows"
            )
            logger.info("Silver rejected-row audit count=%d", rejected_rows)
        finally:
            cursor.close()
    finally:
        connection.close()

    if failures:
        raise RuntimeError("Silver quality gate failed: " + "; ".join(failures))
    logger.info("Silver quality gate passed (%d checks)", checks_passed)


def build_gold_layer() -> None:
    """Rebuild Gold dimensions, facts, and analytical views from Silver."""
    from ecommerce_pipeline.loading.load_gold import load_gold

    logger.info("Starting Gold build")
    engine = _postgres_hook().get_sqlalchemy_engine()
    try:
        load_gold(engine)
    finally:
        engine.dispose()
    logger.info("Gold build completed")


default_args = {
    "owner": "data-engineering",
    "depends_on_past": False,
    "email_on_failure": False,
    "retries": 2,
    "retry_delay": timedelta(minutes=5),
    "retry_exponential_backoff": True,
    "max_retry_delay": timedelta(minutes=30),
}

with DAG(
    dag_id="ecommerce_pipeline",
    description="Load and validate Bronze, rebuild Silver, then build Gold.",
    default_args=default_args,
    start_date=datetime(2024, 1, 1, tzinfo=timezone.utc),
    schedule=PIPELINE_SCHEDULE,
    catchup=False,
    max_active_runs=1,
    dagrun_timeout=timedelta(hours=6),
    tags=["ecommerce", "olist", "warehouse"],
    doc_md=__doc__,
) as dag:
    bronze_load = PythonOperator(
        task_id="bronze_load",
        python_callable=load_bronze_layer,
        do_xcom_push=False,
    )
    bronze_gate = PythonOperator(
        task_id="bronze_quality_gate",
        python_callable=bronze_quality_gate,
        do_xcom_push=False,
    )
    silver_rebuild = PythonOperator(
        task_id="silver_rebuild",
        python_callable=rebuild_silver_layer,
        do_xcom_push=False,
    )
    silver_gate = PythonOperator(
        task_id="silver_quality_gate",
        python_callable=silver_quality_gate,
        do_xcom_push=False,
    )
    gold_build = PythonOperator(
        task_id="gold_build",
        python_callable=build_gold_layer,
        do_xcom_push=False,
    )

    bronze_load >> bronze_gate >> silver_rebuild >> silver_gate >> gold_build
