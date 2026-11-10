select
    c.product_category_name_english as category,
    c.product_category_name,
    count(*) as orders,
    sum(cm.item_count) as items,
    sum(cm.item_revenue) as revenue,
    sum(cm.freight_revenue) as freight,
    round(sum(cm.item_revenue) / nullif(sum(cm.item_count), 0), 2) as avg_price,
    round(avg(r.avg_review_score), 2) as avg_review_score,
    count(*) filter (where r.avg_review_score is not null) as reviewed_orders
from {{ ref('int_order_category_metrics') }} as cm
inner join {{ ref('dim_category') }} as c
    on cm.product_category_name = c.product_category_name
left join {{ ref('int_review_metrics') }} as r
    on cm.order_id = r.order_id
group by c.product_category_name_english, c.product_category_name
