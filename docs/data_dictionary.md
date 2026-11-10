# Data Dictionary

Complete reference for every warehouse object. Types are PostgreSQL types.
Bronze columns are all `text` by design; Silver types are enforced by DDL.

Conventions:

- **Grain** = one row per the stated key.
- **Key** = PK, FK, natural key, or uniqueness constraint.
- **Source** = raw CSV or upstream object.
- **Rule** = transformation applied on the way in.
- Dollar values are BRL (`numeric`), not floating point.
- Timestamps are naive; treat them as `America/Sao_Paulo`.

---

## 1. Bronze layer

### 1.1 Audit tables

#### `bronze.load_batches`

| Column | Type | Null | Key | Description |
|---|---|---|---|---|
| `load_id` | bigserial | no | PK | Batch identifier |
| `source_file` | text | no | — | CSV filename |
| `file_sha256` | char(64) | no | UNIQUE | Content hash used for idempotency |
| `row_count` | bigint | no | — | Valid rows loaded (default 0) |
| `status` | text | no | CHECK | `started`, `success`, `failed` |
| `started_at` | timestamptz | no | — | Batch start |
| `finished_at` | timestamptz | yes | — | Batch finish |
| `error_message` | text | yes | — | Last failure message |

Rule: a `success` batch is never reloaded; a failed batch is retried in place.

#### `bronze.rejected_rows`

| Column | Type | Null | Key | Description |
|---|---|---|---|---|
| `rejected_id` | bigserial | no | PK | Reject identifier |
| `load_id` | bigint | yes | FK → `load_batches` | Batch that produced the reject |
| `source_file` | text | no | index | CSV filename |
| `source_row_number` | bigint | no | index | 1-based data row number |
| `raw_line` | text | yes | — | Raw line, truncated to 4000 chars |
| `reason` | text | no | — | Wrong field count or NUL byte |
| `rejected_at` | timestamptz | no | — | Reject time |

### 1.2 Data tables

Every data table has the same four audit columns and constraint:

| Column | Type | Description |
|---|---|---|
| `_load_id` | bigint NOT NULL | FK to `bronze.load_batches` |
| `_source_file` | text NOT NULL | Source CSV |
| `_source_row_number` | bigint NOT NULL | 1-based CSV data row |
| `_loaded_at` | timestamptz NOT NULL | Ingestion time |
| — | UNIQUE | `(_load_id, _source_row_number)` |

#### `bronze.customers`
Source: `olist_customers_dataset.csv` (99,441 rows).

| Column | Type | Notes |
|---|---|---|
| `customer_id` | text | Order-scoped identifier |
| `customer_unique_id` | text | Person-level identifier |
| `customer_zip_code_prefix` | text | Leading zeros preserved |
| `customer_city` | text | — |
| `customer_state` | text | — |

#### `bronze.geolocation`
Source: `olist_geolocation_dataset.csv` (1,000,163 rows).

| Column | Type | Notes |
|---|---|---|
| `geolocation_zip_code_prefix` | text | Leading zeros preserved |
| `geolocation_lat` | text | Numeric text |
| `geolocation_lng` | text | Numeric text |
| `geolocation_city` | text | — |
| `geolocation_state` | text | — |

#### `bronze.order_items`
Source: `olist_order_items_dataset.csv` (112,650 rows).

| Column | Type | Notes |
|---|---|---|
| `order_id` | text | — |
| `order_item_id` | text | Line number |
| `product_id` | text | — |
| `seller_id` | text | — |
| `shipping_limit_date` | text | Timestamp text |
| `price` | text | Numeric text |
| `freight_value` | text | Numeric text |

#### `bronze.order_payments`
Source: `olist_order_payments_dataset.csv` (103,886 rows).

| Column | Type | Notes |
|---|---|---|
| `order_id` | text | — |
| `payment_sequential` | text | — |
| `payment_type` | text | — |
| `payment_installments` | text | — |
| `payment_value` | text | — |

#### `bronze.order_reviews`
Source: `olist_order_reviews_dataset.csv` (99,224 rows).

