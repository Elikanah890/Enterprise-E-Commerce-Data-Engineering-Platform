# Pipeline Documentation

## Prerequisites

- Python 3.11+
- PostgreSQL 16 (local or Docker)
- `psql` or a PostgreSQL client
- Optional: Airflow, dbt

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

cp .env.example .env
# edit POSTGRES_* values
```

Create the database once:

```bash
psql -U postgres -f sql/database/01_create_database.sql
```

## Stage commands

### Inventory (read-only)

```bash
python scripts/dataset_inventory.py
```

Writes `data/processed/validated/dataset_inventory.csv` and prints the table.

### Ingest

```bash
python scripts/run_pipeline.py --stage ingest
```

Reads all raw CSVs as text, preserving leading zeros and stripping the BOM.

### Transform

```bash
python scripts/run_pipeline.py --stage transform
```

Applies cleaning functions and writes CSVs to `data/processed/cleaned/`.
This is a local preview; the warehouse load uses the SQL transformations.

### Validate

```bash
python scripts/run_pipeline.py --stage validate
```

Checks each raw file against the expected row counts. Returns exit code 1 on
mismatch.

### Load

```bash
python scripts/run_pipeline.py --stage load
```

Creates schemas and tables, loads bronze idempotently, runs the silver cleaning
SQL, and builds gold.

`load_bronze` is hash-based: each CSV is identified by SHA-256, recorded in
`bronze.load_batches`, and skipped on repeat runs. Rows carry `_load_id`,
`_source_file`, and `_source_row_number`. Malformed CSV rows are written to
`bronze.rejected_rows`, never silently dropped.

### All

```bash
python scripts/run_pipeline.py --stage all
```

## SQL execution order

```
sql/database/01_create_database.sql
sql/database/02_create_schemas.sql
sql/bronze/create_bronze_tables.sql
sql/silver/create_silver_tables.sql
sql/silver/cleaning_transformations.sql
sql/gold/dimensions.sql
sql/gold/fact_orders.sql
sql/gold/fact_order_items.sql
sql/gold/fact_payments.sql
sql/gold/fact_reviews.sql
sql/gold/analytical_views.sql
```

Load bronze before running `cleaning_transformations.sql` (either via
`load_bronze` or `COPY`).

## Data quality gates

| Gate | Rule | Action on failure |
|---|---|---|
| Row counts | Match `settings.EXPECTED_ROWS` | Stop |
| Primary keys | No duplicates in declared PKs | Stop |
| Foreign keys | 0 orphans for items/payments/reviews | Stop |
| Review key | `(review_id, order_id)` unique | Stop |
| Zip format | 5 characters after `LPAD` | Stop |
| Delivery rate | ~97% delivered | Warn |
| Late rate | ~7.87% | Warn |
| Payment reconciliation | Document mismatches | Warn |

## Airflow

The DAG is `orchestration/airflow/dags/ecommerce_pipeline_dag.py`.
It runs:

```
inventory -> ingest -> transform -> validate -> load
```

Install Airflow separately, set `PYTHONPATH` to `src`, and ensure the project
root is on the Airflow `PYTHONPATH` so `scripts.run_pipeline` is importable.

## Docker

```bash
cd infrastructure/docker
docker compose up --build
```

The Compose file starts PostgreSQL and the app. The app waits for the database
health check before running.

## Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| `psycopg2` import error | driver missing | `pip install psycopg2-binary` |
| Zip codes lose leading zeros | cast to integer | Use `char(5)` / `read_csv(dtype=str)` |
| Row counts explode after joins | geolocation not aggregated | Use `gold.dim_geolocation` |
| Duplicate orders after review join | joined on `review_id` only | Use `(review_id, order_id)` |
| `null value in column order_purchase_timestamp` | empty timestamp not filtered | Check bronze data; filter empty timestamps |
| Foreign key violation on category | category missing from translation | Insert missing categories first |
| BOM appears in category name | file read without `utf-8-sig` | Use `read_csv` helper |

## Operational notes

- Logs are written to `logs/pipeline.log`.
- Raw files are git-ignored due to size; they remain on disk.
- The gold layer is safe to rebuild; it is derived from silver.
- Silver rebuilds truncate and reload all tables in dependency order.
