select 'monthly' as metric, month::text as key
from {{ ref('mart_delivery_monthly') }}
where late_orders > eligible_orders
   or late_rate_pct < 0
   or late_rate_pct > 100

union all

select 'seller' as metric, seller_id as key
from {{ ref('mart_seller_performance') }}
where late_orders > orders
   or late_rate_pct < 0
   or late_rate_pct > 100