| Column | Type | Notes |
|---|---|---|
| `review_id` | text | Not unique in source |
| `order_id` | text | — |
| `review_score` | text | 1–5 |
| `review_comment_title` | text | May contain newlines |
| `review_comment_message` | text | May contain newlines |
| `review_creation_date` | text | — |
| `review_answer_timestamp` | text | — |

#### `bronze.orders`
Source: `olist_orders_dataset.csv` (99,441 rows).

| Column | Type | Notes |
|---|---|---|
| `order_id` | text | — |
| `customer_id` | text | — |
| `order_status` | text | 8 lifecycle values |
| `order_purchase_timestamp` | text | — |
| `order_approved_at` | text | May be empty |
| `order_delivered_carrier_date` | text | May be empty |
| `order_delivered_customer_date` | text | May be empty |
| `order_estimated_delivery_date` | text | — |

#### `bronze.products`
Source: `olist_products_dataset.csv` (32,951 rows).

| Column | Type | Notes |
|---|---|---|
| `product_id` | text | — |
| `product_category_name` | text | May be empty |
| `product_name_lenght` | text | Legacy typo preserved |
| `product_description_lenght` | text | Legacy typo preserved |
| `product_photos_qty` | text | — |
| `product_weight_g` | text | — |
| `product_length_cm` | text | — |
| `product_height_cm` | text | — |
| `product_width_cm` | text | — |

#### `bronze.sellers`
Source: `olist_sellers_dataset.csv` (3,095 rows).

| Column | Type | Notes |
|---|---|---|
| `seller_id` | text | — |
| `seller_zip_code_prefix` | text | Leading zeros preserved |
| `seller_city` | text | — |
| `seller_state` | text | — |

#### `bronze.category_translation`
Source: `product_category_name_translation.csv` (71 rows).

| Column | Type | Notes |
|---|---|---|
| `product_category_name` | text | BOM stripped on read |
| `product_category_name_english` | text | — |

---

## 2. Silver layer

### 2.1 `silver.rejected_rows`

| Column | Type | Null | Key | Description |
|---|---|---|---|---|
| `rejected_id` | bigserial | no | PK | Reject id |
| `source_table` | text | no | — | Bronze table name |
| `source_key` | text | yes | — | Best available natural key |
| `reason` | text | no | — | Why rejected |
| `raw_record` | jsonb | yes | — | Original row |
| `rejected_at` | timestamptz | no | — | Reject time |

### 2.2 `silver.category_translation`

| Column | Type | Null | Key | Rule |
|---|---|---|---|---|
| `product_category_name` | text | no | PK | BOM stripped, trimmed; 3 missing categories added: `unknown`, `pc_gamer`, `portateis_cozinha_e_preparadores_de_alimentos` |
| `product_category_name_english` | text | no | — | Trimmed |

Grain: one category. 74 rows on the audited snapshot.

### 2.3 `silver.customers`

| Column | Type | Null | Key | Rule |
|---|---|---|---|---|
| `customer_id` | char(32) | no | PK | As received |
| `customer_unique_id` | char(32) | no | natural | As received |
| `customer_zip_code_prefix` | char(5) | no | index | Digits only, `LPAD(...,5,'0')` |
| `customer_city` | text | no | — | `LOWER(TRIM(...))` |
| `customer_state` | char(2) | no | — | `UPPER(TRIM(...))` |

Rows with empty id/zip/state are written to `silver.rejected_rows`.
Grain: one `customer_id` (order-scoped, not person).

### 2.4 `silver.sellers`

| Column | Type | Null | Key | Rule |
|---|---|---|---|---|
| `seller_id` | char(32) | no | PK | As received |
| `seller_zip_code_prefix` | char(5) | no | index | Digits only, `LPAD` |
| `seller_city` | text | no | — | Lower/trim |
| `seller_state` | char(2) | no | — | Upper/trim |

Grain: one `seller_id`.

### 2.5 `silver.products`

