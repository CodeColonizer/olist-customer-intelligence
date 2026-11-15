-- Q17. Do multi-item and multi-seller orders get worse reviews even when they
-- arrive on time? Delivered, reviewed orders delivered on or before the estimated
-- date, by basket type. missing_items_pct: share of the 1-2 star comments for
-- these orders that say items or parts were missing (scripts/analyse_reviews.py).
with on_time as (
    select
        o.order_id,
        case
            when o.item_count <= 1  then '1. Single item'
            when o.seller_count = 1 then '2. Several items, one seller'
            else                         '3. Several items, several sellers'
        end                                              as basket_type,
        case when o.review_score <= 2 then 1 else 0 end  as is_low_review
    from fct_orders o
    where o.is_delivered = 1
      and o.is_late = 0
      and o.review_score is not null
),
missing as (
    select distinct order_id from review_themes where theme = 'Items or parts missing'
),
low_comments as (
    select c.order_id, case when m.order_id is not null then 1 else 0 end as mentions_missing
    from mart_review_comments c
    left join missing m on m.order_id = c.order_id
    where c.review_score <= 2
)
select
    t.basket_type,
    count(*)                                                              as on_time_orders,
    round(100.0 * count(*) / sum(count(*)) over (), 1)                    as order_share_pct,
    sum(t.is_low_review)                                                  as low_reviews,
    round(100.0 * avg(t.is_low_review), 1)                                as low_review_pct,
    round(100.0 * sum(t.is_low_review) / sum(sum(t.is_low_review)) over (), 1) as share_of_low_reviews_pct,
    round(100.0 * avg(lc.mentions_missing), 1)                            as missing_items_pct
from on_time t
left join low_comments lc on lc.order_id = t.order_id
group by t.basket_type
order by t.basket_type
