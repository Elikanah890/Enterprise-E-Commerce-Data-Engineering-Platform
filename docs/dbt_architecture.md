# dbt architecture

## Status

Implemented and live-validated on 2026-11-05 against PostgreSQL 16.15. The
development branch is isolated in three schemas and does not replace Gold:

```text
Python ingestion
    -> bronze
    -> existing Silver SQL
    -> silver (dbt sources, read-only)
    -> dbt staging views       -> dbt_dev_staging
    -> dbt intermediate views  -> dbt_dev_intermediate
    -> dbt dimensions/facts/marts tables -> dbt_dev_marts
```

Gold remains the existing production comparison layer. No dbt model targets
`gold`, and no dbt run modified Bronze, Silver, or Gold.

## Project shape

| Layer | Models | Materialization | Schema |
|---|---:|---|---|
| Staging | 9 | View | `dbt_dev_staging` |
| Intermediate | 5 | View | `dbt_dev_intermediate` |
| Dimensions | 6 | Table | `dbt_dev_marts` |
| Facts | 4 | Table | `dbt_dev_marts` |
| Analytical marts | 9 | Table | `dbt_dev_marts` |

The profile target is `dbt_dev`; it is a routing label, not a created schema.
`generate_schema_name` maps model layers to the three `dbt_dev_*` schemas and
rejects any other target or unsupported resource type. Sources are declared in `models/staging/_sources.yml` for the
9 Silver data tables.

## Dependency map

```text
source('silver', ...)
  +-- stg_category_translation --+-- dim_category -------------------+
  +-- stg_customers -------------+-- dim_customers ------------------+-- fact_orders
  +-- stg_geolocation -----------+-- dim_geolocation --+             +-- fact_order_items
  +-- stg_sellers ---------------+-- dim_sellers -------+             +-- fact_payments
  +-- stg_products --------------+-- dim_products ------+             +-- fact_reviews
  +-- stg_orders ----------------+-- dim_date ------------------------+
  +-- stg_order_items -----------+-- int_order_item_metrics ----------+
  |                              +-- int_order_category_metrics ------+-- mart_category_performance
  |                              +-- int_seller_order_outcomes -------+-- mart_seller_performance
  +-- stg_order_payments --------+-- int_payment_metrics -------------+
  +-- stg_order_reviews ---------+-- int_review_metrics --------------+

fact_orders -> mart_sales_daily, mart_delivery_monthly, mart_customer_rfm,
              mart_payment_reconciliation, mart_data_quality_flags
fact_payments + fact_orders -> mart_payment_mix_monthly
fact_reviews -> mart_review_monthly
```

## Grains

| Model group | Grain |
|---|---|
| Staging | Same as its Silver source; projection and fixed-width `CHAR` cleanup only |
| `int_order_item_metrics` | One order |
| `int_payment_metrics` | One order |
| `int_review_metrics` | One order |
| `int_order_category_metrics` | One order/category |
| `int_seller_order_outcomes` | One seller/order |
| `dim_customers`, `dim_sellers`, `dim_products` | One business entity |
| `dim_category` | One natural category name |
| `dim_geolocation` | One zip prefix |
| `dim_date` | One calendar day |
| `fact_orders` | One order |
| `fact_order_items` | One `(order_id, order_item_id)` |
| `fact_payments` | One `(order_id, payment_sequential)` |
| `fact_reviews` | One `(review_id, order_id)` |
| Analytical marts | One row per declared month/category/seller/customer/status/flag grain |

Item, payment, and review measures are aggregated to order grain before joining
into `fact_orders`. Seller outcomes are aggregated to seller/order before
late-rate calculation. Category review scores are reduced to one order/category
row before averaging.

## Keys

`dim_date` uses an integer `YYYYMMDD` key. Customer, seller, product, category,
order, order-item, payment, and review keys are deterministic MD5 hashes over
natural identifiers, with length-prefixed composite values. Natural identifiers
remain available for lineage. No model uses Silver's rebuild-unstable
`geo_id` or `review_sk` sequence as a warehouse key.

Key hashes were identical across consecutive builds for all dimensions, and
`fact_reviews.review_key` was identical across three builds.

## Calendar

`dim_date` spans 2016-01-01 through 2019-12-31 (1,461 rows), matching the
existing Gold calendar. The bounds are derived from the first order year
through the year after the latest order year. It is not extended by anomalous
2020 shipping or review-answer timestamps.

## Delivery and seller logic

`fact_orders.is_late` is:

```text
order_delivered_customer_date > order_estimated_delivery_date
```

The comparison uses timestamps, not truncated dates. `is_late` is null only
when there is no customer-delivery timestamp. The delivery mart uses orders
with a known delivery timestamp for both numerator and denominator:
7,827 late / 96,476 eligible = 8.11%.

Gold reports the same 7,827 late orders and 8.11% rounded rate, but its
denominator is delivered-status orders (96,478). The 2-row difference is the
intentional population correction. The 7.87% figure is `7,827 / 99,441`; it
uses all orders, not the delivery population.

`mart_seller_performance.late_rate_pct` is order-weighted over all
seller-order pairs: late seller-orders / all seller-orders. It is not
item-weighted. This corrects 366 sellers by more than 1 percentage point versus
Gold, with a maximum difference of 37.40pp.

For item-level `shipped_after_limit`, the model compares carrier handoff with
the seller deadline:

```text
order_delivered_carrier_date > shipping_limit_date
```

Corrected count: 10,423. Gold's old rule
(`shipping_limit_date > order_delivered_customer_date`) produces 23,000; the
two rules overlap on only 16 items.

## Review metrics

`mart_category_performance.avg_review_score` is weighted by order/category, so
an order with several items in one category contributes one score. This
corrects 69 of 74 categories versus Gold, with a maximum difference of 0.48
stars.

`mart_seller_performance.avg_review_score` is also order-weighted. It differs
from Gold's item-weighted value for 1,242 sellers, maximum 1.67 stars. This is
an intentional corrected metric, not a parity claim.

## RFM

`mart_customer_rfm` has exact row count, recency, frequency, and monetary parity
with Gold. Sixty-one segment labels can differ because Gold uses `NTILE` over
tied values without a deterministic tie-breaker. Repeated dbt builds were
stable; the difference is a tie-labeling difference, not changed input data.

## Materialization and safety

- Staging and intermediate are views; dimensions, facts, and marts are tables.
- All builds are full table/view replacements; no incremental models exist.
- No dbt packages, seeds, snapshots, aliases to Gold, or `--full-refresh` runs.
- The dbt login has no access to Bronze or Gold and only `SELECT` on Silver.

See [dbt_models.md](./dbt_models.md) and
[progress/dbt_implementation_report.md](./progress/dbt_implementation_report.md).
