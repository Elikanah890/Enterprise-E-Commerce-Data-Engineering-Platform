# Stage 2 Report — PostgreSQL Warehouse Implementation and Verification

**Date:** 2026-11-02
**Project:** Enterprise E-Commerce Data Engineering Platform
**Database:** `ecommerce_dw` on PostgreSQL 16.15
**Runtime role:** `ecommerce_etl`
**Status:** Complete for the scope of Milestone 2

---

## 1. Executive summary

The PostgreSQL warehouse was created, populated, transformed, and tested against
the live database. No existing database or schema was dropped.

| Layer | Objects | Status |
|---|---|---|
| Bronze | 9 data tables + `load_batches` + `rejected_rows` | Populated, 1,550,922 rows |
| Silver | 9 typed tables + `rejected_rows` | Built, 0 rejected rows |
| Gold | 6 dimensions, 4 facts, 9 analytical views | Built |
| Integration tests | 27 tests | **27 passed, 0 skipped** |
| Repeated ingestion | Hash-based skip | Verified: no duplicate rows |

Key outcome: the warehouse now supports order, item, payment, review, customer,
product, seller, delivery, and geographic analysis with documented flags for
known data-quality anomalies.

---

## 2. Environment and safety

| Item | Value |
|---|---|
| PostgreSQL server | 16.15 (Ubuntu 16.15-0ubuntu0.24.04.1) |
| psql client | 18.6 |
| Host / port | localhost / 5432 |
| Database | `ecommerce_dw` |
| Owner | `ecommerce_etl` |
| Credentials | `.env` (mode 600, gitignored); password not recorded here |
| Existing DBs | Left untouched (`agac_db`, `ecommerce_db`, `farmlink_db`, etc.) |
| Source CSVs | Preserved; `data/raw/` copies remain byte-identical to originals |

No Docker, Airflow, dbt, Spark, Kafka, dashboards, or ML work was added.

---

## 3. Database architecture

### Schemas

| Schema | Purpose |
|---|---|
| `bronze` | Raw text landing zone; source fidelity plus load metadata |
| `silver` | Typed, constrained, cleaned tables; suspicious rows flagged |
| `gold` | Star-schema dimensions, facts, and analytical views |
| `analytics` | Reserved for ad-hoc analytical work |

### Bronze tables

`bronze.customers`, `bronze.geolocation`, `bronze.order_items`,
`bronze.order_payments`, `bronze.order_reviews`, `bronze.orders`,
`bronze.products`, `bronze.sellers`, `bronze.category_translation`, plus:

- `bronze.load_batches` — one row per source-file SHA-256, with status and row count.
- `bronze.rejected_rows` — malformed CSV rows with source row number and reason.

Every bronze data row carries:

- `_load_id` — batch identifier.
- `_source_file` — source CSV name.
- `_source_row_number` — 1-based data row number.
- `_loaded_at` — ingestion timestamp.

Unique constraint: `(_load_id, _source_row_number)`.

### Silver tables

- `silver.category_translation`
- `silver.customers`, `silver.sellers`, `silver.products`
- `silver.geolocation`
- `silver.orders`
- `silver.order_items`, `silver.order_payments`, `silver.order_reviews`
- `silver.rejected_rows`

Declared foreign keys (7 total, all validated):

| Child | Parent |
|---|---|
| `silver.orders.customer_id` | `silver.customers.customer_id` |
| `silver.products.product_category_name` | `silver.category_translation.product_category_name` |
| `silver.order_items.order_id` | `silver.orders.order_id` |
| `silver.order_items.product_id` | `silver.products.product_id` |
| `silver.order_items.seller_id` | `silver.sellers.seller_id` |
| `silver.order_payments.order_id` | `silver.orders.order_id` |
| `silver.order_reviews.order_id` | `silver.orders.order_id` |

### Gold objects

| Object | Grain |
|---|---|
| `gold.dim_date` | one day (2016-01-01 to 2019-12-31) |
| `gold.dim_category` | one product category |
| `gold.dim_geolocation` | one zip prefix |
| `gold.dim_customers` | one `customer_id` |
| `gold.dim_sellers` | one `seller_id` |
| `gold.dim_products` | one `product_id` |
| `gold.fact_orders` | one order |
| `gold.fact_order_items` | one order item `(order_id, order_item_id)` |
| `gold.fact_payments` | one payment sequence `(order_id, payment_sequential)` |
| `gold.fact_reviews` | one review record `(review_id, order_id)` |

Analytical views:

