select
    order_date,
    order_date_key,
    count(*) as orders,
    sum(item_revenue) as revenue,
    sum(freight_revenue) as freight,
    sum(gross_order_value) as gross_value,
    round(avg(gross_order_value), 2) as avg_order_value
from {{ ref('fact_orders') }}
where order_status not in ('canceled', 'unavailable')
group by order_date, order_date_key
