select
    rtrim(order_id) as order_id,
    order_item_id,
    rtrim(product_id) as product_id,
    rtrim(seller_id) as seller_id,
    shipping_limit_date,
    price,
    freight_value,
    is_zero_freight
from {{ source('silver', 'order_items') }}
