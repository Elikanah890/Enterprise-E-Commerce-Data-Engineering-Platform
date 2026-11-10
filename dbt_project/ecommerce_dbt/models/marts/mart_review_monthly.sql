select
    date_trunc('month', review_creation_date)::date as month,
    count(*) as reviews,
    round(avg(review_score), 2) as avg_score,
    round(100.0 * count(*) filter (where review_score <= 2) / nullif(count(*), 0), 2)
        as pct_low_score,
    round(100.0 * count(*) filter (where has_message) / nullif(count(*), 0), 2)
        as pct_with_text,
    round(avg(answer_latency_hours), 2) as avg_answer_hours
from {{ ref('fact_reviews') }}
group by 1
