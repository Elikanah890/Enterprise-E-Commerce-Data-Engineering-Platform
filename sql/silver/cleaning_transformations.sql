-- Silver cleaning transformations.
-- Source: bronze.* (all text) -> silver.* (typed, constrained).
-- Rebuilds silver from bronze. Suspicious records are retained with flags;
-- malformed records are written to silver.rejected_rows.

BEGIN;

TRUNCATE TABLE
    silver.rejected_rows,
    silver.order_reviews,
    silver.order_payments,
    silver.order_items,
    silver.orders,
    silver.geolocation,
    silver.products,
    silver.sellers,
    silver.customers,
    silver.category_translation
RESTART IDENTITY CASCADE;

-- ---------------------------------------------------------------------------
-- Category translation (strip BOM, then add categories missing from source)
-- ---------------------------------------------------------------------------
INSERT INTO silver.rejected_rows (source_table, source_key, reason, raw_record)
SELECT 'bronze.category_translation',
       product_category_name,
       'missing category name',
       to_jsonb(t)
FROM bronze.category_translation t
WHERE TRIM(REPLACE(product_category_name, chr(65279), '')) = '';

INSERT INTO silver.category_translation (
    product_category_name,
    product_category_name_english
)
SELECT DISTINCT ON (clean_name)
       clean_name,
       TRIM(product_category_name_english)
FROM (
    SELECT TRIM(REPLACE(product_category_name, chr(65279), '')) AS clean_name,
           product_category_name_english
    FROM bronze.category_translation
    WHERE TRIM(REPLACE(product_category_name, chr(65279), '')) <> ''
) AS source
ORDER BY clean_name, product_category_name_english;

INSERT INTO silver.category_translation (
    product_category_name,
    product_category_name_english
)
VALUES
    ('unknown', 'unknown'),
    ('pc_gamer', 'pc_gamer'),
    ('portateis_cozinha_e_preparadores_de_alimentos',
     'portable_kitchen_food_preparers')
ON CONFLICT (product_category_name) DO NOTHING;

-- ---------------------------------------------------------------------------
-- Customers
-- ---------------------------------------------------------------------------
INSERT INTO silver.rejected_rows (source_table, source_key, reason, raw_record)
SELECT 'bronze.customers', customer_id,
       'missing customer_id, zip, or state', to_jsonb(c)
FROM bronze.customers c
WHERE customer_id = ''
   OR customer_zip_code_prefix = ''
   OR customer_state = '';

INSERT INTO silver.customers (
    customer_id,
    customer_unique_id,
    customer_zip_code_prefix,
    customer_city,
    customer_state
)
SELECT customer_id,
       customer_unique_id,
       LPAD(REGEXP_REPLACE(customer_zip_code_prefix, '\D', '', 'g'), 5, '0'),
       LOWER(TRIM(customer_city)),
       UPPER(TRIM(customer_state))
FROM bronze.customers
WHERE customer_id <> ''
  AND customer_zip_code_prefix <> ''
  AND customer_state <> '';

-- ---------------------------------------------------------------------------
-- Sellers
-- ---------------------------------------------------------------------------
INSERT INTO silver.rejected_rows (source_table, source_key, reason, raw_record)
SELECT 'bronze.sellers', seller_id,
       'missing seller_id, zip, or state', to_jsonb(s)
FROM bronze.sellers s
WHERE seller_id = ''
   OR seller_zip_code_prefix = ''
   OR seller_state = '';

INSERT INTO silver.sellers (
    seller_id,
    seller_zip_code_prefix,
    seller_city,
    seller_state
)
SELECT seller_id,
       LPAD(REGEXP_REPLACE(seller_zip_code_prefix, '\D', '', 'g'), 5, '0'),
       LOWER(TRIM(seller_city)),
       UPPER(TRIM(seller_state))
FROM bronze.sellers
WHERE seller_id <> ''
  AND seller_zip_code_prefix <> ''
  AND seller_state <> '';

-- ---------------------------------------------------------------------------
-- Products (missing category is flagged, not deleted)
-- ---------------------------------------------------------------------------
INSERT INTO silver.rejected_rows (source_table, source_key, reason, raw_record)
SELECT 'bronze.products', product_id, 'missing product_id', to_jsonb(p)
FROM bronze.products p
WHERE product_id = '';

