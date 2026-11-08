-- Item revenue in fct_orders reconciles to the raw order items (within 1 BRL).
select (select round(sum(price), 2) from raw_order_items) as raw_items,
       (select round(sum(items_value), 2) from fct_orders) as fct_items
where abs((select sum(price) from raw_order_items) - (select sum(items_value) from fct_orders)) > 1
