with seller_orders as (
    select
        seller_id,
        order_id,
        count(*) as item_count,
        sum(price) as item_revenue,
        sum(freight_value) as freight_revenue
    from {{ ref('stg_order_items') }}
    group by seller_id, order_id
)

select
    so.seller_id,
    so.order_id,
    so.item_count,
    so.item_revenue,
    so.freight_revenue,
    o.order_status,
    case
        when o.order_delivered_customer_date is null then null
        else o.order_delivered_customer_date
            > o.order_estimated_delivery_date
    end as is_late
from seller_orders as so
inner join {{ ref('stg_orders') }} as o
    on so.order_id = o.order_id