INSERT INTO silver.products (
    product_id,
    product_category_name,
    category_missing,
    product_name_length,
    product_description_length,
    product_photos_qty,
    product_weight_g,
    product_length_cm,
    product_height_cm,
    product_width_cm
)
SELECT p.product_id,
       CASE
           WHEN p.product_category_name IS NULL
                OR TRIM(p.product_category_name) = ''
                OR t.product_category_name IS NULL THEN 'unknown'
           ELSE TRIM(p.product_category_name)
       END AS product_category_name,
       (p.product_category_name IS NULL
        OR TRIM(p.product_category_name) = ''
        OR t.product_category_name IS NULL) AS category_missing,
       NULLIF(p.product_name_lenght, '')::smallint,
       NULLIF(p.product_description_lenght, '')::integer,
       NULLIF(p.product_photos_qty, '')::smallint,
       NULLIF(p.product_weight_g, '')::integer,
       NULLIF(p.product_length_cm, '')::smallint,
       NULLIF(p.product_height_cm, '')::smallint,
       NULLIF(p.product_width_cm, '')::smallint
FROM bronze.products p
LEFT JOIN silver.category_translation t
       ON TRIM(p.product_category_name) = t.product_category_name
WHERE p.product_id <> '';

-- ---------------------------------------------------------------------------
-- Geolocation: keep every valid point; flag out-of-Brazil points
-- ---------------------------------------------------------------------------
INSERT INTO silver.rejected_rows (source_table, source_key, reason, raw_record)
SELECT 'bronze.geolocation', geolocation_zip_code_prefix,
       'invalid or missing latitude/longitude', to_jsonb(g)
FROM bronze.geolocation g
WHERE geolocation_lat !~ '^-?[0-9]+([.][0-9]+)?$'
   OR geolocation_lng !~ '^-?[0-9]+([.][0-9]+)?$';

INSERT INTO silver.geolocation (
    zip_code_prefix,
    lat,
    lng,
    city,
    state,
    is_outlier
)
SELECT DISTINCT
       LPAD(REGEXP_REPLACE(geolocation_zip_code_prefix, '\D', '', 'g'), 5, '0'),
       geolocation_lat::numeric(10,7),
       geolocation_lng::numeric(10,7),
       LOWER(TRIM(geolocation_city)),
       UPPER(TRIM(geolocation_state)),
       (geolocation_lat::numeric NOT BETWEEN -34 AND 6
        OR geolocation_lng::numeric NOT BETWEEN -74 AND -34) AS is_outlier
FROM bronze.geolocation
WHERE geolocation_lat ~ '^-?[0-9]+([.][0-9]+)?$'
  AND geolocation_lng ~ '^-?[0-9]+([.][0-9]+)?$';

-- ---------------------------------------------------------------------------
-- Orders (invalid/missing required rows are rejected; anomalies are flagged)
-- ---------------------------------------------------------------------------
INSERT INTO silver.rejected_rows (source_table, source_key, reason, raw_record)
SELECT 'bronze.orders', order_id,
       'missing required field, invalid status, or invalid timestamp',
       to_jsonb(o)
FROM bronze.orders o
WHERE order_id = ''
   OR customer_id = ''
   OR order_purchase_timestamp = ''
   OR order_estimated_delivery_date = ''
   OR LOWER(TRIM(order_status)) NOT IN
        ('delivered','shipped','canceled','unavailable',
         'invoiced','processing','created','approved')
   OR order_purchase_timestamp !~ '^[0-9]{4}-[0-9]{2}-[0-9]{2} [0-9]{2}:[0-9]{2}:[0-9]{2}$'
   OR order_estimated_delivery_date !~ '^[0-9]{4}-[0-9]{2}-[0-9]{2} [0-9]{2}:[0-9]{2}:[0-9]{2}$'
   OR (order_approved_at <> ''
       AND order_approved_at !~ '^[0-9]{4}-[0-9]{2}-[0-9]{2} [0-9]{2}:[0-9]{2}:[0-9]{2}$')
   OR (order_delivered_carrier_date <> ''
       AND order_delivered_carrier_date !~ '^[0-9]{4}-[0-9]{2}-[0-9]{2} [0-9]{2}:[0-9]{2}:[0-9]{2}$')
   OR (order_delivered_customer_date <> ''
       AND order_delivered_customer_date !~ '^[0-9]{4}-[0-9]{2}-[0-9]{2} [0-9]{2}:[0-9]{2}:[0-9]{2}$');

