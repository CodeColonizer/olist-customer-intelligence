-- One row per customer in dim_customers.
select customer_unique_id, count(*) as n from dim_customers group by customer_unique_id having count(*) > 1