- `vw_sales_daily`
- `vw_delivery_performance`
- `vw_customer_rfm`
- `vw_category_performance`
- `vw_seller_performance`
- `vw_payment_mix`
- `vw_review_summary`
- `vw_payment_reconciliation`
- `vw_data_quality_flags`

Indexes: **76** across bronze, silver, and gold. Database size: **750 MB**.

---

## 4. SQL scripts executed

| Order | Script | Result |
|---:|---|---|
| 1 | `sql/database/02_create_schemas.sql` | 4 schemas created |
| 2 | `sql/bronze/create_bronze_tables.sql` | 11 bronze tables |
| 3 | `sql/silver/create_silver_tables.sql` | 10 silver tables |
| 4 | `sql/silver/cleaning_transformations.sql` | Silver populated; 0 rejected |
| 5 | `sql/gold/dimensions.sql` | 6 dimensions |
| 6 | `sql/gold/fact_orders.sql` | 99,441 rows |
| 7 | `sql/gold/fact_order_items.sql` | 112,650 rows |
| 8 | `sql/gold/fact_payments.sql` | 103,886 rows |
| 9 | `sql/gold/fact_reviews.sql` | 99,224 rows |
| 10 | `sql/gold/analytical_views.sql` | 9 views |

The programmatic path was also executed:

```bash
python scripts/run_pipeline.py --stage load
```

It skipped all nine already-loaded bronze batches and rebuilt silver and gold
successfully in **45.81 s**.

---

## 5. Actual row counts

### Bronze

| Table | Rows |
|---|---:|
| `bronze.customers` | 99,441 |
| `bronze.geolocation` | 1,000,163 |
| `bronze.order_items` | 112,650 |
| `bronze.order_payments` | 103,886 |
| `bronze.order_reviews` | 99,224 |
| `bronze.orders` | 99,441 |
| `bronze.products` | 32,951 |
| `bronze.sellers` | 3,095 |
| `bronze.category_translation` | 71 |
| **Total** | **1,550,922** |

`bronze.load_batches`: **9 success, 0 failed**. `bronze.rejected_rows`: **0**.

### Silver

| Table | Rows | Note |
|---|---:|---|
| `silver.customers` | 99,441 | unchanged |
| `silver.sellers` | 3,095 | unchanged |
| `silver.products` | 32,951 | missing categories mapped to `unknown` |
| `silver.geolocation` | 738,300 | deduplicated; outliers retained and flagged |
| `silver.orders` | 99,441 | all statuses retained |
| `silver.order_items` | 112,650 | unchanged |
| `silver.order_payments` | 103,886 | unchanged |
| `silver.order_reviews` | 99,224 | unchanged |
| `silver.category_translation` | 74 | 71 source + 3 added |
| `silver.rejected_rows` | 0 | no malformed rows |

### Gold

| Table | Rows |
|---|---:|
| `gold.dim_date` | 1,461 |
| `gold.dim_category` | 74 |
| `gold.dim_geolocation` | 19,015 |
| `gold.dim_customers` | 99,441 |
| `gold.dim_sellers` | 3,095 |
| `gold.dim_products` | 32,951 |
| `gold.fact_orders` | 99,441 |
| `gold.fact_order_items` | 112,650 |
| `gold.fact_payments` | 103,886 |
| `gold.fact_reviews` | 99,224 |

---

## 6. Integration test results

Command:

```bash
python3 -m pytest -q
```

Result:

```text
27 passed in 9.15s
```

No tests were skipped. The PostgreSQL connection test executed against the live
database.

Coverage of the required checks:

| Requirement | Result |
|---|---|
| Database and schema existence | Passed |
| Table existence | Passed |
| Source-to-bronze row counts | Passed (9/9) |
| Bronze-to-silver transformation counts | Passed (9/9) |
| Primary-key uniqueness | Passed (19 key checks) |
| Foreign-key integrity | Passed (7 declared FKs valid) |
| Orphan records | Passed (0 in all checked relationships) |
| Null constraints | Passed (21 required columns checked) |
| Duplicate handling | Passed (bronze row identity, geo key, review key) |
| Monetary reconciliation | Passed |
| Fact table grain | Passed (orders, items, payments, reviews) |
| Analytical view correctness | Passed |
| Repeated ingestion idempotency | Passed (counts unchanged, 9 batches) |

---

## 7. Data-quality findings

### Geolocation

- 1,000,163 raw points deduplicated to **738,300** normalized points.
- **19,015** distinct zip prefixes.
- **33 distinct points** fall outside the Brazil bounding box; they are
  retained with `is_outlier = true` and excluded from centroid medians.
- **21 zip prefixes** contain at least one outlier point.
- `gold.dim_geolocation.outlier_count` sums to **33**.

