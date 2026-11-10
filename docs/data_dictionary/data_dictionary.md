# Data Dictionary

Column types reflect the **silver/gold** warehouse. The raw CSVs are all text.
`geo_id`, `review_sk`, and `customer_sk` are warehouse-added keys.

## customers

| Column | Type | Nullable | Key | Description | Profiling note |
|---|---|---|---|---|---|
| `customer_id` | char(32) | no | PK | Order-scoped customer key | 99,441 unique |
| `customer_unique_id` | char(32) | no | natural key | Person-level customer key | 96,096 unique; 3,345 duplicates |
| `customer_zip_code_prefix` | char(5) | no | quasi-ID | 5-digit zip prefix | 23,995 values start with `0` |
| `customer_city` | text | no | dimension | City, lowercased | 4,119 unique; ASCII in source |
| `customer_state` | char(2) | no | dimension | Brazilian UF | 27 states |

## geolocation

| Column | Type | Nullable | Key | Description | Profiling note |
|---|---|---|---|---|---|
| `geo_id` | bigserial | no | PK | Surrogate key added at load | raw file has no key |
| `zip_code_prefix` | char(5) | no | index | Zip prefix | 19,015 unique in raw |
| `lat` | numeric(10,7) | no | measure | Latitude | 42 raw points outside Brazil |
| `lng` | numeric(10,7) | no | measure | Longitude | 42 raw points outside Brazil |
| `city` | text | no | dimension | City | 8,011 raw unique cities |
| `state` | char(2) | no | dimension | UF | 8 zips map to >1 state |

## orders

| Column | Type | Nullable | Key | Description | Profiling note |
|---|---|---|---|---|---|
| `order_id` | char(32) | no | PK | Order identifier | 99,441 unique |
| `customer_id` | char(32) | no | FK → customers | Order customer | 1:1 in snapshot |
| `order_status` | text | no | category | Order lifecycle status | 8 values; 97.02% delivered |
| `order_purchase_timestamp` | timestamp | no | timestamp | Purchase time | 2016-09-04 to 2018-10-17 |
| `order_approved_at` | timestamp | yes | timestamp | Payment approval | 160 nulls (0.16%) |
| `order_delivered_carrier_date` | timestamp | yes | timestamp | Carrier handoff | 1,783 nulls (1.79%) |
| `order_delivered_customer_date` | timestamp | yes | timestamp | Customer delivery | 2,965 nulls (2.98%) |
| `order_estimated_delivery_date` | timestamp | no | timestamp | Estimated delivery | 459 distinct dates |

## order_items

| Column | Type | Nullable | Key | Description | Profiling note |
|---|---|---|---|---|---|
| `order_id` | char(32) | no | PK / FK → orders | Order | 98,666 distinct orders |
| `order_item_id` | smallint | no | PK | Line number in order | 1–21 |
| `product_id` | char(32) | no | FK → products | Product | 32,951 distinct |
| `seller_id` | char(32) | no | FK → sellers | Seller | 3,095 distinct |
| `shipping_limit_date` | timestamp | no | timestamp | Seller shipping deadline | 4 rows in 2020 |
| `price` | numeric(10,2) | no | measure | Item price, BRL | 0.85–6,735.00; mean 120.65 |
| `freight_value` | numeric(10,2) | no | measure | Freight, BRL | 0–409.68; 383 zeros |

## order_payments

| Column | Type | Nullable | Key | Description | Profiling note |
|---|---|---|---|---|---|
| `order_id` | char(32) | no | PK / FK → orders | Order | 99,440 distinct orders |
| `payment_sequential` | smallint | no | PK | Payment sequence | 1–29 |
| `payment_type` | text | no | category | Payment method | 5 values |
| `payment_installments` | smallint | no | ordinal measure | Installment count | 0–24; 2 zeros |
| `payment_value` | numeric(12,2) | no | measure | Amount paid, BRL | 0–13,664.08; 9 zeros |

## order_reviews

| Column | Type | Nullable | Key | Description | Profiling note |
|---|---|---|---|---|---|
| `review_sk` | bigserial | no | PK | Surrogate key added at load | raw file has no PK |
| `review_id` | char(32) | no | non-unique ID | Review identifier | 814 duplicate rows |
| `order_id` | char(32) | no | FK → orders | Order | 98,673 distinct orders |
| `review_score` | smallint | no | ordinal measure | 1–5 stars | mean 4.0864 |
| `review_comment_title` | text | yes | free text | Optional title | 88.34% null |
| `review_comment_message` | text | yes | free text | Optional message | 58.70% null |
| `review_creation_date` | timestamp | no | timestamp | Review date | 2016-10-02 to 2018-08-31 |
| `review_answer_timestamp` | timestamp | no | timestamp | Answer time | to 2018-10-29 |

## products

