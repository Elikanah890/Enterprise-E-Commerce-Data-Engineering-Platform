select
    rtrim(seller_id) as seller_id,
    rtrim(seller_zip_code_prefix) as seller_zip_code_prefix,
    seller_city,
    rtrim(seller_state) as seller_state
from {{ source('silver', 'sellers') }}
