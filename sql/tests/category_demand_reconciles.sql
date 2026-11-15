-- Category demand: a complete 20-month grid for every category (no gaps, no
-- duplicates), and total items reconcile to the valid order items in the window.
select 'grid' as check_name, count(*) as value
from mart_category_demand
having count(*) <> 20 * (select count(distinct category) from mart_category_demand)
    or count(*) <> count(distinct month || '|' || category)
union all
select 'items', (select sum(items) from mart_category_demand)
where (select sum(items) from mart_category_demand) <> (
    select count(*) from fct_order_items
    where order_status not in ('canceled', 'unavailable')
      and purchase_month between '2017-01' and '2018-08')
