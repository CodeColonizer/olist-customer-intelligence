-- Monthly demand by product category: one row per category per month,
-- Jan 2017 to Aug 2018 (the complete months), with zero-filled gaps.
--
-- Demand = items ordered (each order item row is one unit), counted in the
-- month of purchase. Cancelled and unavailable orders are excluded, but
-- orders that were still in transit are included: demand happens when the
-- customer orders, whether or not delivery has finished.
--
-- Used by scripts/forecast_demand.py.
drop table if exists mart_category_demand;
create table mart_category_demand as
with recursive months(month_start) as (
    select date('2017-01-01')
    union all
    select date(month_start, '+1 month') from months
    where month_start < date('2018-08-01')
),
categories as (
    select distinct coalesce(category, 'unknown') as category
    from fct_order_items
),
items as (
    select
        purchase_month,
        coalesce(category, 'unknown')  as category,
        count(*)                       as items,
        count(distinct order_id)       as orders,
        round(sum(price), 2)           as revenue
    from fct_order_items
    where order_status not in ('canceled', 'unavailable')
    group by purchase_month, coalesce(category, 'unknown')
)
select
    strftime('%Y-%m', m.month_start)    as month,
    c.category,
    coalesce(i.items, 0)                as items,
    coalesce(i.orders, 0)               as orders,
    coalesce(i.revenue, 0)              as revenue
from months m
cross join categories c
left join items i
    on i.purchase_month = strftime('%Y-%m', m.month_start)
   and i.category = c.category;

create unique index idx_mcd_month_category on mart_category_demand(month, category);
