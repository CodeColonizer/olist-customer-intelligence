-- Q18. Which categories are growing or shrinking, and what is the outlook?
-- Items ordered (cancelled/unavailable orders excluded) for the 12 categories
-- with the most items in Jan-Aug 2018, plus the marketplace total (rank 0).
-- Year on year compares Jan-Aug 2018 with Jan-Aug 2017; momentum compares
-- Jun-Aug 2018 with Mar-May 2018. Late rates show how delivery coped with the
-- Black Friday peak in 2017 (share of delivered items that arrived late).
-- The forecast columns come from scripts/forecast_demand.py.
with by_category as (
    select
        category,
        sum(case when month between '2017-01' and '2017-08' then items else 0 end) as items_2017,
        sum(case when month between '2018-01' and '2018-08' then items else 0 end) as items_2018,
        sum(case when month between '2018-03' and '2018-05' then items else 0 end) as items_mar_may,
        sum(case when month between '2018-06' and '2018-08' then items else 0 end) as items_jun_aug,
        sum(case when month = '2017-10' then items else 0 end)                       as items_oct_2017,
        sum(case when month = '2017-11' then items else 0 end)                       as items_nov_2017
    from mart_category_demand
    group by category
),
ranked as (
    select *,
           row_number() over (order by items_2018 desc)  as volume_rank,
           100.0 * items_2018 / sum(items_2018) over ()   as share_2018_pct
    from by_category
),
series as (
    select volume_rank, category, items_2017, items_2018, items_mar_may, items_jun_aug,
           items_oct_2017, items_nov_2017, share_2018_pct
    from ranked
    where volume_rank <= 12
    union all
    select 0, 'All categories', sum(items_2017), sum(items_2018), sum(items_mar_may),
           sum(items_jun_aug), sum(items_oct_2017), sum(items_nov_2017), 100.0
    from ranked
),
lateness as (
    select i.category,
           avg(case when i.purchase_month = '2017-10' then o.is_late end) as late_oct,
           avg(case when i.purchase_month = '2017-11' then o.is_late end) as late_nov
    from fct_order_items i
    join fct_orders o on o.order_id = i.order_id
    where o.is_delivered = 1
    group by i.category
    union all
    select 'All categories',
           avg(case when i.purchase_month = '2017-10' then o.is_late end),
           avg(case when i.purchase_month = '2017-11' then o.is_late end)
    from fct_order_items i
    join fct_orders o on o.order_id = i.order_id
    where o.is_delivered = 1
),
forecast as (
    select series                    as category,
           avg(baseline_forecast)    as forecast_per_month,
           max(black_friday_scenario) as november_black_friday
    from demand_forecasts
    group by series
)
select
    s.volume_rank,
    s.category,
    s.items_2018,
    round(s.share_2018_pct, 1)                                                     as share_2018_pct,
    round(100.0 * (s.items_2018 - s.items_2017) / s.items_2017, 0)                 as yoy_growth_pct,
    round(100.0 * (s.items_jun_aug - s.items_mar_may) / s.items_mar_may, 1)        as momentum_pct,
    round(1.0 * s.items_nov_2017 / s.items_oct_2017, 2)                            as nov_vs_oct_2017,
    round(100.0 * l.late_oct, 1)                                                   as late_pct_oct_2017,
    round(100.0 * l.late_nov, 1)                                                   as late_pct_nov_2017,
    round(s.items_jun_aug / 3.0, 0)                                                as recent_monthly_avg,
    f.forecast_per_month,
    f.november_black_friday
from series s
left join lateness l on l.category = s.category
left join forecast f on f.category = s.category
order by s.volume_rank
