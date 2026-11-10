# Data Quality Report — Olist Brazilian E-Commerce

**Method:** Nine CSVs read with pandas 3.0.3 using `dtype=str`,
`keep_default_na=False`, and UTF-8 with BOM handling. Types inferred by pattern;
dates parsed with `errors="coerce"`. Counts are exact from the parsed data.

**Data window:** orders 2016-09-04 21:15:19 → 2018-10-17 17:30:18; reviews
through 2018-10-29 12:27:35.

> `wc -l` reports 104,720 review lines but the parsed row count is **99,224**
> because 3,852 review messages contain embedded newlines.

## 1. Inventory

| File | Rows | Cols | Size | PK |
|---|---:|---:|---:|---|
| `olist_customers_dataset.csv` | 99,441 | 5 | 9.03 MB | `customer_id` |
| `olist_geolocation_dataset.csv` | 1,000,163 | 5 | 61.27 MB | none |
| `olist_order_items_dataset.csv` | 112,650 | 7 | 15.44 MB | `(order_id, order_item_id)` |
| `olist_order_payments_dataset.csv` | 103,886 | 5 | 5.78 MB | `(order_id, payment_sequential)` |
| `olist_order_reviews_dataset.csv` | 99,224 | 7 | 14.45 MB | `(review_id, order_id)` |
| `olist_orders_dataset.csv` | 99,441 | 8 | 17.65 MB | `order_id` |
| `olist_products_dataset.csv` | 32,951 | 9 | 2.38 MB | `product_id` |
| `olist_sellers_dataset.csv` | 3,095 | 4 | 0.17 MB | `seller_id` |
| `product_category_name_translation.csv` | 71 | 2 | 2.6 KB | `product_category_name` |

## 2. Headline metrics

| Metric | Value |
|---|---:|
| Orders | 99,441 |
| Delivered | 96,478 (97.02%) |
| Item revenue | R$ 13,591,643.70 |
| Freight revenue | R$ 2,251,909.54 |
| Payment total | R$ 16,008,872.12 |
| Average order value | R$ 160.58 |
| Average items/order | 1.142 |
| Late deliveries | 7,827 (7.87%) |
| Mean review score | 4.0864 |
| Repeat buyers | 2,997 (max 17 orders) |

## 3. Issues ranked by severity

### Critical

| Issue | Evidence | Impact | Fix |
|---|---|---|---|
| Geolocation fan-out | 1,000,163 rows, 19,015 zips, 261,831 exact duplicates, 8,556 multi-city zips | Joining facts to geo multiplies rows | Aggregate to `dim_geolocation` |
| `review_id` not unique | 814 excess rows, 789 IDs reused across orders | Joining on `review_id` duplicates orders | Key on `(review_id, order_id)`; aggregate by order |
| Zip must be text | 23,995 customer, 1,027 seller, 245,733 geo values start with `0` | Integer cast destroys zip joins | `char(5)` + `LPAD` |

### High

| Issue | Evidence | Impact | Fix |
|---|---|---|---|
| Orders without items | 775 orders (0.78%); 772 have payments | Inner joins undercount | `LEFT JOIN`; keep all statuses |
| Products without category | 610 products (1.85%); 1,603 item rows (1.42%) | Category metrics incomplete | Map to `unknown`; add 2 translations |
| Delivery timestamp gaps | 2,965 delivered-date nulls; 1,783 carrier nulls; 160 approval nulls | SLA averages biased | Flag nulls; use delivered-only views |
| Date-order anomalies | 1,359 carrier < approval; 23 delivery < carrier; 74 reviews before purchase | Invalid duration features | Flag, do not drop |
| Payment reconciliation | 382/98,666 item orders differ >R$0.01; 772 paid no-item orders | Payment vs item revenue diverge | Flag mismatches; document rule |
| Shipping dates in 2020 | 4 rows on 3 orders | Out-of-window features | Flag/quarantine |

### Medium

| Issue | Evidence | Impact | Fix |
|---|---|---|---|
| Geo outliers | 42 points outside Brazil bbox | Bad centroids | Filter before median |
| Zip ambiguity | 8 zips map to >1 state | State assignment uncertain | Mode + confidence flag |
| City normalization | 8,011 raw vs 5,968 accent-stripped; 2,081 NFD | Text grouping unreliable | Lowercase, trim, unaccent |
| Missing geo zips | 157 customer, 7 seller | Missing coordinates | Left join; `has_geo` flag |
| Zero/invalid payments | 9 zero rows, 2 zero installments, 3 `not_defined` | Payment averages skewed | Flag; exclude from AOV |
| Product edge cases | 1 all-null row, 2 missing dims, 4 zero weights | Freight/volume features | Null out zeros; quarantine all-null |

