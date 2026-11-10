select
    s.seller_id,
    s.seller_state,
    count(*) as orders,
    sum(o.item_count) as items,
    sum(o.item_revenue) as revenue,
    sum(o.freight_revenue) as freight,
    round(avg(r.avg_review_score), 2) as avg_review_score,
    count(*) filter (where o.is_late is true) as late_orders,
    round(
        100.0 * count(*) filter (where o.is_late is true)
        / nullif(count(*), 0),
        2
    ) as late_rate_pct
from {{ ref('int_seller_order_outcomes') }} as o
inner join {{ ref('dim_sellers') }} as s
    on o.seller_id = s.seller_id
left join {{ ref('int_review_metrics') }} as r
    on o.order_id = r.order_id
group by s.seller_id, s.seller_state
