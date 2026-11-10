-- Bronze layer: raw text, exactly as received, plus load metadata.
-- Every source column is TEXT so that leading zeros and malformed values survive.
-- Load idempotency is enforced by bronze.load_batches.file_sha256.

CREATE TABLE IF NOT EXISTS bronze.load_batches (
    load_id        bigserial PRIMARY KEY,
    source_file    text        NOT NULL,
    file_sha256    char(64)    NOT NULL UNIQUE,
    row_count      bigint      NOT NULL DEFAULT 0,
    status         text        NOT NULL DEFAULT 'started'
        CHECK (status IN ('started', 'success', 'failed')),
    started_at     timestamptz NOT NULL DEFAULT now(),
    finished_at    timestamptz,
    error_message  text
);

CREATE TABLE IF NOT EXISTS bronze.rejected_rows (
    rejected_id        bigserial PRIMARY KEY,
    load_id            bigint REFERENCES bronze.load_batches(load_id),
    source_file        text NOT NULL,
    source_row_number  bigint NOT NULL,
    raw_line           text,
    reason             text NOT NULL,
    rejected_at        timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_bronze_rejected_file
    ON bronze.rejected_rows(source_file, source_row_number);

-- Each data table carries:
--   _load_id            batch that produced the row
--   _source_file        source CSV name
--   _source_row_number  1-based data row number in the CSV (header excluded)
--   _loaded_at          ingestion timestamp
-- The unique constraint prevents duplicate rows within a batch.

CREATE TABLE IF NOT EXISTS bronze.customers (
    customer_id               text,
    customer_unique_id        text,
    customer_zip_code_prefix  text,
    customer_city             text,
    customer_state            text,
    _load_id                  bigint NOT NULL REFERENCES bronze.load_batches(load_id),
    _source_file              text   NOT NULL,
    _source_row_number        bigint NOT NULL,
    _loaded_at                timestamptz NOT NULL DEFAULT now(),
    UNIQUE (_load_id, _source_row_number)
);

CREATE TABLE IF NOT EXISTS bronze.geolocation (
    geolocation_zip_code_prefix  text,
    geolocation_lat              text,
    geolocation_lng              text,
    geolocation_city             text,
    geolocation_state            text,
    _load_id                     bigint NOT NULL REFERENCES bronze.load_batches(load_id),
    _source_file                 text   NOT NULL,
    _source_row_number           bigint NOT NULL,
    _loaded_at                   timestamptz NOT NULL DEFAULT now(),
    UNIQUE (_load_id, _source_row_number)
);

CREATE TABLE IF NOT EXISTS bronze.order_items (
    order_id             text,
    order_item_id        text,
    product_id           text,
    seller_id            text,
    shipping_limit_date  text,
    price                text,
    freight_value        text,
    _load_id             bigint NOT NULL REFERENCES bronze.load_batches(load_id),
    _source_file         text   NOT NULL,
    _source_row_number   bigint NOT NULL,
    _loaded_at           timestamptz NOT NULL DEFAULT now(),
    UNIQUE (_load_id, _source_row_number)
);

CREATE TABLE IF NOT EXISTS bronze.order_payments (
    order_id              text,
    payment_sequential    text,
    payment_type          text,
    payment_installments  text,
    payment_value         text,
    _load_id              bigint NOT NULL REFERENCES bronze.load_batches(load_id),
    _source_file          text   NOT NULL,
    _source_row_number    bigint NOT NULL,
    _loaded_at            timestamptz NOT NULL DEFAULT now(),
    UNIQUE (_load_id, _source_row_number)
);

CREATE TABLE IF NOT EXISTS bronze.order_reviews (
    review_id               text,
    order_id                text,
    review_score            text,
    review_comment_title    text,
    review_comment_message  text,
    review_creation_date    text,
    review_answer_timestamp text,
    _load_id                bigint NOT NULL REFERENCES bronze.load_batches(load_id),
    _source_file            text   NOT NULL,
    _source_row_number      bigint NOT NULL,
    _loaded_at              timestamptz NOT NULL DEFAULT now(),
    UNIQUE (_load_id, _source_row_number)
);

CREATE TABLE IF NOT EXISTS bronze.orders (
    order_id                        text,
    customer_id                     text,
    order_status                    text,
    order_purchase_timestamp        text,
    order_approved_at               text,
    order_delivered_carrier_date    text,
    order_delivered_customer_date   text,
    order_estimated_delivery_date   text,
    _load_id                        bigint NOT NULL REFERENCES bronze.load_batches(load_id),
    _source_file                    text   NOT NULL,
    _source_row_number              bigint NOT NULL,
    _loaded_at                      timestamptz NOT NULL DEFAULT now(),
    UNIQUE (_load_id, _source_row_number)
);

CREATE TABLE IF NOT EXISTS bronze.products (
    product_id                  text,
    product_category_name       text,
    product_name_lenght         text,
    product_description_lenght  text,
    product_photos_qty          text,
    product_weight_g            text,
    product_length_cm           text,
    product_height_cm           text,
    product_width_cm            text,
    _load_id                    bigint NOT NULL REFERENCES bronze.load_batches(load_id),
    _source_file                text   NOT NULL,
    _source_row_number          bigint NOT NULL,
    _loaded_at                  timestamptz NOT NULL DEFAULT now(),
    UNIQUE (_load_id, _source_row_number)
);

CREATE TABLE IF NOT EXISTS bronze.sellers (
    seller_id               text,
    seller_zip_code_prefix  text,
    seller_city             text,
    seller_state            text,
    _load_id                bigint NOT NULL REFERENCES bronze.load_batches(load_id),
    _source_file            text   NOT NULL,
    _source_row_number      bigint NOT NULL,
    _loaded_at              timestamptz NOT NULL DEFAULT now(),
    UNIQUE (_load_id, _source_row_number)
);

CREATE TABLE IF NOT EXISTS bronze.category_translation (
    product_category_name          text,
    product_category_name_english  text,
    _load_id                       bigint NOT NULL REFERENCES bronze.load_batches(load_id),
    _source_file                   text   NOT NULL,
    _source_row_number             bigint NOT NULL,
    _loaded_at                     timestamptz NOT NULL DEFAULT now(),
    UNIQUE (_load_id, _source_row_number)
);

CREATE INDEX IF NOT EXISTS idx_bronze_customers_load ON bronze.customers(_load_id);
CREATE INDEX IF NOT EXISTS idx_bronze_geolocation_load ON bronze.geolocation(_load_id);
CREATE INDEX IF NOT EXISTS idx_bronze_order_items_load ON bronze.order_items(_load_id);
CREATE INDEX IF NOT EXISTS idx_bronze_order_payments_load ON bronze.order_payments(_load_id);
CREATE INDEX IF NOT EXISTS idx_bronze_order_reviews_load ON bronze.order_reviews(_load_id);
CREATE INDEX IF NOT EXISTS idx_bronze_orders_load ON bronze.orders(_load_id);
CREATE INDEX IF NOT EXISTS idx_bronze_products_load ON bronze.products(_load_id);
CREATE INDEX IF NOT EXISTS idx_bronze_sellers_load ON bronze.sellers(_load_id);
CREATE INDEX IF NOT EXISTS idx_bronze_category_translation_load ON bronze.category_translation(_load_id);
