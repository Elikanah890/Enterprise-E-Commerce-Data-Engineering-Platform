# dbt implementation report

## Status

**Implemented and validated against the live `ecommerce_dw` database on
2026-11-05.** dbt reads `silver` and writes only to the isolated
`dbt_dev_staging`, `dbt_dev_intermediate`, and `dbt_dev_marts` schemas.

No Bronze, Silver, or Gold object was created, altered, truncated, or dropped.
The existing Gold schema remains the production comparison layer; no dbt model
is declared equivalent to Gold where a metric was intentionally corrected.

## Environment

| Item | Verified value |
|---|---|
| PostgreSQL server | 16.15 |
| Client `psql` | 18.6 |
| Python | 3.11.10 |
| dbt Core | 1.9.4 |
| dbt-postgres | 1.9.0 |
| dbt login | `dbt_dev_user` |
| dbt target schema | `dbt_dev` (macro maps to the three `dbt_dev_*` schemas) |
| dbt project | `dbt_project/ecommerce_dbt` |
| Virtual environment | `.venv-dbt` |

`dbt_dev_user` is a login with `NOSUPERUSER`, `NOCREATEDB`,
`NOCREATEROLE`, `NOINHERIT`, `NOREPLICATION`, and `NOBYPASSRLS`. It has
`USAGE`/`SELECT` on `silver`, no `USAGE`/`CREATE` on `bronze` or `gold`, and
`USAGE`/`CREATE` only on the three pre-created dev schemas. dbt-created
relations are owned by `dbt_dev_user`.

## Commands and results

| Command | Result |
|---|---|
| `dbt debug` | PASS; connection OK |
| `dbt compile` | PASS; 33 models, 162 data tests, 9 sources |
| `dbt test --select 'source:*'` | PASS=39 WARN=0 ERROR=0 |
| `dbt build` | PASS=195 WARN=0 ERROR=0 SKIP=0; 25.18s |
| `dbt test` | PASS=162 WARN=0 ERROR=0 SKIP=0; 8.31s |
| `python3 -m pytest -q` | 27 passed in 8.08s |

The full build executed 19 table models, 14 view models, and 162 tests.
The project has 33 models: 9 staging, 5 intermediate, 6 dimensions, 4 facts,
and 9 analytical marts.

## Row-count reconciliation

Expected values come from the prior audit and live Gold/Silver objects.
Every row count below matches exactly.

| Layer | Model | Expected | Observed | Result |
|---|---|---:|---:|---|
| Staging | `stg_category_translation` | 74 | 74 | Accept |
| Staging | `stg_customers` | 99,441 | 99,441 | Accept |
| Staging | `stg_geolocation` | 738,300 | 738,300 | Accept |
| Staging | `stg_order_items` | 112,650 | 112,650 | Accept |
| Staging | `stg_order_payments` | 103,886 | 103,886 | Accept |
| Staging | `stg_order_reviews` | 99,224 | 99,224 | Accept |
| Staging | `stg_orders` | 99,441 | 99,441 | Accept |
| Staging | `stg_products` | 32,951 | 32,951 | Accept |
| Staging | `stg_sellers` | 3,095 | 3,095 | Accept |
| Intermediate | `int_order_item_metrics` | 98,666 | 98,666 | Accept |
| Intermediate | `int_payment_metrics` | 99,440 | 99,440 | Accept |
| Intermediate | `int_review_metrics` | 98,673 | 98,673 | Accept |
| Intermediate | `int_order_category_metrics` | 99,470 | 99,470 | Accept |
| Intermediate | `int_seller_order_outcomes` | 100,010 | 100,010 | Accept |
| Dimension | `dim_date` | 1,461 | 1,461 | Accept |
| Dimension | `dim_category` | 74 | 74 | Accept |
| Dimension | `dim_geolocation` | 19,015 | 19,015 | Accept |
| Dimension | `dim_customers` | 99,441 | 99,441 | Accept |
| Dimension | `dim_sellers` | 3,095 | 3,095 | Accept |
| Dimension | `dim_products` | 32,951 | 32,951 | Accept |
| Fact | `fact_orders` | 99,441 | 99,441 | Accept |
| Fact | `fact_order_items` | 112,650 | 112,650 | Accept |
| Fact | `fact_payments` | 103,886 | 103,886 | Accept |
| Fact | `fact_reviews` | 99,224 | 99,224 | Accept |
| Mart | `mart_sales_daily` | 614 | 614 | Accept |
| Mart | `mart_delivery_monthly` | 25 | 25 | Accept |
| Mart | `mart_category_performance` | 74 | 74 | Accept |
| Mart | `mart_seller_performance` | 3,095 | 3,095 | Accept |
| Mart | `mart_customer_rfm` | 94,990 | 94,990 | Accept |
| Mart | `mart_payment_mix_monthly` | 90 | 90 | Accept |
| Mart | `mart_review_monthly` | 23 | 23 | Accept |
| Mart | `mart_payment_reconciliation` | 8 | 8 | Accept |
| Mart | `mart_data_quality_flags` | 8 | 8 | Accept |

## Corrected metrics and exact comparisons

