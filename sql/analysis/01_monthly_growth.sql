-- Q1. How are orders and revenue trending month by month?
-- Delivered orders only, window limited to complete months (Jan 2017 - Aug 2018).
-- Revenue = product price excluding freight (GMV).
with monthly as (
    select
        purchase_month,
        count(*)                          as orders,
        count(distinct customer_unique_id) as customers,
        round(sum(items_value), 2)        as revenue,
        round(avg(order_value), 2)        as avg_order_value
    from fct_orders
    where is_delivered = 1
      and purchase_month between '2017-01' and '2018-08'
    group by purchase_month
)
select
    purchase_month,
    orders,
    customers,
    revenue,
    avg_order_value,
    round(100.0 * (revenue - lag(revenue) over (order by purchase_month))
          / lag(revenue) over (order by purchase_month), 1) as revenue_mom_pct
from monthly
order by purchase_month
