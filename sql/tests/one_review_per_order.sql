-- Deduplicated reviews leave at most one review per order.
select order_id, count(*) as n from stg_reviews group by order_id having count(*) > 1
