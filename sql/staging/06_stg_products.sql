-- Products with an English category name.
-- 610 products have no category ('unknown'); 2 categories have no
-- translation, so the Portuguese name is used as a fallback.
drop view if exists stg_products;
create view stg_products as
select
    p.product_id,
    coalesce(p.product_category_name, 'unknown')                    as category_pt,
    coalesce(t.product_category_name_english,
             p.product_category_name, 'unknown')                    as category,
    cast(p.product_weight_g as real)                                as weight_g,
    cast(p.product_length_cm as real)
        * cast(p.product_height_cm as real)
        * cast(p.product_width_cm as real)                          as volume_cm3,
    cast(p.product_photos_qty as integer)                           as photos_qty
from raw_products p
left join raw_category_translation t
    on p.product_category_name = t.product_category_name;
