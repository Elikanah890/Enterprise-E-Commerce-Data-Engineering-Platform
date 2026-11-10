select
    rtrim(customer_id) as customer_id,
    rtrim(customer_unique_id) as customer_unique_id,
    rtrim(customer_zip_code_prefix) as customer_zip_code_prefix,
    customer_city,
    rtrim(customer_state) as customer_state
from {{ source('silver', 'customers') }}
