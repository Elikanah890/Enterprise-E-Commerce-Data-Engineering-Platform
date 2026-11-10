select
    rtrim(order_id) as order_id,
    payment_sequential,
    payment_type,
    payment_installments,
    payment_value,
    is_zero_value,
    is_zero_installments,
    is_not_defined
from {{ source('silver', 'order_payments') }}
