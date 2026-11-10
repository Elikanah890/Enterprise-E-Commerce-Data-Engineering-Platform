-- Gold analytical views used by dashboards and notebooks.

DROP VIEW IF EXISTS gold.vw_sales_daily CASCADE;
DROP VIEW IF EXISTS gold.vw_delivery_performance CASCADE;
DROP VIEW IF EXISTS gold.vw_customer_rfm CASCADE;
DROP VIEW IF EXISTS gold.vw_category_performance CASCADE;
DROP VIEW IF EXISTS gold.vw_seller_performance CASCADE;
DROP VIEW IF EXISTS gold.vw_payment_mix CASCADE;
DROP VIEW IF EXISTS gold.vw_review_summary CASCADE;
DROP VIEW IF EXISTS gold.vw_payment_reconciliation CASCADE;
DROP VIEW IF EXISTS gold.vw_data_quality_flags CASCADE;

-- Daily sales (canceled/unavailable orders excluded)
CREATE VIEW gold.vw_sales_daily AS
SELECT order_date,
       order_date_key,
       COUNT(*)                                      AS orders,
       SUM(item_revenue)                             AS revenue,
       SUM(freight_revenue)                          AS freight,
       SUM(gross_order_value)                        AS gross_value,
       ROUND(AVG(gross_order_value), 2)              AS avg_order_value
FROM gold.fact_orders
WHERE order_status NOT IN ('canceled', 'unavailable')
GROUP BY order_date, order_date_key;

-- Monthly delivery performance
CREATE VIEW gold.vw_delivery_performance AS
SELECT DATE_TRUNC('month', order_purchase_timestamp)::date AS month,
       COUNT(*) FILTER (WHERE order_status = 'delivered')  AS delivered_orders,
       ROUND(AVG(delivery_days) FILTER (WHERE order_status = 'delivered'), 2)
           AS avg_delivery_days,
       COUNT(*) FILTER (WHERE is_late)                     AS late_orders,
       ROUND(
           100.0 * COUNT(*) FILTER (WHERE is_late)
           / NULLIF(COUNT(*) FILTER (WHERE order_status = 'delivered'), 0),
           2
       ) AS late_rate_pct
FROM gold.fact_orders
GROUP BY 1
ORDER BY 1;

-- Customer RFM segmentation (person-level via customer_unique_id)
CREATE VIEW gold.vw_customer_rfm AS
WITH anchor AS (
    SELECT MAX(order_purchase_timestamp::date) AS max_date
    FROM gold.fact_orders
),
base AS (
    SELECT c.customer_unique_id,
           MAX(o.order_purchase_timestamp::date) AS last_order,
           COUNT(*)                              AS frequency,
           SUM(o.gross_order_value)              AS monetary,
           MAX(a.max_date)                       AS max_date
    FROM gold.fact_orders o
    JOIN gold.dim_customers c ON o.customer_id = c.customer_id
    CROSS JOIN anchor a
    WHERE o.order_status NOT IN ('canceled', 'unavailable')
    GROUP BY c.customer_unique_id
),
scored AS (
    SELECT customer_unique_id,
           last_order,
           (max_date - last_order) AS recency_days,
           frequency,
           monetary,
           NTILE(5) OVER (ORDER BY (max_date - last_order) DESC) AS r_score,
           NTILE(5) OVER (ORDER BY frequency)                    AS f_score,
           NTILE(5) OVER (ORDER BY monetary)                     AS m_score
    FROM base
)
SELECT customer_unique_id,
       last_order,
       recency_days,
       frequency,
       monetary,
       r_score,
       f_score,
       m_score,
       (r_score + f_score + m_score) AS rfm_total,
       CASE
           WHEN r_score >= 4 AND f_score >= 4 AND m_score >= 4 THEN 'Champions'
           WHEN r_score >= 3 AND f_score >= 3                  THEN 'Loyal'
           WHEN r_score <= 2 AND f_score >= 3                  THEN 'At Risk'
           WHEN r_score <= 2 AND f_score <= 2                  THEN 'Lost'
           ELSE 'Others'
       END AS segment
FROM scored;

-- Category performance
CREATE VIEW gold.vw_category_performance AS
SELECT p.product_category_name_english AS category,
       COUNT(DISTINCT i.order_id)      AS orders,
       COUNT(*)                        AS items,
       SUM(i.price)                    AS revenue,
       SUM(i.freight_value)            AS freight,
       ROUND(AVG(i.price), 2)          AS avg_price,
       ROUND(AVG(o.avg_review_score), 2) AS avg_review_score
