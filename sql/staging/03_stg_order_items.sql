-- One row per item within an order.
drop view if exists stg_order_items;
create view stg_order_items as
select
    order_id,
    order_item_id,
    product_id,
    seller_id,
    datetime(shipping_limit_date) as shipping_limit_at,
    cast(price as real)           as price,
    cast(freight_value as real)   as freight_value
from raw_order_items;
