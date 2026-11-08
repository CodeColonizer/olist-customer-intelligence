-- Q11. What do the rule-based RFM segments look like, and what are they worth?
select
    rfm_segment,
    count(*)                                                     as customers,
    round(100.0 * count(*) / sum(count(*)) over (), 1)           as customer_share_pct,
    round(sum(total_spend), 2)                                   as revenue,
    round(100.0 * sum(total_spend) / sum(sum(total_spend)) over (), 1) as revenue_share_pct,
    round(avg(total_spend), 2)                                   as avg_spend,
    round(avg(recency_days), 0)                                  as avg_recency_days,
    round(avg(avg_review_score), 2)                              as avg_review_score,
    round(100.0 * avg(experienced_late), 1)                      as experienced_late_pct
from mart_customer_features
group by rfm_segment
order by rfm_segment
