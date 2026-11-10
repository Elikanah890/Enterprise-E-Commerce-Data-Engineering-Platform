with expected as (
    select
        c.product_category_name,
        round(avg(r.avg_review_score), 2) as expected_score
    from {{ ref('int_order_category_metrics') }} as cm
    inner join {{ ref('dim_category') }} as c
        on cm.product_category_name = c.product_category_name
    left join {{ ref('int_review_metrics') }} as r
        on cm.order_id = r.order_id
    group by c.product_category_name
)

select m.product_category_name
from {{ ref('mart_category_performance') }} as m
inner join expected as e
    on m.product_category_name = e.product_category_name
where m.avg_review_score is distinct from e.expected_score
