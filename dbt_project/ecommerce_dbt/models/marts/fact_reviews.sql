select
    r.review_id,
    r.order_id,
    {{ generate_stable_key(['r.review_id', 'r.order_id']) }} as review_key,
    {{ generate_stable_key(['o.customer_id']) }} as customer_key,
    to_char(o.order_purchase_timestamp, 'YYYYMMDD')::integer as order_date_key,
    to_char(r.review_creation_date, 'YYYYMMDD')::integer as review_date_key,
    o.order_status,
    r.review_score,
    r.review_creation_date,
    r.review_answer_timestamp,
    round(
        extract(epoch from (r.review_answer_timestamp - r.review_creation_date))
            / 3600.0,
        2
    ) as answer_latency_hours,
    r.review_creation_date::date - o.order_purchase_timestamp::date
        as review_latency_days,
    r.has_title,
    r.has_message,
    length(r.review_comment_title) as title_length,
    length(r.review_comment_message) as message_length,
    r.is_before_purchase
from {{ ref('stg_order_reviews') }} as r
inner join {{ ref('stg_orders') }} as o
    on r.order_id = o.order_id
