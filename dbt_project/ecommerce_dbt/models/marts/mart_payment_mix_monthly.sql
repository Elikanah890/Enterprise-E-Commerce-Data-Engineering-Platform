select
    date_trunc('month', o.order_purchase_timestamp)::date as month,
    p.payment_type,
    count(*) as payments,
    sum(p.payment_value) as value,
    round(avg(p.payment_installments), 2) as avg_installments
from {{ ref('fact_payments') }} as p
inner join {{ ref('fact_orders') }} as o
    on p.order_id = o.order_id
group by 1, 2
