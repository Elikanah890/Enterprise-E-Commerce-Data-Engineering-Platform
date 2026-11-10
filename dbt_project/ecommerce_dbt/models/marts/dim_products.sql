select
    {{ generate_stable_key(['p.product_id']) }} as product_key,
    p.product_id,
    c.category_key,
    p.product_category_name,
    c.product_category_name_english,
    p.category_missing,
    p.product_name_length,
    p.product_description_length,
    p.product_photos_qty,
    p.product_weight_g,
    p.product_length_cm,
    p.product_height_cm,
    p.product_width_cm,
    (
        p.product_length_cm::integer
        * p.product_height_cm::integer
        * p.product_width_cm::integer
    ) as product_volume_cm3,
    round(
        p.product_weight_g::numeric
        / nullif(
            p.product_length_cm::integer
            * p.product_height_cm::integer
            * p.product_width_cm::integer,
            0
        ),
        4
    ) as density_g_cm3
from {{ ref('stg_products') }} as p
left join {{ ref('dim_category') }} as c
    on p.product_category_name = c.product_category_name
