with date_bounds as (
    select
        date_trunc('year', min(order_purchase_timestamp))::date as first_date,
        (date_trunc('year', max(order_purchase_timestamp))
            + interval '2 years - 1 day')::date as last_date
    from {{ ref('stg_orders') }}
)

select
    to_char(calendar.date_day, 'YYYYMMDD')::integer as date_key,
    calendar.date_day::date as date_day,
    extract(year from calendar.date_day)::integer as year,
    extract(quarter from calendar.date_day)::integer as quarter,
    extract(month from calendar.date_day)::integer as month,
    trim(to_char(calendar.date_day, 'Month')) as month_name,
    extract(day from calendar.date_day)::integer as day_of_month,
    extract(isodow from calendar.date_day)::integer as day_of_week,
    trim(to_char(calendar.date_day, 'Day')) as day_name,
    extract(isodow from calendar.date_day) in (6, 7) as is_weekend
from date_bounds
cross join lateral generate_series(
    date_bounds.first_date::timestamp,
    date_bounds.last_date::timestamp,
    interval '1 day'
) as calendar(date_day)
