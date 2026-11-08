-- One row per seller in dim_sellers.
select seller_id, count(*) as n from dim_sellers group by seller_id having count(*) > 1