| Column | Type | Null | Key | Rule |
|---|---|---|---|---|
| `product_id` | char(32) | no | PK | As received |
| `product_category_name` | text | no | FK → category | Missing/unknown → `unknown`; `category_missing = true` |
| `category_missing` | boolean | no | flag | True when source category was absent or unmapped |
| `product_name_length` | smallint | yes | — | Renamed from `lenght`; empty → NULL |
| `product_description_length` | integer | yes | — | Renamed; empty → NULL |
| `product_photos_qty` | smallint | yes | — | Empty → NULL |
| `product_weight_g` | integer | yes | CHECK ≥ 0 | Empty → NULL |
| `product_length_cm` | smallint | yes | — | Empty → NULL |
| `product_height_cm` | smallint | yes | — | Empty → NULL |
| `product_width_cm` | smallint | yes | — | Empty → NULL |

Grain: one `product_id`. 610 products map to `unknown`.

### 2.6 `silver.geolocation`

| Column | Type | Null | Key | Rule |
|---|---|---|---|---|
| `geo_id` | bigserial | no | PK | Surrogate; unstable across rebuilds |
| `zip_code_prefix` | char(5) | no | index | Digits only, `LPAD` |
| `lat` | numeric(10,7) | no | — | Cast; invalid rows rejected |
| `lng` | numeric(10,7) | no | — | Cast; invalid rows rejected |
| `city` | text | no | — | Lower/trim |
| `state` | char(2) | no | — | Upper/trim |
| `is_outlier` | boolean | no | flag | Outside Brazil bbox (lat −34..6, lng −74..−34) |
| — | — | — | UNIQUE | `(zip_code_prefix, lat, lng, city, state)` |

Grain: one distinct observed point per zip. 738,300 rows after dedup; 33
outlier points.

### 2.7 `silver.orders`

| Column | Type | Null | Key | Rule |
|---|---|---|---|---|
| `order_id` | char(32) | no | PK | As received |
| `customer_id` | char(32) | no | FK → customers | As received |
| `order_status` | text | no | CHECK | Lower/trim; 8 accepted values |
| `order_purchase_timestamp` | timestamp | no | index | Cast; invalid rows rejected |
| `order_approved_at` | timestamp | yes | — | Empty → NULL |
| `order_delivered_carrier_date` | timestamp | yes | — | Empty → NULL |
| `order_delivered_customer_date` | timestamp | yes | — | Empty → NULL |
| `order_estimated_delivery_date` | timestamp | no | — | Cast |
| `has_approved` | boolean | no | flag | `order_approved_at IS NOT NULL` |
| `has_carrier_date` | boolean | no | flag | Carrier date present |
| `has_delivery_date` | boolean | no | flag | Customer delivery present |
| `delivery_anomaly` | boolean | no | flag | Carrier < approval or delivery < carrier |

Accepted statuses: `delivered`, `shipped`, `canceled`, `unavailable`,
`invoiced`, `processing`, `created`, `approved`.
Grain: one `order_id`.

### 2.8 `silver.order_items`

| Column | Type | Null | Key | Rule |
|---|---|---|---|---|
| `order_id` | char(32) | no | PK/FK → orders | As received |
| `order_item_id` | smallint | no | PK | CHECK ≥ 1 |
| `product_id` | char(32) | no | FK → products | As received |
| `seller_id` | char(32) | no | FK → sellers | As received |
| `shipping_limit_date` | timestamp | no | — | Cast |
| `price` | numeric(10,2) | no | CHECK ≥ 0 | Cast |
| `freight_value` | numeric(10,2) | no | CHECK ≥ 0 | Cast |
| `is_zero_freight` | boolean | no | flag | `freight_value = 0` |

Grain: `(order_id, order_item_id)`. 112,650 rows.

### 2.9 `silver.order_payments`

