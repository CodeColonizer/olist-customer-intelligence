-- One row per review that has a written comment, with the order context needed
-- to interpret it (delivery timing, basket size, number of sellers, category).
--
-- Used by scripts/analyse_reviews.py, which tags each low-score comment with
-- complaint themes. Comment text is kept as written (Portuguese); the script
-- handles normalisation (case, accents, punctuation).
--
-- answered_before_delivery: the customer submitted the review before the
-- recorded delivery date, i.e. they were still waiting when they wrote it.
drop table if exists mart_review_comments;
create table mart_review_comments as
with main_category as (
    -- the category with the highest item value in the order
    select order_id, category
    from (
        select order_id, category,
               row_number() over (partition by order_id
                                  order by sum(price) desc, category) as rn
        from fct_order_items
        group by order_id, category
    )
    where rn = 1
)
select
    r.review_id,
    r.order_id,
    o.customer_unique_id,
    r.review_score,
    r.review_title,
    r.review_message,
    r.review_answered_at,
    o.order_status,
    o.is_delivered,
    o.is_late,
    o.days_late,
    o.item_count,
    o.seller_count,
    case
        when o.item_count <= 1  then '1. Single item'
        when o.seller_count = 1 then '2. Several items, one seller'
        else                         '3. Several items, several sellers'
    end                                                        as basket_type,
    coalesce(c.category, 'unknown')                            as category,
    case
        when o.is_delivered = 1 and r.review_answered_at < so.delivered_at then 1
        when o.is_delivered = 1 then 0
    end                                                        as answered_before_delivery
from stg_reviews r
join fct_orders o          on o.order_id = r.order_id
join stg_orders so         on so.order_id = r.order_id
left join main_category c  on c.order_id = r.order_id
where r.has_comment = 1;

create unique index idx_mrc_order on mart_review_comments(order_id);
create index idx_mrc_customer      on mart_review_comments(customer_unique_id);
