select
    i.order_id,
    i.order_item_id,
    {{ generate_stable_key(['i.order_id', 'i.order_item_id']) }} as order_item_key,
    {{ generate_stable_key(['o.customer_id']) }} as customer_key,
    {{ generate_stable_key(['i.product_id']) }} as product_key,
    {{ generate_stable_key(['i.seller_id']) }} as seller_key,
    to_char(o.order_purchase_timestamp, 'YYYYMMDD')::integer as order_date_key,
    o.order_status,
    i.shipping_limit_date,
    i.price,
    i.freight_value,
    i.price + i.freight_value as total_value,
    i.is_zero_freight,
    o.order_delivered_carrier_date,
    o.order_delivered_customer_date,
    case
        when o.order_delivered_customer_date is null then null
        else o.order_delivered_customer_date::date - o.order_purchase_timestamp::date
    end as delivery_days,
    case
        when o.order_delivered_carrier_date is null then null
        else o.order_delivered_carrier_date > i.shipping_limit_date
    end as shipped_after_limit
from {{ ref('stg_order_items') }} as i
inner join {{ ref('stg_orders') }} as o
    on i.order_id = o.order_id