WITH src AS (
    SELECT order_id,
           customer_id,
           LOWER(TRIM(order_status)) AS order_status,
           order_purchase_timestamp::timestamp AS order_purchase_timestamp,
           NULLIF(order_approved_at, '')::timestamp AS order_approved_at,
           NULLIF(order_delivered_carrier_date, '')::timestamp
               AS order_delivered_carrier_date,
           NULLIF(order_delivered_customer_date, '')::timestamp
               AS order_delivered_customer_date,
           order_estimated_delivery_date::timestamp
               AS order_estimated_delivery_date
    FROM bronze.orders
    WHERE order_id <> ''
      AND customer_id <> ''
      AND order_purchase_timestamp <> ''
      AND order_estimated_delivery_date <> ''
      AND LOWER(TRIM(order_status)) IN
          ('delivered','shipped','canceled','unavailable',
           'invoiced','processing','created','approved')
      AND order_purchase_timestamp ~ '^[0-9]{4}-[0-9]{2}-[0-9]{2} [0-9]{2}:[0-9]{2}:[0-9]{2}$'
      AND order_estimated_delivery_date ~ '^[0-9]{4}-[0-9]{2}-[0-9]{2} [0-9]{2}:[0-9]{2}:[0-9]{2}$'
      AND (order_approved_at = ''
           OR order_approved_at ~ '^[0-9]{4}-[0-9]{2}-[0-9]{2} [0-9]{2}:[0-9]{2}:[0-9]{2}$')
      AND (order_delivered_carrier_date = ''
           OR order_delivered_carrier_date ~ '^[0-9]{4}-[0-9]{2}-[0-9]{2} [0-9]{2}:[0-9]{2}:[0-9]{2}$')
      AND (order_delivered_customer_date = ''
           OR order_delivered_customer_date ~ '^[0-9]{4}-[0-9]{2}-[0-9]{2} [0-9]{2}:[0-9]{2}:[0-9]{2}$')
)
INSERT INTO silver.orders (
    order_id,
    customer_id,
    order_status,
    order_purchase_timestamp,
    order_approved_at,
    order_delivered_carrier_date,
    order_delivered_customer_date,
    order_estimated_delivery_date,
    has_approved,
    has_carrier_date,
    has_delivery_date,
    delivery_anomaly
)
SELECT order_id,
       customer_id,
       order_status,
       order_purchase_timestamp,
       order_approved_at,
       order_delivered_carrier_date,
       order_delivered_customer_date,
       order_estimated_delivery_date,
       (order_approved_at IS NOT NULL),
       (order_delivered_carrier_date IS NOT NULL),
       (order_delivered_customer_date IS NOT NULL),
       (
           (order_delivered_carrier_date IS NOT NULL
            AND order_approved_at IS NOT NULL
            AND order_delivered_carrier_date < order_approved_at)
           OR
           (order_delivered_customer_date IS NOT NULL
            AND order_delivered_carrier_date IS NOT NULL
            AND order_delivered_customer_date < order_delivered_carrier_date)
       ) AS delivery_anomaly
FROM src;

-- ---------------------------------------------------------------------------
-- Order items
-- ---------------------------------------------------------------------------
INSERT INTO silver.rejected_rows (source_table, source_key, reason, raw_record)
SELECT 'bronze.order_items', order_id,
       'missing required field or invalid numeric/timestamp', to_jsonb(i)
FROM bronze.order_items i
WHERE order_id = ''
   OR product_id = ''
   OR seller_id = ''
   OR shipping_limit_date = ''
   OR order_item_id !~ '^[0-9]+$'
   OR price !~ '^[0-9]+([.][0-9]+)?$'
   OR freight_value !~ '^[0-9]+([.][0-9]+)?$'
   OR shipping_limit_date !~ '^[0-9]{4}-[0-9]{2}-[0-9]{2} [0-9]{2}:[0-9]{2}:[0-9]{2}$';

WITH src AS (
    SELECT order_id,
           order_item_id::smallint AS order_item_id,
           product_id,
           seller_id,
           shipping_limit_date::timestamp AS shipping_limit_date,
           price::numeric(10,2) AS price,
           freight_value::numeric(10,2) AS freight_value
    FROM bronze.order_items
    WHERE order_id <> ''
      AND product_id <> ''
      AND seller_id <> ''
      AND shipping_limit_date <> ''
      AND order_item_id ~ '^[0-9]+$'
      AND price ~ '^[0-9]+([.][0-9]+)?$'
      AND freight_value ~ '^[0-9]+([.][0-9]+)?$'
      AND shipping_limit_date ~ '^[0-9]{4}-[0-9]{2}-[0-9]{2} [0-9]{2}:[0-9]{2}:[0-9]{2}$'
)
INSERT INTO silver.order_items (
    order_id,
    order_item_id,
    product_id,
    seller_id,
    shipping_limit_date,
    price,
    freight_value,
    is_zero_freight
)
SELECT order_id,
       order_item_id,
       product_id,
       seller_id,
       shipping_limit_date,
       price,
       freight_value,
       (freight_value = 0) AS is_zero_freight
FROM src;

