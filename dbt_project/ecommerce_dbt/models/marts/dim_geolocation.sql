select
    zip_code_prefix,
    coalesce(
        percentile_cont(0.5) within group (order by lat)
            filter (where not is_outlier),
        percentile_cont(0.5) within group (order by lat)
    ) as lat,
    coalesce(
        percentile_cont(0.5) within group (order by lng)
            filter (where not is_outlier),
        percentile_cont(0.5) within group (order by lng)
    ) as lng,
    mode() within group (order by city) as city,
    mode() within group (order by state) as state,
    count(*) as point_count,
    count(*) filter (where is_outlier) as outlier_count
from {{ ref('stg_geolocation') }}
group by zip_code_prefix
