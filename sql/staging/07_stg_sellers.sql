drop view if exists stg_sellers;
create view stg_sellers as
select
    seller_id,
    seller_zip_code_prefix,
    lower(trim(seller_city))  as seller_city,
    upper(trim(seller_state)) as seller_state
from raw_sellers;
