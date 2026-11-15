-- Review comments mart: one row per order (review_id is not unique in the source:
-- a few reviews are attached to several orders), every row has comment text and
-- a valid score, and the delivery-timing flag is only set for delivered orders.
select order_id
from mart_review_comments
where review_message is null
   or review_score not between 1 and 5
   or (is_delivered = 0 and answered_before_delivery is not null)
   or (is_delivered = 1 and answered_before_delivery not in (0, 1))
   or order_id in (
        select order_id from mart_review_comments
        group by order_id having count(*) > 1)
