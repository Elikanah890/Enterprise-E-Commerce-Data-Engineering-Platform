-- Gold fact: one row per review record.
-- Grain: one review record; (review_id, order_id) is unique.
-- An order may have multiple reviews.

DROP TABLE IF EXISTS gold.fact_reviews CASCADE;

CREATE TABLE gold.fact_reviews AS
SELECT r.review_sk,
       r.review_id,
       r.order_id,
       o.order_purchase_timestamp::date                          AS order_date,
       TO_CHAR(o.order_purchase_timestamp, 'YYYYMMDD')::integer  AS order_date_key,
       o.order_status,
       r.review_score,
       r.review_creation_date,
       r.review_answer_timestamp,
       ROUND(
           EXTRACT(EPOCH FROM (r.review_answer_timestamp - r.review_creation_date))
           / 3600.0,
           2
       ) AS answer_latency_hours,
       (r.review_creation_date::date - o.order_purchase_timestamp::date)
           AS review_latency_days,
       r.has_title,
       r.has_message,
       LENGTH(r.review_comment_title)   AS title_length,
       LENGTH(r.review_comment_message) AS message_length,
       r.is_before_purchase
FROM silver.order_reviews r
JOIN silver.orders o ON r.order_id = o.order_id;

ALTER TABLE gold.fact_reviews ADD PRIMARY KEY (review_sk);
ALTER TABLE gold.fact_reviews
    ADD CONSTRAINT uq_fact_reviews_review_order UNIQUE (review_id, order_id);
CREATE INDEX idx_fact_reviews_order ON gold.fact_reviews(order_id);
CREATE INDEX idx_fact_reviews_score ON gold.fact_reviews(review_score);
CREATE INDEX idx_fact_reviews_date ON gold.fact_reviews(order_date_key);
