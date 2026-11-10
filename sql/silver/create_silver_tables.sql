-- Silver layer: typed, constrained, deduplicated tables.
-- Suspicious records are retained with flags; malformed records are logged in
-- silver.rejected_rows rather than silently dropped.

CREATE TABLE IF NOT EXISTS silver.rejected_rows (
    rejected_id   bigserial PRIMARY KEY,
    source_table  text NOT NULL,
    source_key    text,
    reason        text NOT NULL,
    raw_record    jsonb,
    rejected_at   timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS silver.category_translation (
    product_category_name          text PRIMARY KEY,
    product_category_name_english  text NOT NULL
);

CREATE TABLE IF NOT EXISTS silver.customers (
    customer_id               char(32) PRIMARY KEY,
    customer_unique_id        char(32) NOT NULL,
    customer_zip_code_prefix  char(5)  NOT NULL,
    customer_city             text      NOT NULL,
    customer_state            char(2)   NOT NULL
);

CREATE TABLE IF NOT EXISTS silver.sellers (
    seller_id               char(32) PRIMARY KEY,
    seller_zip_code_prefix  char(5)  NOT NULL,
    seller_city             text      NOT NULL,
    seller_state            char(2)   NOT NULL
);

CREATE TABLE IF NOT EXISTS silver.products (
    product_id                  char(32) PRIMARY KEY,
    product_category_name       text NOT NULL
        REFERENCES silver.category_translation(product_category_name),
    category_missing            boolean NOT NULL DEFAULT false,
    product_name_length         smallint,
    product_description_length  integer,
    product_photos_qty          smallint,
    product_weight_g            integer CHECK (product_weight_g >= 0),
    product_length_cm           smallint,
    product_height_cm           smallint,
    product_width_cm            smallint
);

CREATE TABLE IF NOT EXISTS silver.geolocation (
    geo_id           bigserial PRIMARY KEY,
    zip_code_prefix  char(5)       NOT NULL,
    lat              numeric(10,7) NOT NULL,
    lng              numeric(10,7) NOT NULL,
    city             text          NOT NULL,
    state            char(2)       NOT NULL,
    is_outlier       boolean       NOT NULL DEFAULT false,
    UNIQUE (zip_code_prefix, lat, lng, city, state)
);

CREATE TABLE IF NOT EXISTS silver.orders (
    order_id                        char(32) PRIMARY KEY,
    customer_id                     char(32) NOT NULL
        REFERENCES silver.customers(customer_id),
    order_status                    text NOT NULL
        CHECK (order_status IN
            ('delivered','shipped','canceled','unavailable',
             'invoiced','processing','created','approved')),
    order_purchase_timestamp        timestamp NOT NULL,
    order_approved_at               timestamp,
    order_delivered_carrier_date    timestamp,
    order_delivered_customer_date   timestamp,
    order_estimated_delivery_date   timestamp NOT NULL,
    has_approved                    boolean NOT NULL DEFAULT false,
    has_carrier_date                boolean NOT NULL DEFAULT false,
    has_delivery_date               boolean NOT NULL DEFAULT false,
    delivery_anomaly                boolean NOT NULL DEFAULT false
);

CREATE TABLE IF NOT EXISTS silver.order_items (
    order_id             char(32) NOT NULL
        REFERENCES silver.orders(order_id),
    order_item_id        smallint NOT NULL CHECK (order_item_id >= 1),
    product_id           char(32) NOT NULL
        REFERENCES silver.products(product_id),
    seller_id            char(32) NOT NULL
        REFERENCES silver.sellers(seller_id),
    shipping_limit_date  timestamp NOT NULL,
    price                numeric(10,2) NOT NULL CHECK (price >= 0),
    freight_value        numeric(10,2) NOT NULL CHECK (freight_value >= 0),
    is_zero_freight      boolean NOT NULL DEFAULT false,
    PRIMARY KEY (order_id, order_item_id)
);

CREATE TABLE IF NOT EXISTS silver.order_payments (
    order_id              char(32) NOT NULL
        REFERENCES silver.orders(order_id),
    payment_sequential    smallint NOT NULL CHECK (payment_sequential >= 1),
    payment_type          text NOT NULL
        CHECK (payment_type IN
            ('credit_card','boleto','voucher','debit_card','not_defined')),
    payment_installments  smallint NOT NULL CHECK (payment_installments >= 0),
    payment_value         numeric(12,2) NOT NULL CHECK (payment_value >= 0),
    is_zero_value         boolean NOT NULL DEFAULT false,
    is_zero_installments  boolean NOT NULL DEFAULT false,
    is_not_defined        boolean NOT NULL DEFAULT false,
    PRIMARY KEY (order_id, payment_sequential)
);

CREATE TABLE IF NOT EXISTS silver.order_reviews (
    review_sk               bigserial PRIMARY KEY,
    review_id               char(32) NOT NULL,
    order_id                char(32) NOT NULL
        REFERENCES silver.orders(order_id),
    review_score            smallint NOT NULL CHECK (review_score BETWEEN 1 AND 5),
    review_comment_title    text,
    review_comment_message  text,
    review_creation_date    timestamp NOT NULL,
    review_answer_timestamp timestamp NOT NULL,
    has_title               boolean NOT NULL DEFAULT false,
    has_message             boolean NOT NULL DEFAULT false,
    is_before_purchase      boolean NOT NULL DEFAULT false,
    UNIQUE (review_id, order_id)
);

CREATE INDEX IF NOT EXISTS idx_silver_customers_unique_id
    ON silver.customers(customer_unique_id);
CREATE INDEX IF NOT EXISTS idx_silver_customers_zip
    ON silver.customers(customer_zip_code_prefix);
CREATE INDEX IF NOT EXISTS idx_silver_sellers_zip
    ON silver.sellers(seller_zip_code_prefix);
CREATE INDEX IF NOT EXISTS idx_silver_products_category
    ON silver.products(product_category_name);
CREATE INDEX IF NOT EXISTS idx_silver_geo_zip
    ON silver.geolocation(zip_code_prefix);
CREATE INDEX IF NOT EXISTS idx_silver_orders_customer
    ON silver.orders(customer_id);
CREATE INDEX IF NOT EXISTS idx_silver_orders_purchase
    ON silver.orders(order_purchase_timestamp);
CREATE INDEX IF NOT EXISTS idx_silver_items_product
    ON silver.order_items(product_id);
CREATE INDEX IF NOT EXISTS idx_silver_items_seller
    ON silver.order_items(seller_id);
CREATE INDEX IF NOT EXISTS idx_silver_payments_order
    ON silver.order_payments(order_id);
CREATE INDEX IF NOT EXISTS idx_silver_reviews_order
    ON silver.order_reviews(order_id);
CREATE INDEX IF NOT EXISTS idx_silver_reviews_score
    ON silver.order_reviews(review_score);
