select
    p.product_category_name,
    i.order_id,
    count(*) as item_count,
    sum(i.price) as item_revenue,
    sum(i.freight_value) as freight_revenue
from {{ ref('stg_order_items') }} as i
inner join {{ ref('stg_products') }} as p
    on i.product_id = p.product_id
group by p.product_category_name, i.order_id
