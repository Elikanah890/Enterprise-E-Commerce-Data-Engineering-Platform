select 'orders_without_items' as flag, count(*) as row_count
from {{ ref('fact_orders') }}
where not has_items

union all

select 'orders_without_payments', count(*)
from {{ ref('fact_orders') }}
where not has_payment

union all

select 'orders_without_reviews', count(*)
from {{ ref('fact_orders') }}
where not has_review

union all

select 'payment_mismatches', count(*)
from {{ ref('fact_orders') }}
where payment_mismatch

union all

select 'delivery_anomalies', count(*)
from {{ ref('fact_orders') }}
where delivery_anomaly

union all

select 'products_missing_category', count(*)
from {{ ref('dim_products') }}
where category_missing

union all

select 'reviews_before_purchase', count(*)
from {{ ref('fact_reviews') }}
where is_before_purchase

union all

select 'zero_value_payments', count(*)
from {{ ref('fact_payments') }}
where is_zero_value
