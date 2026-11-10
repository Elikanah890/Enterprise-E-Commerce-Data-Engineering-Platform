-- Gold dimensions.
-- Run after silver is populated.
-- These are derived tables; rebuilding them does not touch bronze or silver.

DROP TABLE IF EXISTS gold.dim_date CASCADE;
DROP TABLE IF EXISTS gold.dim_geolocation CASCADE;
DROP TABLE IF EXISTS gold.dim_sellers CASCADE;
DROP TABLE IF EXISTS gold.dim_products CASCADE;
DROP TABLE IF EXISTS gold.dim_customers CASCADE;
DROP TABLE IF EXISTS gold.dim_category CASCADE;

-- ---------------------------------------------------------------------------
-- Date dimension
-- ---------------------------------------------------------------------------
CREATE TABLE gold.dim_date AS
SELECT TO_CHAR(d, 'YYYYMMDD')::integer       AS date_key,
       d::date                               AS date_day,
       EXTRACT(YEAR FROM d)::integer         AS year,
       EXTRACT(QUARTER FROM d)::integer      AS quarter,
       EXTRACT(MONTH FROM d)::integer        AS month,
       TRIM(TO_CHAR(d, 'Month'))             AS month_name,
       EXTRACT(DAY FROM d)::integer          AS day_of_month,
       EXTRACT(ISODOW FROM d)::integer       AS day_of_week,
       TRIM(TO_CHAR(d, 'Day'))               AS day_name,
       (EXTRACT(ISODOW FROM d) IN (6, 7))    AS is_weekend
FROM generate_series('2016-01-01'::date, '2019-12-31'::date, '1 day') AS d;

ALTER TABLE gold.dim_date ADD PRIMARY KEY (date_key);
CREATE INDEX idx_dim_date_day ON gold.dim_date(date_day);

-- ---------------------------------------------------------------------------
-- Category dimension (snowflake lookup for products)
-- ---------------------------------------------------------------------------
CREATE TABLE gold.dim_category AS
SELECT ROW_NUMBER() OVER (ORDER BY product_category_name)::integer AS category_key,
       product_category_name,
       product_category_name_english
FROM silver.category_translation;

ALTER TABLE gold.dim_category ADD PRIMARY KEY (category_key);
ALTER TABLE gold.dim_category ADD CONSTRAINT uq_dim_category_name
    UNIQUE (product_category_name);

-- ---------------------------------------------------------------------------
-- Geolocation dimension: one row per zip prefix
-- Median coordinates exclude flagged outliers; if a zip has only outliers,
-- the median falls back to all points.
-- ---------------------------------------------------------------------------
CREATE TABLE gold.dim_geolocation AS
WITH points AS (
    SELECT zip_code_prefix, lat, lng, city, state, is_outlier
    FROM silver.geolocation
)
SELECT zip_code_prefix,
       COALESCE(
           percentile_cont(0.5) WITHIN GROUP (ORDER BY lat)
               FILTER (WHERE NOT is_outlier),
           percentile_cont(0.5) WITHIN GROUP (ORDER BY lat)
       ) AS lat,
       COALESCE(
           percentile_cont(0.5) WITHIN GROUP (ORDER BY lng)
               FILTER (WHERE NOT is_outlier),
           percentile_cont(0.5) WITHIN GROUP (ORDER BY lng)
       ) AS lng,
       mode() WITHIN GROUP (ORDER BY city)  AS city,
       mode() WITHIN GROUP (ORDER BY state) AS state,
       COUNT(*)                             AS point_count,
       COUNT(*) FILTER (WHERE is_outlier)   AS outlier_count
FROM points
GROUP BY zip_code_prefix;

ALTER TABLE gold.dim_geolocation ADD PRIMARY KEY (zip_code_prefix);

-- ---------------------------------------------------------------------------
-- Customer dimension (with optional geographic enrichment)
-- ---------------------------------------------------------------------------
CREATE TABLE gold.dim_customers AS
SELECT c.customer_id,
       c.customer_unique_id,
       c.customer_zip_code_prefix,
       c.customer_city,
       c.customer_state,
       (g.zip_code_prefix IS NOT NULL) AS has_geo,
       g.lat                           AS geo_lat,
       g.lng                           AS geo_lng
FROM silver.customers c
LEFT JOIN gold.dim_geolocation g
       ON c.customer_zip_code_prefix = g.zip_code_prefix;

ALTER TABLE gold.dim_customers ADD PRIMARY KEY (customer_id);
CREATE INDEX idx_dim_customers_unique ON gold.dim_customers(customer_unique_id);
CREATE INDEX idx_dim_customers_state ON gold.dim_customers(customer_state);

-- ---------------------------------------------------------------------------
-- Seller dimension (with optional geographic enrichment)
-- ---------------------------------------------------------------------------
CREATE TABLE gold.dim_sellers AS
SELECT s.seller_id,
       s.seller_zip_code_prefix,
       s.seller_city,
       s.seller_state,
       (g.zip_code_prefix IS NOT NULL) AS has_geo,
       g.lat                           AS geo_lat,
       g.lng                           AS geo_lng
FROM silver.sellers s
LEFT JOIN gold.dim_geolocation g
       ON s.seller_zip_code_prefix = g.zip_code_prefix;

ALTER TABLE gold.dim_sellers ADD PRIMARY KEY (seller_id);
CREATE INDEX idx_dim_sellers_state ON gold.dim_sellers(seller_state);

-- ---------------------------------------------------------------------------
-- Product dimension (with category key, English label, and volume)
-- ---------------------------------------------------------------------------
CREATE TABLE gold.dim_products AS
SELECT p.product_id,
       dc.category_key,
       p.product_category_name,
       COALESCE(dc.product_category_name_english, 'unknown')
           AS product_category_name_english,
       p.category_missing,
       p.product_name_length,
       p.product_description_length,
       p.product_photos_qty,
       p.product_weight_g,
       p.product_length_cm,
       p.product_height_cm,
       p.product_width_cm,
       (p.product_length_cm::integer
        * p.product_height_cm::integer
        * p.product_width_cm::integer) AS product_volume_cm3,
       ROUND(
           p.product_weight_g::numeric
           / NULLIF(
               p.product_length_cm::integer
               * p.product_height_cm::integer
               * p.product_width_cm::integer,
               0
           ),
           4
       ) AS density_g_cm3
FROM silver.products p
LEFT JOIN gold.dim_category dc
       ON p.product_category_name = dc.product_category_name;

ALTER TABLE gold.dim_products ADD PRIMARY KEY (product_id);
CREATE INDEX idx_dim_products_category ON gold.dim_products(category_key);
