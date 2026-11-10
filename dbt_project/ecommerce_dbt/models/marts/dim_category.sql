select
    {{ generate_stable_key(['product_category_name']) }} as category_key,
    product_category_name,
    product_category_name_english
from {{ ref('stg_category_translation') }}
