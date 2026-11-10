select
    p.order_id,
    p.payment_sequential,
    {{ generate_stable_key(['p.order_id', 'p.payment_sequential']) }} as payment_key,
    {{ generate_stable_key(['o.customer_id']) }} as customer_key,
    to_char(o.order_purchase_timestamp, 'YYYYMMDD')::integer as order_date_key,
    p.payment_type,
    p.payment_installments,
    p.payment_value,
    p.is_zero_value,
    p.is_zero_installments,
    p.is_not_defined,
    o.order_status
from {{ ref('stg_order_payments') }} as p
inner join {{ ref('stg_orders') }} as o
    on p.order_id = o.order_id
