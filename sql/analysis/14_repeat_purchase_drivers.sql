-- Q14. Which first-purchase factors are linked to customers returning within 180 days?
-- Customers with a full 180-day window (first purchase Jan 2017 - Mar 2018).
-- Simple return rates by factor, to read alongside the model in
-- scripts/train_repeat_model.py (the model controls for factors jointly).
with base as (
    select * from mart_repeat_purchase where has_full_window = 1
),
by_factor as (
    select 'Delivery time' as factor,
           case when delivery_days < 7  then '1. under 7 days'
                when delivery_days < 14 then '2. 7-13 days'
                when delivery_days < 21 then '3. 14-20 days'
                else '4. 21+ days' end as grp,
           returned_180d
    from base
    union all
    select 'Region', region, returned_180d from base
    union all
    select 'Instalments',
           case when installments = 1 then '1. one payment'
                when installments <= 3 then '2. 2-3'
                when installments <= 6 then '3. 4-6'
                else '4. 7+' end,
           returned_180d
    from base
    union all
    select 'Review score',
           case when review_missing = 1 then '4. no review'
                when review_score <= 2  then '1. 1-2 stars'
                when review_score < 4   then '2. 3 stars'
                else '3. 4-5 stars' end,
           returned_180d
    from base
    union all
    select 'Product category (1,000+ customers)', category, returned_180d
    from base
    where category in (select category from base group by category having count(*) >= 1000)
)
select
    factor,
    grp                                   as factor_group,
    count(*)                              as customers,
    sum(returned_180d)                    as returners,
    round(100.0 * avg(returned_180d), 2)  as return_rate_pct
from by_factor
group by factor, grp
order by factor, return_rate_pct desc
