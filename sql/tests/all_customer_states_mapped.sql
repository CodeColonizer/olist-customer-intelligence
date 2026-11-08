-- Every customer state maps to a region in dim_states.
select distinct customer_state from mart_customer_features where region is null
