-- Q15. How do seller scorecard tiers compare, and how much revenue sits in each?
-- Established sellers (30+ delivered orders); see sql/marts/10_mart_seller_scorecard.sql.
select
    tier,
    count(*)                                                        as sellers,
    round(100.0 * count(*) / sum(count(*)) over (), 1)              as seller_share_pct,
    round(sum(revenue), 2)                                          as revenue,
    round(100.0 * sum(revenue) / sum(sum(revenue)) over (), 1)      as revenue_share_pct,
    round(avg(score), 1)                                            as avg_score,
    round(100.0 * avg(late_delivery_rate), 1)                       as avg_late_delivery_pct,
    round(100.0 * avg(late_dispatch_rate), 1)                       as avg_late_dispatch_pct,
    round(100.0 * avg(low_review_rate), 1)                          as avg_low_review_pct,
    round(100.0 * avg(cancellation_rate), 2)                        as avg_cancellation_pct,
    round(avg(avg_review_score), 2)                                 as avg_review_score
from mart_seller_scorecard
group by tier
order by tier
