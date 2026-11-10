select
    order_id,
    count(*) as payment_count,
    sum(payment_value) as payment_total,
    max(payment_installments) as max_installments
from {{ ref('stg_order_payments') }}
group by order_id
