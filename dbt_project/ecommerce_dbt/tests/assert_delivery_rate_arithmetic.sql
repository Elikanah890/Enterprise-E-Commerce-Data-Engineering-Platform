select month
from {{ ref('mart_delivery_monthly') }}
where late_rate_pct is distinct from round(
        100.0 * late_orders / nullif(eligible_orders, 0),
        2
    )
   or late_orders > eligible_orders
