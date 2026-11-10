select
    rtrim(order_id) as order_id,
    rtrim(customer_id) as customer_id,
    order_status,
    order_purchase_timestamp,
    order_approved_at,
    order_delivered_carrier_date,
    order_delivered_customer_date,
    order_estimated_delivery_date,
    has_approved,
    has_carrier_date,
    has_delivery_date,
    delivery_anomaly
from {{ source('silver', 'orders') }}