| Metric | dbt observed | Gold observed | Result |
|---|---:|---:|---|
| Item revenue | 13,591,643.70 | 13,591,643.70 | Exact |
| Freight revenue | 2,251,909.54 | 2,251,909.54 | Exact |
| Payment total | 16,008,872.12 | 16,008,872.12 | Exact |
| Payment mismatches | 1,076 | 1,076 | Exact |
| `shipped_after_limit` (carrier handoff > limit) | 10,423 | 23,000 (old logic) | Corrected; 16-row overlap |
| Late orders (delivery > estimate) | 7,827 | 7,827 | Exact count |
| Delivery eligible orders (non-null delivery timestamp) | 96,476 | 96,478 delivered status | 2-row population difference |
| Delivery late rate | 8.11% | 8.11% | Exact rounded result |
| All-order late rate (`7,827 / 99,441`) | 7.87% | 7.87% | Different denominator; not a Gold view metric |
| Seller late-rate rows differing >1pp | 366 | — | Corrected order weighting |
| Seller late-rate max absolute difference | 37.40pp | — | Corrected order weighting |
| Category review rows differing | 69 of 74 | — | Corrected order weighting |
| Category review max absolute difference | 0.48 stars | — | Corrected order weighting |
| Seller review-score rows differing | 1,242 | — | Order-weighted vs item-weighted |
| Seller review-score max absolute difference | 1.67 stars | — | Order-weighted vs item-weighted |
| RFM base metric differences | 0 | — | Exact |
| RFM segment-label differences | 61 | — | Gold `NTILE` tie ordering |
| Delivery monthly rate differences | 1 month, 0.02pp | — | 2-order denominator difference |

### Metric definitions

- `fact_order_items.shipped_after_limit` is
  `order_delivered_carrier_date > shipping_limit_date`. It is not based on
  customer delivery time and does not use the old Gold
  `shipping_limit_date > order_delivered_customer_date` rule.
- `fact_orders.is_late` is
  `order_delivered_customer_date > order_estimated_delivery_date`, resolved at
  timestamp precision. The numerator and delivery denominator both include
  orders with a known delivery timestamp. The denominator is 96,476; Gold's
  status-based denominator is 96,478.
- `mart_seller_performance.late_rate_pct` uses one row per seller/order:
  late seller-orders / all seller-orders. This is the comparison that produces
  366 affected sellers and a 37.40pp maximum difference from Gold.
- `mart_category_performance.avg_review_score` averages one order-level review
  score per order/category, so an order with several items in one category
  contributes once.
- `mart_customer_rfm` has exact recency, frequency, monetary, and row-count
  parity. Sixty-one segment labels can differ because Gold uses `NTILE` over
  tied values without a deterministic tie-breaker. Repeated dbt builds were
  stable; the difference is not a changed business input.

## Analytic mart parity

The following marts have zero row-level differences against their Gold views:

| Mart | Comparison |
|---|---|
| `mart_sales_daily` | 0 differences across 614 rows |
| `mart_payment_mix_monthly` | 0 differences across 90 rows |
| `mart_review_monthly` | 0 differences across 23 rows |
| `mart_payment_reconciliation` | 0 differences across 8 rows |
| `mart_data_quality_flags` | All 8 counts exact |

`mart_delivery_monthly` matches Gold on total late orders (7,827) and rounded
late rate (8.11%). One month differs by 0.02pp because dbt excludes orders
without a delivery timestamp from both numerator and denominator, while Gold
uses delivered status as the denominator.

## Stability evidence

| Check | Evidence |
|---|---|
| `dim_category.category_key` | MD5 of natural category name; identical key hashes across consecutive builds |
| `dim_customers`, `dim_sellers`, `dim_products` keys | Identical key hashes across consecutive builds |
| `fact_reviews.review_key` | Identical MD5 key hash across three builds |
| `dim_date` | 1,461 rows; 2016-01-01 through 2019-12-31; integer `YYYYMMDD` keys |
| `fact_reviews` grain | `(review_id, order_id)` unique |
| Fact grains | All declared composite grains unique |
| Relationships | All dimension and fact relationship tests pass |

## Tests and safeguards

- 39 source tests pass: unique/not-null business keys, 7 declared FK
  relationships, accepted `order_status` and `payment_type` values.
- 123 model tests pass: grain uniqueness, keys, relationships, accepted values,
  payment reconciliation, delivery-rate arithmetic/population, shipping
  semantics, RFM segments, and quality-flag counts.
- No dbt packages, seeds, snapshots, incremental models, or `--full-refresh`
  runs were used.
- The project has no `packages.yml`; only `dbt-core` and `dbt-postgres` are
  installed in `.venv-dbt`.
- The source declaration contains the 9 Silver data tables. The dbt login also
  has a read grant on `silver.rejected_rows`, but no model reads it.

## Environment caveats

1. **Git is still absent in this workspace.** `git status` returns
   `fatal: not a git repository`; no baseline commit exists. The earlier claim
   that Git was initialized could not be verified.
2. **The restricted role was not present when this run started.** It was
   recreated from `sql/security/create_dbt_dev_role.sql`, with a generated
   one-time password kept outside the repository. The password must be rotated
   through the approved secret workflow before shared use.
3. **The prior readiness audit file was overwritten by a copy of the project
   roadmap.** Its key findings were revalidated live in this report. The
   readiness file now contains a concise audit summary and points here.
4. **Silver multi-batch safety is unresolved.** This work reads the current
   Silver snapshot only. It does not fix the `TRUNCATE`/full-rebuild behavior
   or add `_load_id` filtering.
5. **No Gold migration is approved.** Corrected metrics intentionally diverge
   from Gold where Gold is wrong or item-weighted. Do not replace Gold views
   until the metrics are accepted by the business owner.

## Next milestone

Gold parity review and metric sign-off; then decide whether to (a) replace Gold
views with corrected dbt marts, or (b) keep Gold stable and expose the corrected
marts alongside it. Multi-batch Silver hardening and Git/CI remain separate
prerequisites for any incremental or production dbt rollout.
