-- Prices, freight and order values are never negative.
select order_id from fct_orders where items_value < 0 or freight_value < 0 or order_value < 0
