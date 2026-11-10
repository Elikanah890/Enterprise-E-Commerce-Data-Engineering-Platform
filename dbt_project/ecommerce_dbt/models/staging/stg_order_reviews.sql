select
    rtrim(review_id) as review_id,
    rtrim(order_id) as order_id,
    review_score,
    review_comment_title,
    review_comment_message,
    review_creation_date,
    review_answer_timestamp,
    has_title,
    has_message,
    is_before_purchase
from {{ source('silver', 'order_reviews') }}