| Column | Type | Null | Key | Rule |
|---|---|---|---|---|
| `order_id` | char(32) | no | PK/FK → orders | As received |
| `payment_sequential` | smallint | no | PK | CHECK ≥ 1 |
| `payment_type` | text | no | CHECK | Lower/trim; 5 accepted values |
| `payment_installments` | smallint | no | CHECK ≥ 0 | Cast |
| `payment_value` | numeric(12,2) | no | CHECK ≥ 0 | Cast |
| `is_zero_value` | boolean | no | flag | Value = 0 |
| `is_zero_installments` | boolean | no | flag | Installments = 0 |
| `is_not_defined` | boolean | no | flag | Type = `not_defined` |

Accepted types: `credit_card`, `boleto`, `voucher`, `debit_card`,
`not_defined`. Grain: `(order_id, payment_sequential)`. 103,886 rows.

### 2.10 `silver.order_reviews`

| Column | Type | Null | Key | Rule |
|---|---|---|---|---|
| `review_sk` | bigserial | no | PK | Surrogate; unstable across rebuilds |
| `review_id` | char(32) | no | — | Not unique alone |
| `order_id` | char(32) | no | FK → orders | As received |
| `review_score` | smallint | no | CHECK 1–5 | Cast |
| `review_comment_title` | text | yes | — | Empty → NULL |
| `review_comment_message` | text | yes | — | Empty → NULL |
| `review_creation_date` | timestamp | no | — | Cast |
| `review_answer_timestamp` | timestamp | no | — | Cast |
| `has_title` | boolean | no | flag | Title present |
| `has_message` | boolean | no | flag | Message present |
| `is_before_purchase` | boolean | no | flag | Review before order purchase |

Uniqueness: `(review_id, order_id)`. Grain: one review record (an order may
have several). 99,224 rows.

---

## 3. Gold layer

### 3.1 `gold.dim_date`

Generated calendar, 2016-01-01 → 2019-12-31 (1,461 rows).

| Column | Type | Key | Description |
|---|---|---|---|
| `date_key` | integer | PK | `YYYYMMDD` |
| `date_day` | date | index | Calendar date |
| `year` | integer | — | Year |
| `quarter` | integer | — | Quarter |
| `month` | integer | — | Month number |
| `month_name` | text | — | English month name |
| `day_of_month` | integer | — | Day |
| `day_of_week` | integer | — | ISO day (1=Mon) |
| `day_name` | text | — | English day name |
| `is_weekend` | boolean | — | ISO day 6/7 |

### 3.2 `gold.dim_category`

| Column | Type | Key | Source / rule |
|---|---|---|---|
| `category_key` | integer | PK | `ROW_NUMBER()` over category name |
| `product_category_name` | text | UNIQUE | Silver translation |
| `product_category_name_english` | text | — | Silver translation |

### 3.3 `gold.dim_geolocation`

| Column | Type | Key | Source / rule |
|---|---|---|---|
| `zip_code_prefix` | char(5) | PK | Silver geolocation |
| `lat` | numeric | — | Median non-outlier latitude (fallback all) |
| `lng` | numeric | — | Median non-outlier longitude (fallback all) |
| `city` | text | — | Modal city |
| `state` | char(2) | — | Modal state |
| `point_count` | bigint | — | Distinct points for the zip |
| `outlier_count` | bigint | — | Flagged points for the zip |

Grain: one zip prefix (19,015 rows).

### 3.4 `gold.dim_customers`

| Column | Type | Key | Source / rule |
|---|---|---|---|
| `customer_id` | char(32) | PK | Silver customers |
| `customer_unique_id` | char(32) | index | Silver |
| `customer_zip_code_prefix` | char(5) | — | Silver |
| `customer_city` | text | — | Silver |
| `customer_state` | char(2) | index | Silver |
| `has_geo` | boolean | — | Zip found in `dim_geolocation` |
| `geo_lat` | numeric | — | Zip latitude |
| `geo_lng` | numeric | — | Zip longitude |

### 3.5 `gold.dim_sellers`

| Column | Type | Key | Source / rule |
|---|---|---|---|
| `seller_id` | char(32) | PK | Silver sellers |
| `seller_zip_code_prefix` | char(5) | — | Silver |
| `seller_city` | text | — | Silver |
| `seller_state` | char(2) | index | Silver |
| `has_geo` | boolean | — | Zip found |
| `geo_lat` | numeric | — | Zip latitude |
| `geo_lng` | numeric | — | Zip longitude |