| Column | Type | Nullable | Key | Description | Profiling note |
|---|---|---|---|---|---|
| `product_id` | char(32) | no | PK | Product identifier | 32,951 unique |
| `product_category_name` | text | no | FK → category_translation | Portuguese category | 610 raw nulls → `unknown` |
| `product_name_length` | smallint | yes | measure | Name length | raw column `lenght` |
| `product_description_length` | integer | yes | measure | Description length | raw column `lenght` |
| `product_photos_qty` | smallint | yes | measure | Photo count | 1–20 |
| `product_weight_g` | integer | yes | measure | Weight, grams | 0–40,425; 4 zeros |
| `product_length_cm` | smallint | yes | measure | Length, cm | 7–105 |
| `product_height_cm` | smallint | yes | measure | Height, cm | 2–105 |
| `product_width_cm` | smallint | yes | measure | Width, cm | 6–118 |

## sellers

| Column | Type | Nullable | Key | Description | Profiling note |
|---|---|---|---|---|---|
| `seller_id` | char(32) | no | PK | Seller identifier | 3,095 unique |
| `seller_zip_code_prefix` | char(5) | no | quasi-ID | 5-digit zip prefix | 1,027 leading zeros |
| `seller_city` | text | no | dimension | City | 611 unique |
| `seller_state` | char(2) | no | dimension | UF | 23 states |

## category_translation

| Column | Type | Nullable | Key | Description | Profiling note |
|---|---|---|---|---|---|
| `product_category_name` | text | no | PK | Portuguese category | 71 raw + 3 added |
| `product_category_name_english` | text | no | dimension | English label | 71 unique in raw |

## Derived gold columns

| Table | Column | Type | Description |
|---|---|---|---|
| `dim_products` | `product_volume_cm3` | integer | `length × height × width` |
| `dim_products` | `density_g_cm3` | numeric | weight / volume |
| `dim_geolocation` | `point_count` | bigint | number of raw points for the zip |
| `fact_orders` | `order_date` | date | purchase date |
| `fact_orders` | `order_date_key` | integer | `YYYYMMDD` |
| `fact_orders` | `delivery_days` | integer | delivered date − purchase date |
| `fact_orders` | `is_late` | boolean | delivered after estimate |
| `fact_orders` | `days_vs_estimate` | integer | delivered − estimate |
| `fact_orders` | `gross_order_value` | numeric | item revenue + freight |
| `fact_orders` | `avg_review_score` | numeric | mean review score per order |
| `fact_order_items` | `total_value` | numeric | price + freight |
| `fact_order_items` | `shipped_after_limit` | boolean | delivery after shipping limit |
| `vw_customer_rfm` | `segment` | text | Champions / Loyal / At Risk / Lost / Others |

## Gold objects added in Stage 2

| Table | Column | Type | Description |
|---|---|---|---|
| `dim_category` | `category_key` | integer | Surrogate category key |
| `dim_category` | `product_category_name` | text | Portuguese category name |
| `dim_category` | `product_category_name_english` | text | English category label |
| `dim_customers` | `has_geo` | boolean | Zip found in `dim_geolocation` |
| `dim_customers` | `geo_lat` / `geo_lng` | numeric | Zip centroid coordinates |
| `dim_sellers` | `has_geo` | boolean | Zip found in `dim_geolocation` |
| `dim_sellers` | `geo_lat` / `geo_lng` | numeric | Zip centroid coordinates |
| `dim_products` | `category_key` | integer | FK to `dim_category` |
| `dim_products` | `category_missing` | boolean | Category was missing in source |
| `dim_geolocation` | `outlier_count` | bigint | Flagged points for the zip |
| `fact_orders` | `has_items` | boolean | Order has at least one item |
| `fact_orders` | `has_payment` | boolean | Order has at least one payment row |
| `fact_orders` | `has_review` | boolean | Order has at least one review |
| `fact_orders` | `payment_mismatch` | boolean | Payment total differs from item + freight by > R$0.01 |
| `fact_orders` | `payment_mismatch_amount` | numeric | payment total − (item revenue + freight) |
| `fact_order_items` | `is_zero_freight` | boolean | Freight value is exactly zero |
| `fact_payments` | `is_zero_value` | boolean | Payment value is exactly zero |
| `fact_payments` | `is_zero_installments` | boolean | Installments equal zero |
| `fact_payments` | `is_not_defined` | boolean | Payment type is `not_defined` |
| `fact_reviews` | `review_sk` | bigint | Surrogate review key (PK) |
| `fact_reviews` | `answer_latency_hours` | numeric | Answer timestamp − creation date, in hours |
| `fact_reviews` | `review_latency_days` | integer | Review creation date − order purchase date |
| `fact_reviews` | `has_title` | boolean | Non-empty review title |
| `fact_reviews` | `has_message` | boolean | Non-empty review message |
| `fact_reviews` | `title_length` | integer | Title character length |
| `fact_reviews` | `message_length` | integer | Message character length |
| `fact_reviews` | `is_before_purchase` | boolean | Review created before order purchase |
