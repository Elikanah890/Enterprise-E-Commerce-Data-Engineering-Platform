-- Sales analysis queries.

-- Monthly revenue and average order value
SELECT month,
       orders,
       revenue,
       freight,
       gross_value,
       avg_order_value
FROM gold.vw_sales_daily
ORDER BY order_date;

-- Revenue by month (aggregated)
SELECT DATE_TRUNC('month', order_date)::date AS month,
       SUM(orders)       AS orders,
       SUM(revenue)      AS revenue,
       SUM(freight)      AS freight,
       ROUND(SUM(revenue) / NULLIF(SUM(orders), 0), 2) AS revenue_per_order
FROM gold.vw_sales_daily
GROUP BY 1
ORDER BY 1;

-- Top categories by revenue
SELECT category, orders, items, revenue, avg_price, avg_review_score
FROM gold.vw_category_performance
ORDER BY revenue DESC
LIMIT 15;
