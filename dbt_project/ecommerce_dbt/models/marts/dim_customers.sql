select
    {{ generate_stable_key(['c.customer_id']) }} as customer_key,
    c.customer_id,
    c.customer_unique_id,
    c.customer_zip_code_prefix,
    c.customer_city,
    c.customer_state,
    (g.zip_code_prefix is not null) as has_geo,
    g.lat as geo_lat,
    g.lng as geo_lng
from {{ ref('stg_customers') }} as c
left join {{ ref('dim_geolocation') }} as g
    on c.customer_zip_code_prefix = g.zip_code_prefix
