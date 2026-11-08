-- Q8. Do sellers with more late deliveries get worse reviews?
-- Sellers with at least 30 delivered orders, grouped by late-delivery rate.
select
    case
        when late_delivery_rate < 0.05 then '1. under 5% late'
        when late_delivery_rate < 0.10 then '2. 5-10% late'
        when late_delivery_rate < 0.15 then '3. 10-15% late'
        else '4. 15%+ late'
    end                                   as seller_late_band,
    count(*)                              as sellers,
    sum(order_count)                      as orders,
    round(sum(revenue), 2)                as revenue,
    round(avg(avg_review_score), 2)       as avg_review_score,
    round(100.0 * avg(low_review_rate), 1) as avg_low_review_pct
from dim_sellers
where order_count >= 30
group by 1
order by 1
