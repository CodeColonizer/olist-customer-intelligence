-- Seller scorecard: a 0-100 performance score and tier for established sellers
-- (30+ delivered orders), so the marketplace can see who to reward, support
-- or review.
--
-- Four metrics, all "lower is better":
--   late_dispatch_rate   item handed to the carrier after the seller's shipping
--                        deadline (fully in the seller's control)
--   late_delivery_rate   order reached the customer after the promised date
--   low_review_rate      share of the seller's reviewed orders rated 1-2 stars
--   cancellation_rate    share of the seller's orders cancelled or unavailable
--
-- Each metric is converted to a percentile among established sellers
-- (percent_rank: 0 = best) and the score is a weighted average of
-- (1 - percentile) x 100. Weights reflect what customers feel most:
--   late delivery 30%, low reviews 30%, late dispatch 25%, cancellations 15%.
-- The score is relative: 50 means "middle of the pack", not "50% good".
drop table if exists mart_seller_scorecard;
create table mart_seller_scorecard as
with seller_orders as (
    -- one row per seller per order (an order can include several sellers)
    select distinct seller_id, order_id
    from fct_order_items
),
order_metrics as (
    select
        so.seller_id,
        count(*)                                                       as all_orders,
        sum(case when o.order_status in ('canceled', 'unavailable')
                 then 1 else 0 end)                                    as cancelled_orders,
        sum(o.is_delivered)                                            as delivered_orders,
        avg(case when o.is_delivered = 1 then o.is_late end)           as late_delivery_rate,
        avg(case when o.is_delivered = 1 and o.review_score is not null
                 then case when o.review_score <= 2 then 1.0 else 0 end end) as low_review_rate,
        avg(case when o.is_delivered = 1 then o.review_score end)      as avg_review_score
    from seller_orders so
    join fct_orders o on o.order_id = so.order_id
    group by so.seller_id
),
dispatch as (
    select
        i.seller_id,
        avg(case when o.delivered_to_carrier_at > i.shipping_limit_at
                 then 1.0 else 0 end)                                  as late_dispatch_rate
    from stg_order_items i
    join stg_orders o on o.order_id = i.order_id
    where o.is_delivered = 1 and o.delivered_to_carrier_at is not null
    group by i.seller_id
),
established as (
    select
        m.seller_id,
        d.seller_state,
        d.revenue,
        m.delivered_orders,
        m.all_orders,
        round(1.0 * m.cancelled_orders / m.all_orders, 4)              as cancellation_rate,
        round(m.late_delivery_rate, 4)                                 as late_delivery_rate,
        round(p.late_dispatch_rate, 4)                                 as late_dispatch_rate,
        round(m.low_review_rate, 4)                                    as low_review_rate,
        round(m.avg_review_score, 2)                                   as avg_review_score
    from order_metrics m
    join dim_sellers d on d.seller_id = m.seller_id
    join dispatch p    on p.seller_id = m.seller_id
    where m.delivered_orders >= 30
),
ranked as (
    select
        *,
        percent_rank() over (order by late_delivery_rate) as pr_late_delivery,
        percent_rank() over (order by low_review_rate)    as pr_low_review,
        percent_rank() over (order by late_dispatch_rate) as pr_late_dispatch,
        percent_rank() over (order by cancellation_rate)  as pr_cancellation
    from established
),
scored as (
    select
        *,
        round(100 * (0.30 * (1 - pr_late_delivery)
                   + 0.30 * (1 - pr_low_review)
                   + 0.25 * (1 - pr_late_dispatch)
                   + 0.15 * (1 - pr_cancellation)), 1) as score
    from ranked
)
select
    seller_id,
    seller_state,
    revenue,
    delivered_orders,
    late_delivery_rate,
    late_dispatch_rate,
    low_review_rate,
    cancellation_rate,
    avg_review_score,
    score,
    case
        when score >= 75 then '1. Top performer'
        when score >= 50 then '2. Solid'
        when score >= 25 then '3. Needs improvement'
        else                  '4. At risk'
    end as tier,
    rank() over (order by score desc) as score_rank
from scored;

create unique index idx_mss_seller on mart_seller_scorecard(seller_id);
