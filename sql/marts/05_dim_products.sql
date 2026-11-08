drop table if exists dim_products;
create table dim_products as
select * from stg_products;

create unique index idx_dp_product on dim_products(product_id);