-- ---------------------------------------------------------------------------
-- Payments
-- ---------------------------------------------------------------------------
INSERT INTO silver.rejected_rows (source_table, source_key, reason, raw_record)
SELECT 'bronze.order_payments', order_id,
       'missing required field, invalid payment type, or invalid numeric', to_jsonb(p)
FROM bronze.order_payments p
WHERE order_id = ''
   OR payment_sequential !~ '^[0-9]+$'
   OR LOWER(TRIM(payment_type)) NOT IN
        ('credit_card','boleto','voucher','debit_card','not_defined')
   OR payment_installments !~ '^[0-9]+$'
   OR payment_value !~ '^[0-9]+([.][0-9]+)?$';

WITH src AS (
    SELECT order_id,
           payment_sequential::smallint AS payment_sequential,
           LOWER(TRIM(payment_type)) AS payment_type,
           payment_installments::smallint AS payment_installments,
           payment_value::numeric(12,2) AS payment_value
    FROM bronze.order_payments
    WHERE order_id <> ''
      AND payment_sequential ~ '^[0-9]+$'
      AND LOWER(TRIM(payment_type)) IN
          ('credit_card','boleto','voucher','debit_card','not_defined')
      AND payment_installments ~ '^[0-9]+$'
      AND payment_value ~ '^[0-9]+([.][0-9]+)?$'
)
INSERT INTO silver.order_payments (
    order_id,
    payment_sequential,
    payment_type,
    payment_installments,
    payment_value,
    is_zero_value,
    is_zero_installments,
    is_not_defined
)
SELECT order_id,
       payment_sequential,
       payment_type,
       payment_installments,
       payment_value,
       (payment_value = 0) AS is_zero_value,
       (payment_installments = 0) AS is_zero_installments,
       (payment_type = 'not_defined') AS is_not_defined
FROM src;

-- ---------------------------------------------------------------------------
-- Reviews (review_id is not unique; composite key is review_id + order_id)
-- ---------------------------------------------------------------------------
INSERT INTO silver.rejected_rows (source_table, source_key, reason, raw_record)
SELECT 'bronze.order_reviews', review_id,
       'missing required field, invalid score, or invalid timestamp', to_jsonb(r)
FROM bronze.order_reviews r
WHERE review_id = ''
   OR order_id = ''
   OR review_score !~ '^[1-5]$'
   OR review_creation_date = ''
   OR review_answer_timestamp = ''
   OR review_creation_date !~ '^[0-9]{4}-[0-9]{2}-[0-9]{2} [0-9]{2}:[0-9]{2}:[0-9]{2}$'
   OR review_answer_timestamp !~ '^[0-9]{4}-[0-9]{2}-[0-9]{2} [0-9]{2}:[0-9]{2}:[0-9]{2}$';

WITH src AS (
    SELECT review_id,
           order_id,
           review_score::smallint AS review_score,
           NULLIF(TRIM(review_comment_title), '') AS review_comment_title,
           NULLIF(TRIM(review_comment_message), '') AS review_comment_message,
           review_creation_date::timestamp AS review_creation_date,
           review_answer_timestamp::timestamp AS review_answer_timestamp
    FROM bronze.order_reviews
    WHERE review_id <> ''
      AND order_id <> ''
      AND review_score ~ '^[1-5]$'
      AND review_creation_date <> ''
      AND review_answer_timestamp <> ''
      AND review_creation_date ~ '^[0-9]{4}-[0-9]{2}-[0-9]{2} [0-9]{2}:[0-9]{2}:[0-9]{2}$'
      AND review_answer_timestamp ~ '^[0-9]{4}-[0-9]{2}-[0-9]{2} [0-9]{2}:[0-9]{2}:[0-9]{2}$'
)
INSERT INTO silver.order_reviews (
    review_id,
    order_id,
    review_score,
    review_comment_title,
    review_comment_message,
    review_creation_date,
    review_answer_timestamp,
    has_title,
    has_message,
    is_before_purchase
)
SELECT s.review_id,
       s.order_id,
       s.review_score,
       s.review_comment_title,
       s.review_comment_message,
       s.review_creation_date,
       s.review_answer_timestamp,
       (s.review_comment_title IS NOT NULL),
       (s.review_comment_message IS NOT NULL),
       COALESCE(s.review_creation_date < o.order_purchase_timestamp, false)
FROM src s
LEFT JOIN silver.orders o ON s.order_id = o.order_id;

COMMIT;

ANALYZE silver.customers;
ANALYZE silver.sellers;
ANALYZE silver.products;
ANALYZE silver.geolocation;
ANALYZE silver.orders;
ANALYZE silver.order_items;
ANALYZE silver.order_payments;
ANALYZE silver.order_reviews;
ANALYZE silver.category_translation;
ANALYZE silver.rejected_rows;