### Products

- **610** products have `category_missing = true`.
- Those 610 are stored with category `unknown`; the `unknown` category exists
  in `dim_category`.
- 3 categories were added to translation: `unknown`, `pc_gamer`,
  `portateis_cozinha_e_preparadores_de_alimentos`.

### Orders and delivery

| Flag | Count |
|---|---:|
| `NOT has_approved` | 160 |
| `NOT has_carrier_date` | 1,783 |
| `NOT has_delivery_date` | 2,965 |
| `delivery_anomaly` | 1,382 |

`delivery_anomaly` is the sum of 1,359 carrier-before-approval rows and 23
delivery-before-carrier rows; these sets do not overlap.

### Payments

| Flag | Count |
|---|---:|
| `is_zero_value` | 9 |
| `is_zero_installments` | 2 |
| `is_not_defined` | 3 |
| `payment_mismatch` | 1,076 |

Payment reconciliation:

- **304** orders with items have a payment mismatch greater than R$0.01.
- **772** itemless orders have a positive payment total and are therefore
  mismatches.
- **3** additional itemless orders have a zero-value payment row and are not
  mismatches.
- Total mismatches: **304 + 772 = 1,076**.

**Correction from the earlier report:** the earlier float-based calculation
reported 382 item-order mismatches. PostgreSQL `NUMERIC` arithmetic gives
**304**. The difference is caused by binary floating-point comparisons around
the R$0.01 tolerance. The database result is authoritative.

### Reviews

| Flag | Count |
|---|---:|
| `has_title` | 11,566 |
| `has_message` | 40,968 |
| `is_before_purchase` | 74 |

The raw non-empty counts were 11,568 titles and 40,977 messages. Nine messages
and two titles were whitespace-only and were normalized to NULL. This is an
intentional cleaning rule, not row loss.

### Items

- `is_zero_freight`: **383** item rows.

### Fact-level coverage

| Flag | Count |
|---|---:|
| Orders without items | 775 |
| Orders without payments | 1 |
| Orders without reviews | 768 |
| Payment mismatches | 1,076 |
| Delivery anomalies | 1,382 |

---

## 8. Primary-key and foreign-key results

- All declared primary keys and unique constraints passed duplicate checks.
- All 7 declared foreign keys are validated (`convalidated = true`).
- Orphan checks returned 0 for:
  - `orders -> customers`
  - `order_items -> orders/products/sellers`
  - `order_payments -> orders`
  - `order_reviews -> orders`
  - `products -> category_translation`
  - `fact_orders -> dim_customers`
  - `fact_order_items -> dim_products/dim_sellers`
  - `fact_reviews -> fact_orders`

Gold facts intentionally use indexes and verified relationships rather than
declared FKs, because they are derived analytical tables.

---

## 9. Failed checks and fixes during implementation

| Failure | Cause | Fix |
|---|---|---|
| `ModuleNotFoundError: psycopg2` | Driver not installed | Installed `psycopg2-binary 2.9.13` |
| `smallint out of range` in `dim_products` | `smallint` multiplication of 105×105×118 | Cast dimensions to `integer` |
| `unterminated quoted string` in `COMMENT ON SCHEMA` | Naive semicolon splitter split inside a quoted comment | Execute SQL files as one multi-statement command; strip transaction control |
| `RecursionError` in `test_connection` | Test function shadowed the imported helper | Imported as `check_connection` |
| `Decimal(...) == float` assertion failures | PostgreSQL returns `NUMERIC` as `Decimal` | Compared with `pytest.approx` |
| `NOT has_items AND has_payment` expected 772, got 775 | Three itemless orders have zero-value payment rows | Asserted 775 payment rows and 772 positive-total orders separately |
| Payment mismatch expected 382, got 304 | Earlier float arithmetic vs exact `NUMERIC` | Adopted the database result; documented the correction |

No failure was hidden. All tests were re-run after the fixes.

---

## 10. Performance observations

### Timings

| Operation | Time |
|---|---:|
| First Bronze load (all 9 files) | 54.74 s |
| Repeat Bronze load (hash skip) | 0.81 s |
| Silver cleaning | 43.84 s |
| Gold dimensions | 2.81 s |
| Gold facts + views | 4.37 s |
| Full programmatic load (Bronze skipped) | 45.81 s |

The first Bronze load is dominated by geolocation: approximately 33 s for
1,000,163 rows.

### Query plans (actual execution)