### 3.6 `gold.dim_products`

| Column | Type | Key | Source / rule |
|---|---|---|---|
| `product_id` | char(32) | PK | Silver products |
| `category_key` | integer | index | FK to `dim_category` |
| `product_category_name` | text | — | Silver (may be `unknown`) |
| `product_category_name_english` | text | — | Category translation, fallback `unknown` |
| `category_missing` | boolean | — | Silver flag |
| `product_name_length` | smallint | — | Silver |
| `product_description_length` | integer | — | Silver |
| `product_photos_qty` | smallint | — | Silver |
| `product_weight_g` | integer | — | Silver |
| `product_length_cm` | smallint | — | Silver |
| `product_height_cm` | smallint | — | Silver |
| `product_width_cm` | smallint | — | Silver |
| `product_volume_cm3` | integer | — | length × height × width |
| `density_g_cm3` | numeric | — | weight / volume (NULL when volume 0) |

### 3.7 `gold.fact_orders`

Grain: one order (99,441 rows). Items, payments, and reviews are pre-aggregated
before joining to prevent fan-out.

| Column | Type | Key | Source / rule |
|---|---|---|---|
| `order_id` | char(32) | PK | Silver orders |
| `customer_id` | char(32) | index | Silver orders |
| `order_status` | text | index | Silver |
| `order_purchase_timestamp` | timestamp | — | Silver |
| `order_date` | date | — | Purchase date |
| `order_date_key` | integer | index | `YYYYMMDD` |
| `order_approved_at` | timestamp | — | Silver |
| `order_delivered_carrier_date` | timestamp | — | Silver |
| `order_delivered_customer_date` | timestamp | — | Silver |
| `order_estimated_delivery_date` | timestamp | — | Silver |
| `delivery_days` | integer | — | delivery date − purchase date |
| `is_late` | boolean | — | Delivered after estimate; **false** when no delivery |
| `days_vs_estimate` | integer | — | delivery − estimate |
| `is_delivered` | boolean | — | status = delivered |
| `is_canceled` | boolean | — | status = canceled |
| `delivery_anomaly` | boolean | — | Silver flag |
| `item_count` | bigint | — | Count of items |
| `item_revenue` | numeric | — | Sum item price |
| `freight_revenue` | numeric | — | Sum freight |
| `gross_order_value` | numeric | — | item revenue + freight |
| `payment_count` | bigint | — | Count of payment rows |
| `payment_total` | numeric | — | Sum payment value |
| `max_installments` | smallint | — | Max installments |
| `avg_review_score` | numeric | — | Mean review score |
| `review_count` | bigint | — | Count of reviews |
| `has_items` | boolean | — | item_count > 0 |
| `has_payment` | boolean | — | payment_count > 0 |
| `has_review` | boolean | — | review_count > 0 |
| `payment_mismatch` | boolean | partial index | `abs(payment_total − gross_order_value) > 0.01` |
| `payment_mismatch_amount` | numeric | — | payment_total − gross_order_value |

### 3.8 `gold.fact_order_items`

Grain: `(order_id, order_item_id)` (112,650 rows).

| Column | Type | Key | Source / rule |
|---|---|---|---|
| `order_id` | char(32) | PK/FK → fact_orders | Silver items |
| `order_item_id` | smallint | PK | Silver |
| `product_id` | char(32) | index | Silver |
| `seller_id` | char(32) | index | Silver |
| `order_date` | date | — | Purchase date |
| `order_date_key` | integer | index | `YYYYMMDD` |
| `order_status` | text | — | Silver orders |
| `shipping_limit_date` | timestamp | — | Silver |
| `price` | numeric | — | Silver |
| `freight_value` | numeric | — | Silver |
| `total_value` | numeric | — | price + freight |
| `is_zero_freight` | boolean | — | Silver flag |
| `order_delivered_customer_date` | timestamp | — | Silver orders |
| `delivery_days` | integer | — | delivery date − purchase date |
| `shipped_after_limit` | boolean | — | **Legacy Gold rule:** delivery after shipping limit (see ADR-004) |

