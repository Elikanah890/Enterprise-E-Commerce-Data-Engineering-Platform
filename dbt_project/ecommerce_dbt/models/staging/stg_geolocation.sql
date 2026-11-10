select
    rtrim(zip_code_prefix) as zip_code_prefix,
    lat,
    lng,
    city,
    rtrim(state) as state,
    is_outlier
from {{ source('silver', 'geolocation') }}
