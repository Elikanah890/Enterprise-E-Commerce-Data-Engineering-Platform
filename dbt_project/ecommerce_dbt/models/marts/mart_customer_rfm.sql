with anchor as (
    select max(order_date) as max_date
    from {{ ref('fact_orders') }}
),

customer_metrics as (
    select
        c.customer_unique_id,
        max(o.order_date) as last_order,
        count(*) as frequency,
        sum(o.gross_order_value) as monetary
    from {{ ref('fact_orders') }} as o
    inner join {{ ref('dim_customers') }} as c
        on o.customer_key = c.customer_key
    where o.order_status not in ('canceled', 'unavailable')
    group by c.customer_unique_id
),

scored as (
    select
        m.customer_unique_id,
        m.last_order,
        (a.max_date - m.last_order) as recency_days,
        m.frequency,
        m.monetary,
        ntile(5) over (order by (a.max_date - m.last_order) desc) as r_score,
        ntile(5) over (order by m.frequency) as f_score,
        ntile(5) over (order by m.monetary) as m_score
    from customer_metrics as m
    cross join anchor as a
)

select
    customer_unique_id,
    last_order,
    recency_days,
    frequency,
    monetary,
    r_score,
    f_score,
    m_score,
    r_score + f_score + m_score as rfm_total,
    case
        when r_score >= 4 and f_score >= 4 and m_score >= 4 then 'Champions'
        when r_score >= 3 and f_score >= 3 then 'Loyal'
        when r_score <= 2 and f_score >= 3 then 'At Risk'
        when r_score <= 2 and f_score <= 2 then 'Lost'
        else 'Others'
    end as segment
from scored