FROM gold.fact_order_items i
JOIN gold.dim_products p ON i.product_id = p.product_id
LEFT JOIN gold.fact_orders o ON i.order_id = o.order_id
GROUP BY p.product_category_name_english;

-- Seller performance
CREATE VIEW gold.vw_seller_performance AS
SELECT s.seller_id,
       s.seller_state,
       COUNT(DISTINCT i.order_id) AS orders,
       COUNT(*)                   AS items,
       SUM(i.price)               AS revenue,
       SUM(i.freight_value)       AS freight,
       ROUND(AVG(o.avg_review_score), 2) AS avg_review_score,
       ROUND(
           100.0 * COUNT(*) FILTER (WHERE o.is_late) / NULLIF(COUNT(*), 0),
           2
       ) AS late_rate_pct
FROM gold.fact_order_items i
JOIN gold.dim_sellers s ON i.seller_id = s.seller_id
JOIN gold.fact_orders o ON i.order_id = o.order_id
GROUP BY s.seller_id, s.seller_state;

-- Payment method mix by month
CREATE VIEW gold.vw_payment_mix AS
SELECT DATE_TRUNC('month', o.order_purchase_timestamp)::date AS month,
       p.payment_type,
       COUNT(*)                          AS payments,
       SUM(p.payment_value)              AS value,
       ROUND(AVG(p.payment_installments), 2) AS avg_installments
FROM gold.fact_payments p
JOIN gold.fact_orders o ON p.order_id = o.order_id
GROUP BY 1, 2
ORDER BY 1, 2;

-- Review summary by month
CREATE VIEW gold.vw_review_summary AS
SELECT DATE_TRUNC('month', review_creation_date)::date AS month,
       COUNT(*)                                        AS reviews,
       ROUND(AVG(review_score), 2)                     AS avg_score,
       ROUND(
           100.0 * COUNT(*) FILTER (WHERE review_score <= 2) / NULLIF(COUNT(*), 0),
           2
       ) AS pct_low_score,
       ROUND(
           100.0 * COUNT(*) FILTER (WHERE has_message) / NULLIF(COUNT(*), 0),
           2
       ) AS pct_with_text,
       ROUND(AVG(answer_latency_hours), 2)             AS avg_answer_hours
FROM gold.fact_reviews
GROUP BY 1
ORDER BY 1;

-- Payment reconciliation by order status
CREATE VIEW gold.vw_payment_reconciliation AS
SELECT order_status,
       COUNT(*)                                            AS orders,
       COUNT(*) FILTER (WHERE has_items)                   AS item_orders,
       COUNT(*) FILTER (WHERE has_payment)                 AS paid_orders,
       COUNT(*) FILTER (WHERE payment_mismatch)            AS mismatch_orders,
       COUNT(*) FILTER (WHERE payment_mismatch_amount < -0.01) AS underpaid_orders,
       COUNT(*) FILTER (WHERE payment_mismatch_amount > 0.01)  AS overpaid_orders,
       ROUND(SUM(payment_mismatch_amount), 2)              AS net_mismatch_amount
FROM gold.fact_orders
GROUP BY order_status;

-- Data-quality flag counts for the engineering dashboard
CREATE VIEW gold.vw_data_quality_flags AS
SELECT 'orders_without_items' AS flag, COUNT(*) AS rows
FROM gold.fact_orders WHERE NOT has_items
UNION ALL
SELECT 'orders_without_payments', COUNT(*)
FROM gold.fact_orders WHERE NOT has_payment
UNION ALL
SELECT 'orders_without_reviews', COUNT(*)
FROM gold.fact_orders WHERE NOT has_review
UNION ALL
SELECT 'payment_mismatches', COUNT(*)
FROM gold.fact_orders WHERE payment_mismatch
UNION ALL
SELECT 'delivery_anomalies', COUNT(*)
FROM gold.fact_orders WHERE delivery_anomaly
UNION ALL
SELECT 'products_missing_category', COUNT(*)
FROM gold.dim_products WHERE category_missing
UNION ALL
SELECT 'reviews_before_purchase', COUNT(*)
FROM gold.fact_reviews WHERE is_before_purchase
UNION ALL
SELECT 'zero_value_payments', COUNT(*)
FROM gold.fact_payments WHERE is_zero_value;
