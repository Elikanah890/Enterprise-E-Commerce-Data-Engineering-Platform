select
    order_id,
    count(*) as item_count,
    sum(price) as item_revenue,
    sum(freight_value) as freight_revenue,
    min(shipping_limit_date) as first_shipping_limit,
    max(shipping_limit_date) as last_shipping_limit
from {{ ref('stg_order_items') }}
group by order_id
