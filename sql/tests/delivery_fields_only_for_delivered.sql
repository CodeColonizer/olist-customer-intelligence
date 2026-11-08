-- Delivery metrics exist only for delivered orders, and all delivered orders with a date have them.
select order_id from fct_orders
where (is_delivered = 0 and delivery_days is not null)
   or (is_delivered = 1 and (delivery_days is null or is_late is null))
