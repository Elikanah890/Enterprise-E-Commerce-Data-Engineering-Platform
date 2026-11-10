select
    date_trunc('month', order_purchase_timestamp)::date as month,
    count(*) filter (where order_status = 'delivered') as delivered_orders,
    round(avg(delivery_days) filter (where is_delivered and delivery_days is not null), 2)
        as avg_delivery_days,
    count(*) filter (where is_late is true) as late_orders,
    count(*) filter (where is_late is not null) as eligible_orders,
    round(
        100.0 * count(*) filter (where is_late is true)
        / nullif(count(*) filter (where is_late is not null), 0),
        2
    ) as late_rate_pct
from {{ ref('fact_orders') }}
group by 1
