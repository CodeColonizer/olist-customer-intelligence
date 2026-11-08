-- Every order has a customer and a purchase timestamp.
select order_id from fct_orders where customer_unique_id is null or purchased_at is null
