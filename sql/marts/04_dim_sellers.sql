-- One row per seller with performance metrics on delivered orders.
-- Delivery and review metrics are order-level (an order counts once per seller).
drop table if exists dim_sellers;
create table dim_sellers as
with seller_items as (
    select
        seller_id,
        count(*)                    as items_sold,
        count(distinct order_id)    as order_count,
        round(sum(price), 2)        as revenue,
        count(distinct category)    as category_count,
        min(purchase_month)         as first_sale_month,
        max(purchase_month)         as last_sale_month
    from fct_order_items
    where order_status = 'delivered'
    group by seller_id
),
seller_orders as (
    select distinct i.seller_id, o.order_id, o.is_late, o.review_score, o.delivery_days
    from fct_order_items i
    join fct_orders o on o.order_id = i.order_id
    where o.is_delivered = 1
),
seller_service as (
    select
        seller_id,
        round(avg(is_late), 4)        as late_delivery_rate,
        round(avg(delivery_days), 2)  as avg_delivery_days,
        round(avg(review_score), 2)   as avg_review_score,
        round(avg(case when review_score <= 2 then 1.0 else 0 end), 4)
                                      as low_review_rate
    from seller_orders
    group by seller_id
)
select
    s.seller_id,
    s.seller_state,
    s.seller_city,
    coalesce(i.items_sold, 0)    as items_sold,
    coalesce(i.order_count, 0)   as order_count,
    coalesce(i.revenue, 0)       as revenue,
    i.category_count,
    i.first_sale_month,
    i.last_sale_month,
    v.late_delivery_rate,
    v.avg_delivery_days,
    v.avg_review_score,
    v.low_review_rate
from stg_sellers s
left join seller_items i   on i.seller_id = s.seller_id
left join seller_service v on v.seller_id = s.seller_id;

create unique index idx_ds_seller on dim_sellers(seller_id);
