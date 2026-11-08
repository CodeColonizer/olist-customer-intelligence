-- Q9. How do delivery times and satisfaction vary by customer state?
select
    customer_state,
    count(*)                                   as orders,
    round(sum(items_value), 2)                 as revenue,
    round(avg(delivery_days), 1)               as avg_delivery_days,
    round(100.0 * avg(is_late), 1)             as late_pct,
    round(avg(review_score), 2)                as avg_review_score,
    round(avg(freight_value), 2)               as avg_freight
from fct_orders
where is_delivered = 1
group by customer_state
order by orders desc
