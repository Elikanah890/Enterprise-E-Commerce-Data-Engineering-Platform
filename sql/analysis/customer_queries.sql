-- Customer analysis queries.

-- RFM segment summary
SELECT segment,
       COUNT(*)          AS customers,
       ROUND(AVG(recency_days), 1) AS avg_recency_days,
       ROUND(AVG(frequency), 2)    AS avg_orders,
       ROUND(SUM(monetary), 2)     AS monetary
FROM gold.vw_customer_rfm
GROUP BY segment
ORDER BY monetary DESC;

-- Customers by state
SELECT customer_state,
       COUNT(*) AS customers
FROM gold.dim_customers
GROUP BY customer_state
ORDER BY customers DESC;

-- Repeat buyer rate
WITH person_orders AS (
    SELECT c.customer_unique_id,
           COUNT(*) AS orders
    FROM gold.fact_orders o
    JOIN gold.dim_customers c ON o.customer_id = c.customer_id
    GROUP BY c.customer_unique_id
)
SELECT COUNT(*)                                           AS customers,
       COUNT(*) FILTER (WHERE orders > 1)                 AS repeat_customers,
       ROUND(100.0 * COUNT(*) FILTER (WHERE orders > 1)
             / NULLIF(COUNT(*), 0), 2)                    AS repeat_rate_pct
FROM person_orders;
