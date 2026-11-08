-- customer_id is generated per order; customer_unique_id identifies the person.
-- Person-level analysis (repeat purchases, lifetime value) uses customer_unique_id.
drop view if exists stg_customers;
create view stg_customers as
select
    customer_id,
    customer_unique_id,
    customer_zip_code_prefix,
    lower(trim(customer_city))  as customer_city,
    upper(trim(customer_state)) as customer_state
from raw_customers;
