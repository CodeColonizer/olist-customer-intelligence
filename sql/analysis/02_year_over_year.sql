-- Q2. How much did the business grow year on year (Jan-Aug 2018 vs Jan-Aug 2017)?
with by_year as (
    select
        substr(purchase_month, 1, 4)       as year,
        count(*)                           as orders,
        round(sum(items_value), 2)         as revenue,
        count(distinct customer_unique_id) as customers
    from fct_orders
    where is_delivered = 1
      and substr(purchase_month, 6, 2) between '01' and '08'
      and substr(purchase_month, 1, 4) in ('2017', '2018')
    group by year
)
select
    max(case when year = '2017' then orders end)    as orders_2017,
    max(case when year = '2018' then orders end)    as orders_2018,
    round(100.0 * (max(case when year = '2018' then orders end)
                 - max(case when year = '2017' then orders end))
          / max(case when year = '2017' then orders end), 1) as orders_growth_pct,
    max(case when year = '2017' then revenue end)   as revenue_2017,
    max(case when year = '2018' then revenue end)   as revenue_2018,
    round(100.0 * (max(case when year = '2018' then revenue end)
                 - max(case when year = '2017' then revenue end))
          / max(case when year = '2017' then revenue end), 1) as revenue_growth_pct
from by_year
