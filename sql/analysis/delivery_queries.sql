-- Delivery analysis queries.

-- Monthly delivery performance
SELECT month,
       delivered_orders,
       avg_delivery_days,
       late_orders,
       late_rate_pct
FROM gold.vw_delivery_performance
ORDER BY month;

-- Late-delivery rate by customer state
SELECT c.customer_state,
       COUNT(*)                                          AS delivered_orders,
       COUNT(*) FILTER (WHERE o.is_late)                 AS late_orders,
       ROUND(100.0 * COUNT(*) FILTER (WHERE o.is_late)
             / NULLIF(COUNT(*), 0), 2)                   AS late_rate_pct
FROM gold.fact_orders o
JOIN gold.dim_customers c ON o.customer_id = c.customer_id
WHERE o.order_status = 'delivered'
GROUP BY c.customer_state
ORDER BY late_rate_pct DESC;

-- Delivery-time distribution buckets
SELECT CASE
           WHEN delivery_days <= 3  THEN '0-3 days'
           WHEN delivery_days <= 7  THEN '4-7 days'
           WHEN delivery_days <= 14 THEN '8-14 days'
           WHEN delivery_days <= 30 THEN '15-30 days'
           ELSE '30+ days'
       END AS bucket,
       COUNT(*) AS orders
FROM gold.fact_orders
WHERE order_status = 'delivered'
  AND delivery_days IS NOT NULL
GROUP BY bucket
ORDER BY MIN(delivery_days);
