-- Q5. How does delivery performance affect customer satisfaction?
select
    case
        when days_late <= -10 then '1. 10+ days early'
        when days_late <= -1  then '2. 1-9 days early'
        when days_late = 0    then '3. on the estimated day'
        when days_late <= 3   then '4. 1-3 days late'
        when days_late <= 7   then '5. 4-7 days late'
        else '6. 8+ days late'
    end                                                            as delivery_timing,
    count(*)                                                       as orders,
    round(100.0 * count(*) / sum(count(*)) over (), 1)             as pct_of_orders,
    round(avg(review_score), 2)                                    as avg_review_score,
    round(100.0 * avg(case when review_score <= 2 then 1.0 else 0 end), 1) as low_review_pct
from fct_orders
where is_delivered = 1 and review_score is not null
group by 1
order by 1
