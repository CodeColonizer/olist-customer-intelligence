-- Customer order counts add up to the number of delivered orders.
select (select sum(order_count) from dim_customers) as dim_total, (select count(*) from fct_orders where is_delivered = 1) as fct_total
where (select sum(order_count) from dim_customers) <> (select count(*) from fct_orders where is_delivered = 1)
