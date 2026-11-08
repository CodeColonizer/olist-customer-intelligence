-- Every customer in dim_customers has exactly one feature row and a segment.
select
    (select count(*) from dim_customers) as dim_n,
    (select count(*) from mart_customer_features where rfm_segment is not null) as mart_n
where (select count(*) from dim_customers)
   <> (select count(*) from mart_customer_features where rfm_segment is not null)
