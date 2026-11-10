with expected as (
    select
        s.seller_id,
        round(
            100.0 * count(*) filter (where o.is_late)
            / nullif(count(*), 0),
            2
        ) as expected_rate
    from {{ ref('int_seller_order_outcomes') }} as o
    inner join {{ ref('dim_sellers') }} as s
        on o.seller_id = s.seller_id
    group by s.seller_id
)

select m.seller_id
from {{ ref('mart_seller_performance') }} as m
inner join expected as e
    on m.seller_id = e.seller_id
where m.late_rate_pct is distinct from e.expected_rate
