-- One row per order item, enriched with product, seller and order context.
drop table if exists fct_order_items;
create table fct_order_items as
select
    i.order_id,
    i.order_item_id,
    i.product_id,
    i.seller_id,
    p.category,
    s.seller_state,
    o.purchase_month,
    o.order_status,
    i.price,
    i.freight_value,
    round(i.price + i.freight_value, 2) as item_total
from stg_order_items i
join stg_orders o   on o.order_id = i.order_id
left join stg_products p on p.product_id = i.product_id
left join stg_sellers s  on s.seller_id = i.seller_id;

create index idx_foi_order  on fct_order_items(order_id);
create index idx_foi_seller on fct_order_items(seller_id);