### Low

| Issue | Evidence | Impact | Fix |
|---|---|---|---|
| BOM in translation | header starts with `\ufeff` | Header mismatch | `utf-8-sig` |
| Sparse review text | 88.34% no title, 58.70% no message | Text models need missingness handling | Flags; no imputation |
| Embedded newlines | 3,852 messages | Line-based tools misparse | Proper CSV parser |
| No timezone metadata | all timestamps naive | Ambiguity | Document `America/Sao_Paulo` |
| Column typos | `lenght` | Confusing schema | Rename in silver |
| Unused geo zips | 4,099 | Wasted reference rows | Keep; harmless |

## 4. Relationship integrity

| Relationship | Orphans | Notes |
|---|---:|---|
| `orders.customer_id → customers.customer_id` | 0 | 1:1 in snapshot |
| `order_items.order_id → orders.order_id` | 0 | 775 orders without items |
| `order_items.product_id → products.product_id` | 0 | all products referenced |
| `order_items.seller_id → sellers.seller_id` | 0 | all sellers referenced |
| `order_payments.order_id → orders.order_id` | 0 | 1 order unpaid |
| `order_reviews.order_id → orders.order_id` | 0 | 768 orders unreviewed |
| `products.category → category_translation` | 2 | `pc_gamer`, `portateis_cozinha_e_preparadores_de_alimentos` |
| customer zip → geolocation | 157 zips | soft link |
| seller zip → geolocation | 7 zips | soft link |

## 5. Cleaning rules (must apply before ingestion)

1. Load raw as text; strip BOM; preserve zip prefixes with `LPAD(...,5,'0')`.
2. Deduplicate geolocation on all five columns; filter out-of-Brazil points;
   aggregate to one row per zip using median lat/lng and modal city/state.
3. Key reviews on `(review_id, order_id)`. For order-level analysis, select the
   latest review and keep a review count.
4. Map missing/unknown product categories to `unknown`; add `pc_gamer` and
   `portateis_cozinha_e_preparadores_de_alimentos` to the translation table.
5. Rename `product_name_lenght` / `product_description_lenght`.
6. Normalise city text (lower, trim, unaccent) and UF (upper).
7. Keep canceled/unavailable orders; create delivered-only views.
8. Flag—but do not drop—date anomalies, zero payments, zero installments,
   zero weights, and missing geolocation.
9. Do not deduplicate `order_items`, `order_payments`, or `order_reviews` by
   `order_id`; multiple rows are legitimate.
10. Pre-aggregate items, payments, and reviews before joining to orders.

## 6. Validation queries

```sql
-- Row counts
SELECT 'customers' AS table_name, count(*) FROM silver.customers
UNION ALL SELECT 'orders', count(*) FROM silver.orders
UNION ALL SELECT 'order_items', count(*) FROM silver.order_items
UNION ALL SELECT 'order_payments', count(*) FROM silver.order_payments
UNION ALL SELECT 'order_reviews', count(*) FROM silver.order_reviews
UNION ALL SELECT 'products', count(*) FROM silver.products
UNION ALL SELECT 'sellers', count(*) FROM silver.sellers;

-- Orphan checks (all should return 0)
SELECT count(*) FROM silver.order_items i
LEFT JOIN silver.orders o USING (order_id) WHERE o.order_id IS NULL;
SELECT count(*) FROM silver.order_items i
LEFT JOIN silver.products p USING (product_id) WHERE p.product_id IS NULL;
SELECT count(*) FROM silver.order_items i
LEFT JOIN silver.sellers s USING (seller_id) WHERE s.seller_id IS NULL;
SELECT count(*) FROM silver.order_payments p
LEFT JOIN silver.orders o USING (order_id) WHERE o.order_id IS NULL;
SELECT count(*) FROM silver.order_reviews r
LEFT JOIN silver.orders o USING (order_id) WHERE o.order_id IS NULL;

-- Duplicate key checks
SELECT count(*) FROM (
  SELECT review_id, order_id FROM silver.order_reviews
  GROUP BY 1,2 HAVING count(*) > 1
) d;

-- Delivery rate
SELECT round(100.0 * count(*) FILTER (WHERE order_status = 'delivered')
             / count(*), 2) AS delivered_pct
FROM silver.orders;
```

## 7. Accepted gaps

- Review title/message sparsity is expected and is not imputed.
- One delivered order has no payment record; retained for fidelity.
- 775 itemless orders are retained; they are valid unavailable/canceled states.
- 42 geolocation outliers are excluded from centroids but retained in the raw
  layer for audit.
- Naive timestamps are treated as `America/Sao_Paulo` by convention.
