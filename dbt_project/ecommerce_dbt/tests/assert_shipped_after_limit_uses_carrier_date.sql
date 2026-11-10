select order_id, order_item_id
from {{ ref('fact_order_items') }}
where shipped_after_limit is distinct from
    case
        when order_delivered_carrier_date is null then null
        else order_delivered_carrier_date > shipping_limit_date
    end
