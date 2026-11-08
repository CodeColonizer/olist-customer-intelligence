-- Q12. Profile of the k-means customer segments (see scripts/segment_customers.py).
select
    s.cluster_segment,
    count(*)                                                     as customers,
    round(100.0 * count(*) / sum(count(*)) over (), 1)           as customer_share_pct,
    round(sum(f.total_spend), 2)                                 as revenue,
    round(100.0 * sum(f.total_spend) / sum(sum(f.total_spend)) over (), 1) as revenue_share_pct,
    round(avg(f.total_spend), 2)                                 as avg_spend,
    round(avg(f.recency_days), 0)                                as avg_recency_days,
    round(avg(f.avg_review_score), 2)                            as avg_review_score,
    round(avg(f.avg_delivery_days), 1)                           as avg_delivery_days,
    round(100.0 * avg(f.experienced_late), 1)                    as experienced_late_pct,
    round(avg(f.avg_installments), 1)                            as avg_installments,
    round(100.0 * avg(f.is_returning_customer), 1)               as returning_pct
from customer_segments s
join mart_customer_features f on f.customer_unique_id = s.customer_unique_id
group by s.cluster_segment
order by revenue desc
