-- Every order item links to an order (referential integrity).
select i.order_id from fct_order_items i left join fct_orders o on o.order_id = i.order_id where o.order_id is null
