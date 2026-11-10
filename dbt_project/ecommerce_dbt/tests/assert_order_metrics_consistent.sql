select order_id
from {{ ref('fact_orders') }}
where gross_order_value <> item_revenue + freight_revenue
   or payment_mismatch is distinct from (
        abs(payment_total - gross_order_value) > 0.01
   )
   or payment_mismatch_amount <> payment_total - gross_order_value