### 3.9 `gold.fact_payments`

Grain: `(order_id, payment_sequential)` (103,886 rows).

| Column | Type | Key | Source / rule |
|---|---|---|---|
| `order_id` | char(32) | PK/FK → fact_orders | Silver payments |
| `payment_sequential` | smallint | PK | Silver |
| `payment_type` | text | index | Silver |
| `payment_installments` | smallint | — | Silver |
| `payment_value` | numeric | — | Silver |
| `is_zero_value` | boolean | partial index | Silver flag |
| `is_zero_installments` | boolean | — | Silver flag |
| `is_not_defined` | boolean | — | Silver flag |
| `order_date` | date | — | Purchase date |
| `order_date_key` | integer | index | `YYYYMMDD` |
| `order_status` | text | — | Silver orders |

### 3.10 `gold.fact_reviews`

Grain: one review record; unique `(review_id, order_id)` (99,224 rows).

| Column | Type | Key | Source / rule |
|---|---|---|---|
| `review_sk` | bigint | PK | Silver surrogate |
| `review_id` | char(32) | UNIQUE with order | Silver |
| `order_id` | char(32) | FK → fact_orders | Silver |
| `order_date` | date | — | Purchase date |
| `order_date_key` | integer | index | `YYYYMMDD` |
| `order_status` | text | — | Silver orders |
| `review_score` | smallint | index | Silver |
| `review_creation_date` | timestamp | — | Silver |
| `review_answer_timestamp` | timestamp | — | Silver |
| `answer_latency_hours` | numeric | — | (answer − creation) / 3600 |
| `review_latency_days` | integer | — | creation date − purchase date |
| `has_title` | boolean | — | Silver flag |
| `has_message` | boolean | — | Silver flag |
| `title_length` | integer | — | Char length |
| `message_length` | integer | — | Char length |
| `is_before_purchase` | boolean | — | Silver flag |

### 3.11 Gold views

| View | Grain | Key metrics |
|---|---|---|
| `vw_sales_daily` | one order date | orders, revenue, freight, gross value, AOV (excludes canceled/unavailable) |
| `vw_delivery_performance` | one month | delivered orders, avg delivery days, late orders, late rate |
| `vw_customer_rfm` | one `customer_unique_id` | recency, frequency, monetary, R/F/M scores, segment |
| `vw_category_performance` | one English category | orders, items, revenue, freight, avg price, avg review score |
| `vw_seller_performance` | one seller | orders, items, revenue, freight, avg review score, late rate |
| `vw_payment_mix` | month × payment type | payments, value, avg installments |
| `vw_review_summary` | one month | reviews, avg score, low-score %, text %, avg answer hours |
| `vw_payment_reconciliation` | one order status | orders, item/paid/mismatch/under/over counts, net mismatch |
| `vw_data_quality_flags` | one flag | count of retained anomalies |

---

## 4. dbt development models (`dbt_dev_*`)

dbt reads Silver and writes only to `dbt_dev_staging`, `dbt_dev_intermediate`,
and `dbt_dev_marts`.

### 4.1 Staging (9 views)

`stg_category_translation`, `stg_customers`, `stg_geolocation`,
`stg_order_items`, `stg_order_payments`, `stg_order_reviews`, `stg_orders`,
`stg_products`, `stg_sellers`.

Rules: trim fixed-width `CHAR` padding; exclude unstable Silver keys
(`geo_id`, `review_sk`); otherwise pass through Silver.

### 4.2 Intermediate (5 views)

| Model | Grain | Purpose |
|---|---|---|
| `int_order_item_metrics` | one order | item/freight sums, shipping-limit bounds |
| `int_payment_metrics` | one order | payment count, total, max installments |
| `int_review_metrics` | one order | review count, mean score |
| `int_order_category_metrics` | one order/category | item aggregation before review attribution |
| `int_seller_order_outcomes` | one seller/order | item measures + nullable late outcome |

