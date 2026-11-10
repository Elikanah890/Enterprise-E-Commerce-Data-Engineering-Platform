select order_status
from {{ ref('mart_payment_reconciliation') }}
where mismatch_orders > orders
   or item_orders > orders
   or paid_orders > orders
   or underpaid_orders + overpaid_orders > mismatch_orders

union all

select 'total'
where (
    select sum(orders)
    from {{ ref('mart_payment_reconciliation') }}
) <> (
    select count(*)
    from {{ ref('fact_orders') }}
)
