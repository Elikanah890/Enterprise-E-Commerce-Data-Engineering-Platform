-- Gold fact: one row per order item.
-- Grain: (order_id, order_item_id).

DROP TABLE IF EXISTS gold.fact_order_items CASCADE;

CREATE TABLE gold.fact_order_items AS
SELECT i.order_id,
       i.order_item_id,
       i.product_id,
       i.seller_id,
       o.order_purchase_timestamp::date                          AS order_date,
       TO_CHAR(o.order_purchase_timestamp, 'YYYYMMDD')::integer  AS order_date_key,
       o.order_status,
       i.shipping_limit_date,
       i.price,
       i.freight_value,
       (i.price + i.freight_value) AS total_value,
       i.is_zero_freight,
       o.order_delivered_customer_date,
       CASE
           WHEN o.order_delivered_customer_date IS NULL THEN NULL
           ELSE (o.order_delivered_customer_date::date
                 - o.order_purchase_timestamp::date)
       END AS delivery_days,
       CASE
           WHEN o.order_delivered_customer_date IS NULL THEN NULL
           WHEN i.shipping_limit_date > o.order_delivered_customer_date THEN TRUE
           ELSE FALSE
       END AS shipped_after_limit
FROM silver.order_items i
JOIN silver.orders o ON i.order_id = o.order_id;

ALTER TABLE gold.fact_order_items
    ADD PRIMARY KEY (order_id, order_item_id);
CREATE INDEX idx_fact_items_product ON gold.fact_order_items(product_id);
CREATE INDEX idx_fact_items_seller ON gold.fact_order_items(seller_id);
CREATE INDEX idx_fact_items_date ON gold.fact_order_items(order_date_key);