### 4.3 Dimensions (6 tables)

`dim_date` (YYYYMMDD key), `dim_category`, `dim_geolocation`,
`dim_customers`, `dim_sellers`, `dim_products`. Keys are deterministic MD5
hashes over natural identifiers (length-prefixed composites); natural IDs remain
for lineage.

### 4.4 Facts (4 tables)

`fact_orders`, `fact_order_items`, `fact_payments`, `fact_reviews`.
`fact_orders` aggregates items, payments, and reviews independently before the
join. `fact_reviews.review_key` is stable across rebuilds.

### 4.5 Analytical marts (9 tables)

| Model | Grain | Purpose |
|---|---|---|
| `mart_sales_daily` | one date | daily sales and AOV |
| `mart_delivery_monthly` | one month | late rate over orders with a delivery timestamp |
| `mart_category_performance` | one category | order-weighted review score |
| `mart_seller_performance` | one seller | order-weighted late rate and review score |
| `mart_customer_rfm` | one `customer_unique_id` | person-level RFM |
| `mart_payment_mix_monthly` | month × payment type | payment mix |
| `mart_review_monthly` | one month | review volume/score/text/latency |
| `mart_payment_reconciliation` | one order status | payment vs item mismatch |
| `mart_data_quality_flags` | one flag | retained anomaly counts |

See `docs/dbt_models.md` for row counts and the corrected metric definitions.

---

## 5. Relationships and grains

```text
customers 1 ── * orders 1 ── * order_items * ── 1 products * ── 1 category_translation
                              │
                              ├── * order_payments
                              └── * order_reviews

customers.customer_zip_code_prefix ── soft ── geolocation.zip_code_prefix
sellers.seller_zip_code_prefix     ── soft ── geolocation.zip_code_prefix
```

| Relationship | Cardinality | Notes |
|---|---|---|
| `orders.customer_id → customers.customer_id` | 1:1 in snapshot | `customer_id` is order-scoped |
| `order_items.order_id → orders.order_id` | N:1 | 775 orders have no items |
| `order_items.product_id → products.product_id` | N:1 | 0 orphans |
| `order_items.seller_id → sellers.seller_id` | N:1 | 0 orphans |
| `order_payments.order_id → orders.order_id` | N:1 | 1 order has no payment |
| `order_reviews.order_id → orders.order_id` | N:1 | 768 orders have no review |
| `products.product_category_name → category_translation` | N:1 | Missing mapped to `unknown` |
| customer/seller zip → geolocation zip | soft N:M | 157 customer / 7 seller zips missing |

## 6. Quality flags and known counts

| Flag | Location | Count |
|---|---|---|
| Orders without items | `fact_orders.has_items = false` | 775 |
| Orders without payments | `fact_orders.has_payment = false` | 1 |
| Orders without reviews | `fact_orders.has_review = false` | 768 |
| Payment mismatches | `fact_orders.payment_mismatch` | 1,076 |
| Delivery anomalies | `fact_orders.delivery_anomaly` | 1,382 |
| Products missing category | `dim_products.category_missing` | 610 |
| Reviews before purchase | `fact_reviews.is_before_purchase` | 74 |
| Zero-value payments | `fact_payments.is_zero_value` | 9 |
| Zero-installment payments | `silver.order_payments.is_zero_installments` | 2 |
| Not-defined payments | `silver.order_payments.is_not_defined` | 3 |
| Zero-freight items | `silver.order_items.is_zero_freight` | 383 |
| Geolocation outliers | `silver.geolocation.is_outlier` | 33 points |
| Rejected Bronze rows | `bronze.rejected_rows` | 0 |
| Rejected Silver rows | `silver.rejected_rows` | 0 |

## 7. Timestamp and currency conventions

- All timestamps are naive and interpreted as `America/Sao_Paulo`.
- `order_purchase_timestamp` is the business event time.
- `review_creation_date` and `order_estimated_delivery_date` are date-only at
  midnight.
- Delivery days are calendar-date differences, not 24-hour durations.
- Currency is BRL, stored as `numeric`, never float.
