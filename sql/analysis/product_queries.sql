-- Product analysis queries.

-- Category ranking by revenue
SELECT category,
       orders,
       items,
       revenue,
       freight,
       avg_price,
       avg_review_score
FROM gold.vw_category_performance
ORDER BY revenue DESC;

-- Product-level revenue (top 25)
SELECT i.product_id,
       p.product_category_name_english AS category,
       COUNT(*)          AS items_sold,
       SUM(i.price)      AS revenue,
       ROUND(AVG(i.price), 2) AS avg_price
FROM gold.fact_order_items i
JOIN gold.dim_products p ON i.product_id = p.product_id
GROUP BY i.product_id, p.product_category_name_english
ORDER BY revenue DESC
LIMIT 25;

-- Freight burden by category
SELECT category,
       revenue,
       freight,
       ROUND(100.0 * freight / NULLIF(revenue, 0), 2) AS freight_pct_of_revenue
FROM gold.vw_category_performance
ORDER BY freight_pct_of_revenue DESC;
