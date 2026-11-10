# Entity-Relationship Description

## Text ERD

```
                         +----------------------------+
                         | category_translation       |
                         | PK product_category_name   |
                         +-------------+--------------+
                                       | 1
                                       | *
                         +-------------+--------------+
                         | products                   |
                         | PK product_id              |
                         +-------------+--------------+
                                       | 1
                                       | *
+------------------+     +-------------+--------------+     +------------------+
| customers        |1   *| order_items                |*  1| sellers          |
| PK customer_id   +-----+ PK (order_id, order_item_id)|-----+ PK seller_id     |
| customer_unique_id     | FK order_id                |     | seller_zip       |
| customer_zip     |     | FK product_id              |     | seller_state     |
| customer_state   |     | FK seller_id               |     +--------+---------+
+--------+---------+     | price, freight             |              | *
         | 1             | shipping_limit_date        |              | 1
         |               +-------------+--------------+     +--------+---------+
         | *                           | *                  | geolocation      |
+--------+---------+     +-------------+--------------+     | no natural PK    |
| orders           |1   *| order_payments             |     | zip (soft link)  |
| PK order_id      +-----+ PK (order_id,              |     | lat, lng         |
| FK customer_id   |     |     payment_sequential)    |     | city, state      |
| order_status     |     +----------------------------+     +------------------+
| purchase/approve |
| carrier/deliver  |1
| estimated        |*
+--------+---------+     +----------------------------+
         |               | order_reviews              |
         +---------------+ PK (review_id, order_id)   |
                         | FK order_id                |
                         | review_score, comments     |
                         +----------------------------+
```

## Relationships

| Relationship | Key | Cardinality | Status |
|---|---|---|---|
| `orders.customer_id → customers.customer_id` | `customer_id` | 1:1 in snapshot | 0 orphans |
| `order_items.order_id → orders.order_id` | `order_id` | N:1 | 0 orphans |
| `order_items.product_id → products.product_id` | `product_id` | N:1 | 0 orphans |
| `order_items.seller_id → sellers.seller_id` | `seller_id` | N:1 | 0 orphans |
| `order_payments.order_id → orders.order_id` | `order_id` | N:1 | 0 orphans |
| `order_reviews.order_id → orders.order_id` | `order_id` | N:1 | 0 orphans |
| `products.product_category_name → category_translation` | category | N:1 | 2 orphans in raw; repaired to `unknown` in silver |
| `customers.customer_zip_code_prefix → geolocation.zip` | zip | N:M soft | 157 zips missing |
| `sellers.seller_zip_code_prefix → geolocation.zip` | zip | N:M soft | 7 zips missing |

## Grain

| Table | Grain | Primary key |
|---|---|---|
| customers | one `customer_id` | `customer_id` |
| geolocation | one observed point per zip | surrogate `geo_id`; unique after dedup |
| orders | one order | `order_id` |
| order_items | one line item | `(order_id, order_item_id)` |
| order_payments | one payment sequence | `(order_id, payment_sequential)` |
| order_reviews | one review record | `(review_id, order_id)` |
| products | one product | `product_id` |
| sellers | one seller | `seller_id` |
| category_translation | one category | `product_category_name` |

## Important caveats

1. **`customer_id` is order-scoped.** `customer_unique_id` is the real person
   key. 2,997 people have more than one order; the maximum is 17.
2. **`review_id` is not unique.** 789 IDs are reused across different orders.
   The composite `(review_id, order_id)` is unique.
3. **Geolocation has no natural key.** The raw table has 1,000,163 rows for
   19,015 zips and 261,831 exact duplicates. Aggregate to `dim_geolocation`.
4. **775 orders have no item rows; 1 has no payment; 768 have no review.**
   Use `LEFT JOIN` from orders when counting orders.
5. **Zip is a soft foreign key.** It is not unique in geolocation and 157
   customer / 7 seller zips are missing.

## Star-schema verdict

The core is a **constellation**:

- `fact_orders` — order-level fact.
- `fact_order_items` — line-item fact.
- `fact_payments` — payment fact.
- `dim_customers`, `dim_products`, `dim_sellers`, `dim_date` — conformed dimensions.
- `dim_geolocation` — zip-level dimension built from a point-level bridge.
- `category_translation` — snowflake lookup for products.
