-- No orders are dropped or duplicated between raw and fct_orders.
select (select count(*) from raw_orders) as raw_n, (select count(*) from fct_orders) as fct_n
where (select count(*) from raw_orders) <> (select count(*) from fct_orders)
