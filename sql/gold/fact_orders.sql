-- Gold fact: one row per order.
-- Item, payment, and review aggregates are pre-computed to avoid fan-out.
-- Payment totals and item revenue are NOT assumed to be interchangeable;
-- mismatches are flagged explicitly.

DROP TABLE IF EXISTS gold.fact_orders CASCADE;

CREATE TABLE gold.fact_orders AS
WITH item_agg AS (
    SELECT order_id,
           COUNT(*)                 AS item_count,
           SUM(price)               AS item_revenue,
           SUM(freight_value)       AS freight_revenue,
           MIN(shipping_limit_date) AS first_shipping_limit
    FROM silver.order_items
    GROUP BY order_id
),
payment_agg AS (
    SELECT order_id,
           COUNT(*)                    AS payment_count,
           SUM(payment_value)          AS payment_total,
           MAX(payment_installments)   AS max_installments
    FROM silver.order_payments
    GROUP BY order_id
),
review_agg AS (
    SELECT order_id,
           COUNT(*)          AS review_count,
           AVG(review_score) AS avg_review_score
    FROM silver.order_reviews
    GROUP BY order_id
)
SELECT o.order_id,
       o.customer_id,
       o.order_status,
       o.order_purchase_timestamp,
       o.order_purchase_timestamp::date                          AS order_date,
       TO_CHAR(o.order_purchase_timestamp, 'YYYYMMDD')::integer  AS order_date_key,
       o.order_approved_at,
       o.order_delivered_carrier_date,
       o.order_delivered_customer_date,
       o.order_estimated_delivery_date,
       CASE
           WHEN o.order_delivered_customer_date IS NULL THEN NULL
           ELSE (o.order_delivered_customer_date::date
                 - o.order_purchase_timestamp::date)
       END AS delivery_days,
       CASE
           WHEN o.order_delivered_customer_date IS NULL THEN FALSE
           WHEN o.order_delivered_customer_date > o.order_estimated_delivery_date
               THEN TRUE
           ELSE FALSE
       END AS is_late,
       CASE
           WHEN o.order_delivered_customer_date IS NULL THEN NULL
           ELSE (o.order_delivered_customer_date::date
                 - o.order_estimated_delivery_date::date)
       END AS days_vs_estimate,
       (o.order_status = 'delivered')  AS is_delivered,
       (o.order_status = 'canceled')   AS is_canceled,
       o.delivery_anomaly,
       COALESCE(i.item_count, 0)       AS item_count,
       COALESCE(i.item_revenue, 0)     AS item_revenue,
       COALESCE(i.freight_revenue, 0)  AS freight_revenue,
       COALESCE(i.item_revenue, 0) + COALESCE(i.freight_revenue, 0)
           AS gross_order_value,
       COALESCE(p.payment_count, 0)    AS payment_count,
       COALESCE(p.payment_total, 0)    AS payment_total,
       p.max_installments,
       r.avg_review_score,
       COALESCE(r.review_count, 0)     AS review_count,
       (COALESCE(i.item_count, 0) > 0)      AS has_items,
       (COALESCE(p.payment_count, 0) > 0)   AS has_payment,
       (COALESCE(r.review_count, 0) > 0)    AS has_review,
       (ABS(COALESCE(p.payment_total, 0)
            - (COALESCE(i.item_revenue, 0) + COALESCE(i.freight_revenue, 0)))
        > 0.01) AS payment_mismatch,
       (COALESCE(p.payment_total, 0)
        - (COALESCE(i.item_revenue, 0) + COALESCE(i.freight_revenue, 0)))
           AS payment_mismatch_amount
FROM silver.orders o
LEFT JOIN item_agg i     ON o.order_id = i.order_id
LEFT JOIN payment_agg p  ON o.order_id = p.order_id
LEFT JOIN review_agg r   ON o.order_id = r.order_id;

ALTER TABLE gold.fact_orders ADD PRIMARY KEY (order_id);
CREATE INDEX idx_fact_orders_customer ON gold.fact_orders(customer_id);
CREATE INDEX idx_fact_orders_date ON gold.fact_orders(order_date_key);
CREATE INDEX idx_fact_orders_status ON gold.fact_orders(order_status);
CREATE INDEX idx_fact_orders_mismatch
    ON gold.fact_orders(order_id) WHERE payment_mismatch;
