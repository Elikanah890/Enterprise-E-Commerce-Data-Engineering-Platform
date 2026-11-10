select flag
from {{ ref('mart_data_quality_flags') }}
where (flag = 'orders_without_items' and row_count <> 775)
   or (flag = 'orders_without_payments' and row_count <> 1)
   or (flag = 'orders_without_reviews' and row_count <> 768)
   or (flag = 'payment_mismatches' and row_count <> 1076)
   or (flag = 'delivery_anomalies' and row_count <> 1382)
   or (flag = 'products_missing_category' and row_count <> 610)
   or (flag = 'reviews_before_purchase' and row_count <> 74)
   or (flag = 'zero_value_payments' and row_count <> 9)
