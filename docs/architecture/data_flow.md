# Data Flow

## End-to-end flow

```
data/raw/*.csv
   │  read_csv(dtype=str, encoding="utf-8-sig")
   ▼
bronze.*                  all TEXT + _loaded_at + _source_file
   │  sql/silver/cleaning_transformations.sql
   ▼
silver.*                  typed, constrained, deduplicated
   │  sql/gold/dimensions.sql, fact_*.sql
   ▼
gold.*                    star schema + analytical views
   │
   ▼
dashboards / notebooks / analytics
```

## Isolated dbt development branch

dbt reads the existing Silver relations as sources and builds a parallel
development branch. It does not replace the established Gold pipeline:

```text
silver.* -> dbt staging views      -> dbt_dev_staging
         -> dbt intermediate views -> dbt_dev_intermediate
         -> dbt marts tables       -> dbt_dev_marts

silver.* -> existing SQL transformations -> gold.*
```

The dbt profile targets the `dbt_dev` namespace and a schema-name macro limits
models to the three `dbt_dev_*` schemas. The dbt branch is implemented and
validated: 33 models, 9 sources, 162 tests, and a 195-check full build. The Gold
schema remains the existing comparison baseline until a separately approved
migration. See `docs/progress/dbt_implementation_report.md`.

## Stage details

### 1. Raw

- Nine CSVs in `data/raw/`.
- UTF-8. One file (`product_category_name_translation.csv`) has a BOM.
- Reviews contain embedded newlines; line-based row counts overcount.

### 2. Bronze

- One table per CSV: `bronze.customers`, `bronze.geolocation`, etc.
- Every source column is `TEXT`.
- No cleaning, filtering, or deduplication.
- Audit columns: `_loaded_at`, `_source_file`.

### 3. Silver

| Source | Transformations |
|---|---|
| `customers` | zip `LPAD` to 5; city lower/trim; state upper |
| `sellers` | zip `LPAD` to 5; city lower/trim; state upper |
| `products` | rename `lenght` -> `length`; null category -> `unknown`; numeric casts |
| `geolocation` | zip `LPAD`; numeric lat/lng; exact dedup; Brazil bbox filter |
| `orders` | timestamp casts; status lower/trim |
| `order_items` | `order_item_id` smallint; timestamp; numeric money |
| `order_payments` | sequential/installments smallint; type lower; numeric money |
| `order_reviews` | score smallint; timestamp casts; empty text -> NULL |
| `category_translation` | BOM strip; add `unknown`, `pc_gamer`, and the portable-kitchen category |

Silver constraints:

- `customers.customer_id` PK.
- `orders.order_id` PK; `orders.customer_id` FK.
- `order_items` PK `(order_id, order_item_id)`; FKs to orders/products/sellers.
- `order_payments` PK `(order_id, payment_sequential)`; FK to orders.
- `order_reviews` unique `(review_id, order_id)`; FK to orders.
- `geolocation` surrogate `geo_id`; unique `(zip, lat, lng, city, state)`.

Suspicious records are retained with flags rather than deleted:

- `geolocation.is_outlier` for out-of-Brazil points (33 distinct points).
- `products.category_missing` for the 610 uncategorised products.
- `orders.has_approved`, `has_carrier_date`, `has_delivery_date`, and
  `delivery_anomaly`.
- `order_payments.is_zero_value`, `is_zero_installments`, `is_not_defined`.
- `order_items.is_zero_freight`.
- `order_reviews.has_title`, `has_message`, `is_before_purchase`.

Malformed records are written to `silver.rejected_rows`. The current run has
zero rejected rows.

### 4. Gold

| Object | Grain | Source |
|---|---|---|
| `dim_date` | one day | generated series 2016-01-01 to 2019-12-31 |
| `dim_category` | one product category | silver category translation |
| `dim_customers` | one `customer_id` | silver customers + geo enrichment |
| `dim_products` | one `product_id` | silver products + category translation |
| `dim_sellers` | one `seller_id` | silver sellers + geo enrichment |
| `dim_geolocation` | one zip prefix | silver geolocation (median over non-outlier points) |
| `fact_orders` | one order | orders + pre-aggregated items/payments/reviews |
| `fact_order_items` | one order item | order items + orders |
| `fact_payments` | one payment sequence | payments + orders |
| `fact_reviews` | one review record | reviews + orders |

### 5. Analytical views

- `vw_sales_daily` — daily orders, revenue, freight, AOV.
- `vw_delivery_performance` — monthly delivered orders, delivery days, late rate.
- `vw_customer_rfm` — person-level recency, frequency, monetary, segment.
- `vw_category_performance` — category orders, items, revenue, review score.
- `vw_seller_performance` — seller orders, revenue, late rate, review score.
- `vw_payment_mix` — monthly payment-type mix and installments.
- `vw_review_summary` — monthly review volume, score, text rate, answer latency.
- `vw_payment_reconciliation` — order-status view of payment/item mismatches.
- `vw_data_quality_flags` — counts of retained anomalies for engineering.

## Grain and fan-out rules

1. `orders` is one row per order.
2. `order_items`, `order_payments`, and `order_reviews` are multi-row per order.
3. **Never** join orders to all three satellite tables in one query without
   pre-aggregating each satellite first.
4. `fact_orders` already contains pre-aggregated item, payment, and review
   metrics; use it for order-level analysis.
5. Geolocation must be aggregated to one row per zip before joining.

## Time semantics

- All source timestamps are naive; treat them as `America/Sao_Paulo`.
- `order_purchase_timestamp` is the business event time.
- `review_creation_date` is date-only at midnight.
- `order_estimated_delivery_date` is date-only at midnight.
- Delivery days are calculated as calendar-date differences.
