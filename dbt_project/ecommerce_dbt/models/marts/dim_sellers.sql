select
    {{ generate_stable_key(['s.seller_id']) }} as seller_key,
    s.seller_id,
    s.seller_zip_code_prefix,
    s.seller_city,
    s.seller_state,
    (g.zip_code_prefix is not null) as has_geo,
    g.lat as geo_lat,
    g.lng as geo_lng
from {{ ref('stg_sellers') }} as s
left join {{ ref('dim_geolocation') }} as g
    on s.seller_zip_code_prefix = g.zip_code_prefix
