# dbt model guide

This guide describes the live dbt development layer. It was validated on
2026-11-05: 33 models, 9 sources, 162 tests, and a full build of 195 checks.
Staging and intermediate models are views; dimensions, facts, and marts are
tables. All output stays in the three `dbt_dev_*` schemas.

## Sources

`models/staging/_sources.yml` declares the 9 Silver data tables:

`category_translation`, `customers`, `geolocation`, `order_items`,
`order_payments`, `order_reviews`, `orders`, `products`, and `sellers`.

dbt only reads these relations. The dbt login also has a grant on
`silver.rejected_rows`, but no model uses it.

## Staging

Staging removes PostgreSQL `CHAR` padding and selects only the columns needed
downstream. Silver already performs typing, deduplication, and business
cleaning.

| Model | Rows | Key checks |
|---|---:|---|
| `stg_category_translation` | 74 | Unique, non-null natural category name |
| `stg_customers` | 99,441 | Unique `customer_id`; non-null person ID |
| `stg_geolocation` | 738,300 | Unique natural point tuple; excludes unstable `geo_id` |
| `stg_order_items` | 112,650 | Unique `(order_id, order_item_id)` |
| `stg_order_payments` | 103,886 | Unique `(order_id, payment_sequential)`; accepted type |
| `stg_order_reviews` | 99,224 | Unique `(review_id, order_id)`; score 1–5 |
| `stg_orders` | 99,441 | Unique `order_id`; accepted status |
| `stg_products` | 32,951 | Unique `product_id`; non-null category |
| `stg_sellers` | 3,095 | Unique `seller_id` |

## Intermediate

| Model | Rows | Logic |
|---|---:|---|
| `int_order_item_metrics` | 98,666 | One order; item/freight sums and shipping-limit bounds |
| `int_payment_metrics` | 99,440 | One order; payment count, total, max installments |
| `int_review_metrics` | 98,673 | One order; review count and mean score |
| `int_order_category_metrics` | 99,470 | One order/category; item aggregation before review attribution |
| `int_seller_order_outcomes` | 100,010 | One seller/order; item measures plus nullable late outcome |

The single-key models test `order_id` uniqueness. The multi-key models test
their declared composite grain.

## Dimensions

| Model | Rows | Design |
|---|---:|---|
| `dim_date` | 1,461 | Calendar 2016-01-01 to 2019-12-31; deterministic `YYYYMMDD` key |
| `dim_category` | 74 | MD5 of natural category name; stable across inserts |
| `dim_geolocation` | 19,015 | Median coordinates, preferring non-outliers |
| `dim_customers` | 99,441 | One `customer_id`; deterministic hash key; optional geo |
| `dim_sellers` | 3,095 | One seller; deterministic hash key; optional geo |
| `dim_products` | 32,951 | One product; deterministic key; category relationship |

## Facts

| Model | Rows | Design |
|---|---:|---|
| `fact_orders` | 99,441 | One order; independently aggregated items, payments, reviews |
| `fact_order_items` | 112,650 | One item; corrected carrier-handoff shipping flag |
| `fact_payments` | 103,886 | One payment sequence; order/date keys |
| `fact_reviews` | 99,224 | One `(review_id, order_id)`; deterministic composite key |

`fact_orders.is_late` compares customer delivery and estimate at timestamp
precision. `fact_order_items.shipped_after_limit` compares carrier handoff with
the seller shipping deadline. `fact_reviews` never uses Silver `review_sk`.

## Analytical marts

| Model | Rows | Purpose |
|---|---:|---|
| `mart_sales_daily` | 614 | Daily sales, freight, gross value, average order value |
| `mart_delivery_monthly` | 25 | Late orders / orders with a delivery timestamp |
| `mart_category_performance` | 74 | Category volume and order-weighted review score |
| `mart_seller_performance` | 3,095 | Seller volume and order-weighted late rate |
| `mart_customer_rfm` | 94,990 | Person-level RFM on non-canceled/unavailable orders |
| `mart_payment_mix_monthly` | 90 | Payment method mix by month |
| `mart_review_monthly` | 23 | Monthly review volume, score, text, latency |
| `mart_payment_reconciliation` | 8 | Payment mismatch counts by order status |
| `mart_data_quality_flags` | 8 | Operations counts for retained anomalies |

### Corrected metric definitions

- Seller late rate uses late seller-orders / all seller-orders; it is not
  weighted by item rows.
- Category review score is one order/category score per order, not one score
  per item.
- Delivery late rate uses orders with a known delivery timestamp in both
  numerator and denominator.
- `shipped_after_limit` uses carrier handoff time, not customer delivery time.
- Seller review score is order-weighted; it intentionally differs from Gold's
  item-weighted seller review score.
- RFM base metrics match Gold; 61 segment labels can differ because Gold's
  `NTILE` tie ordering is not deterministic.

## Tests

| Test group | Count | Coverage |
|---|---:|---|
| Source tests | 39 | Keys, 7 relationships, accepted status/type values |
| Model tests | 123 | Grain uniqueness, keys, relationships, metrics, business rules |
| Total `dbt test` | 162 | All pass |
| Full `dbt build` | 195 | 33 model operations + 162 tests |

Singular tests verify payment reconciliation arithmetic, delivery-rate
population and arithmetic, seller order weighting, category review weighting,
shipping-flag semantics, and expected quality-flag counts.

See [dbt_architecture.md](./dbt_architecture.md) and the live reconciliation in
[progress/dbt_implementation_report.md](./progress/dbt_implementation_report.md).
