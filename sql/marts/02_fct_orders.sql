-- One row per order: the main fact table for analysis and Power BI.
-- items_value / freight_value come from order items (product revenue);
-- payment_value is what the customer paid (can differ slightly due to
-- instalment interest and vouchers).
drop table if exists fct_orders;
create table fct_orders as
with items as (
    select
        order_id,
        count(*)                       as item_count,
        count(distinct seller_id)      as seller_count,
        count(distinct product_id)     as product_count,
        round(sum(price), 2)           as items_value,
        round(sum(freight_value), 2)   as freight_value
    from stg_order_items
    group by order_id
)
select
    o.order_id,
    c.customer_unique_id,
    c.customer_state,
    c.customer_city,
    o.order_status,
    o.purchased_at,
    o.purchase_date,
    o.purchase_month,
    coalesce(i.item_count, 0)                         as item_count,
    coalesce(i.seller_count, 0)                       as seller_count,
    coalesce(i.product_count, 0)                      as product_count,
    coalesce(i.items_value, 0)                        as items_value,
    coalesce(i.freight_value, 0)                      as freight_value,
    round(coalesce(i.items_value, 0)
          + coalesce(i.freight_value, 0), 2)          as order_value,
    p.payment_value,
    p.primary_payment_type,
    p.max_installments,
    o.is_delivered,
    o.delivery_days,
    o.estimated_delivery_days,
    o.days_late,
    o.is_late,
    r.review_score,
    r.has_comment                                     as review_has_comment
from stg_orders o
join stg_customers c     on c.customer_id = o.customer_id
left join items i        on i.order_id = o.order_id
left join stg_payments p on p.order_id = o.order_id
left join stg_reviews r  on r.order_id = o.order_id;

create unique index idx_fo_order    on fct_orders(order_id);
create index idx_fo_customer        on fct_orders(customer_unique_id);
