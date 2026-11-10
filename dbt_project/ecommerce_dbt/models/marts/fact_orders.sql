with orders as (
    select *
    from {{ ref('stg_orders') }}
),

item_metrics as (
    select *
    from {{ ref('int_order_item_metrics') }}
),

payment_metrics as (
    select *
    from {{ ref('int_payment_metrics') }}
),

review_metrics as (
    select *
    from {{ ref('int_review_metrics') }}
)

select
    o.order_id,
    {{ generate_stable_key(['o.order_id']) }} as order_key,
    {{ generate_stable_key(['o.customer_id']) }} as customer_key,
    to_char(o.order_purchase_timestamp, 'YYYYMMDD')::integer as order_date_key,
    o.order_status,
    o.order_purchase_timestamp,
    o.order_purchase_timestamp::date as order_date,
    o.order_approved_at,
    o.order_delivered_carrier_date,
    o.order_delivered_customer_date,
    o.order_estimated_delivery_date,
    case
        when o.order_delivered_customer_date is null then null
        else o.order_delivered_customer_date::date - o.order_purchase_timestamp::date
    end as delivery_days,
    case
        when o.order_delivered_customer_date is null then null
        else o.order_delivered_customer_date
            > o.order_estimated_delivery_date
    end as is_late,
    case
        when o.order_delivered_customer_date is null then null
        else o.order_delivered_customer_date::date
            - o.order_estimated_delivery_date::date
    end as days_vs_estimate,
    (o.order_status = 'delivered') as is_delivered,
    (o.order_status = 'canceled') as is_canceled,
    o.delivery_anomaly,
    coalesce(i.item_count, 0) as item_count,
    coalesce(i.item_revenue, 0) as item_revenue,
    coalesce(i.freight_revenue, 0) as freight_revenue,
    coalesce(i.item_revenue, 0) + coalesce(i.freight_revenue, 0) as gross_order_value,
    coalesce(p.payment_count, 0) as payment_count,
    coalesce(p.payment_total, 0) as payment_total,
    p.max_installments,
    r.avg_review_score,
    coalesce(r.review_count, 0) as review_count,
    (coalesce(i.item_count, 0) > 0) as has_items,
    (coalesce(p.payment_count, 0) > 0) as has_payment,
    (coalesce(r.review_count, 0) > 0) as has_review,
    (
        abs(
            coalesce(p.payment_total, 0)
            - coalesce(i.item_revenue, 0)
            - coalesce(i.freight_revenue, 0)
        ) > 0.01
    ) as payment_mismatch,
    (
        coalesce(p.payment_total, 0)
        - coalesce(i.item_revenue, 0)
        - coalesce(i.freight_revenue, 0)
    ) as payment_mismatch_amount
from orders as o
left join item_metrics as i
    on o.order_id = i.order_id
left join payment_metrics as p
    on o.order_id = p.order_id
left join review_metrics as r
    on o.order_id = r.order_id
