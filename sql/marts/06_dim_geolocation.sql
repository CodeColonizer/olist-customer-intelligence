drop table if exists dim_geolocation;
create table dim_geolocation as
select * from stg_geolocation;

create unique index idx_dg_zip on dim_geolocation(zip_code_prefix);
