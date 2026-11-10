select
    rtrim(product_category_name) as product_category_name,
    rtrim(product_category_name_english) as product_category_name_english
from {{ source('silver', 'category_translation') }}
