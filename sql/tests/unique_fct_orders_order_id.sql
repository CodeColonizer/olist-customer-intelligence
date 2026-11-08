-- Each order appears exactly once in fct_orders.
select order_id, count(*) as n from fct_orders group by order_id having count(*) > 1
