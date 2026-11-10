select
    order_status,
    count(*) as orders,
    count(*) filter (where has_items) as item_orders,
    count(*) filter (where has_payment) as paid_orders,
    count(*) filter (where payment_mismatch) as mismatch_orders,
    count(*) filter (where payment_mismatch_amount < -0.01) as underpaid_orders,
    count(*) filter (where payment_mismatch_amount > 0.01) as overpaid_orders,
    round(sum(payment_mismatch_amount), 2) as net_mismatch_amount
from {{ ref('fact_orders') }}
group by order_status
