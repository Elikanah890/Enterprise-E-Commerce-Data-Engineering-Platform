-- Gold fact: one row per payment sequence.
-- Grain: (order_id, payment_sequential).

DROP TABLE IF EXISTS gold.fact_payments CASCADE;

CREATE TABLE gold.fact_payments AS
SELECT p.order_id,
       p.payment_sequential,
       p.payment_type,
       p.payment_installments,
       p.payment_value,
       p.is_zero_value,
       p.is_zero_installments,
       p.is_not_defined,
       o.order_purchase_timestamp::date                          AS order_date,
       TO_CHAR(o.order_purchase_timestamp, 'YYYYMMDD')::integer  AS order_date_key,
       o.order_status
FROM silver.order_payments p
JOIN silver.orders o ON p.order_id = o.order_id;

ALTER TABLE gold.fact_payments
    ADD PRIMARY KEY (order_id, payment_sequential);
CREATE INDEX idx_fact_payments_date ON gold.fact_payments(order_date_key);
CREATE INDEX idx_fact_payments_type ON gold.fact_payments(payment_type);
CREATE INDEX idx_fact_payments_zero_value
    ON gold.fact_payments(order_id) WHERE is_zero_value;
