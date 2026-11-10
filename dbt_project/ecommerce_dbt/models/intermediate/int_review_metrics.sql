select
    order_id,
    count(*) as review_count,
    avg(review_score)::numeric as avg_review_score
from {{ ref('stg_order_reviews') }}
group by order_id