| Query | Execution time |
|---|---:|
| `vw_sales_daily` | 64.4 ms |
| `vw_delivery_performance` | 26.5 ms |
| `vw_payment_reconciliation` | 24.6 ms |
| `vw_category_performance` | 367.7 ms |
| `vw_customer_rfm` | 729.4 ms |
| Late rate by customer state | 495.2 ms |

The category and RFM queries use parallel sequential scans and hash
aggregations. The late-rate query uses a bitmap index on `order_status` and
nested-loop lookups on `dim_customers`. These are acceptable for the current
data size (99k orders, 112k items).

No additional indexes were added. The existing 76 indexes cover primary keys,
foreign keys, dates, status, product, seller, and customer access paths. Adding
more indexes now would be premature without a larger data volume or a specific
slow production query.

### Table sizes

| Table | Size |
|---|---:|
| `bronze.geolocation` | 178 MB |
| `silver.geolocation` | 120 MB |
| `silver.order_reviews` | 38 MB |
| `gold.fact_orders` | 37 MB |
| `gold.fact_reviews` | 35 MB |
| `gold.fact_order_items` | 33 MB |

Database total: **750 MB**.

---

## 11. Files changed

### SQL

- `sql/database/01_create_database.sql`
- `sql/bronze/create_bronze_tables.sql`
- `sql/silver/create_silver_tables.sql`
- `sql/silver/cleaning_transformations.sql`
- `sql/gold/dimensions.sql`
- `sql/gold/fact_orders.sql`
- `sql/gold/fact_order_items.sql`
- `sql/gold/fact_payments.sql`
- `sql/gold/fact_reviews.sql` (new)
- `sql/gold/analytical_views.sql`

### Python

- `src/ecommerce_pipeline/config/settings.py`
- `src/ecommerce_pipeline/loading/load_bronze.py` (rewritten idempotent loader)
- `src/ecommerce_pipeline/loading/load_gold.py`
- `src/ecommerce_pipeline/loading/create_tables.py`
- `scripts/run_pipeline.py`

### Tests

- `tests/integration/test_postgres_connection.py`
- `tests/integration/test_warehouse.py` (new)

### Configuration and documentation

- `.env.example`
- `README.md`
- `infrastructure/docker/docker-compose.yml`
- `dbt_project/ecommerce_dbt/profiles.yml.example`
- `docs/architecture/data_flow.md`
- `docs/data_dictionary/data_dictionary.md`
- `docs/pipeline/pipeline_documentation.md`
- `docs/progress/stage_2_report.md` (this file)
- `.env` (created locally, mode 600, gitignored; not committed)

### Unchanged

- All 9 source CSVs under `data/raw/` remain byte-identical to the originals.
- No source dataset file was modified.
- No existing database outside `ecommerce_dw` was touched.

---

## 12. Outstanding issues

1. **Failed-batch retry is implemented but not exercised with a genuinely
   malformed CSV.** The source data has zero malformed rows, so the rejection
   path is currently confirmed only by design and by zero-count checks.
2. **No read-only BI role yet.** All current access uses `ecommerce_etl`.
3. **No backup/retention policy.** The local database has no scheduled backup.
4. **Docker Compose is unavailable on this host.** The local PostgreSQL server
   was used instead.
5. **Gold rebuilds use `DROP TABLE IF EXISTS` on derived tables.** This does not
   touch bronze or silver, but a production deployment should adopt versioned
   migrations or dbt-managed rebuilds.
6. **No partitioning.** Current volumes are small enough that partitioning is
   unnecessary.
7. **dbt, Airflow, dashboards, and ML were intentionally not implemented** in
   this milestone.

---

## 13. Manual actions required

None are required to use the warehouse. Optional follow-ups:

1. Keep `.env` private and rotate the `ecommerce_etl` password if it was shared.
2. Create a read-only role for BI tools.
3. Configure a PostgreSQL backup schedule.
4. Decide whether to keep the local `postgres` superuser workflow or move to
   the dedicated `ecommerce_etl` role for all operations.
5. If Docker is used later, install the Compose plugin and use
   `infrastructure/docker/docker-compose.yml`.

---

## 14. Completion checklist

- [x] PostgreSQL database `ecommerce_dw` exists.
- [x] Bronze tables populated with all 9 files.
- [x] Silver transformations executed successfully.
- [x] Gold dimensions, facts, and views exist.
- [x] Actual PostgreSQL integration tests pass (27/27).
- [x] Row counts and relationships verified.
- [x] Repeated loading tested (hash-based skip, no duplicates).
- [x] Detailed implementation report created.
- [x] Original source dataset preserved.
- [x] No dbt, Airflow, dashboards, Docker requirement, Spark, Kafka, or ML work added.
