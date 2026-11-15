-- Seller scorecard: one row per established seller, scores between 0 and 100,
-- every seller has a tier, and all rates are valid proportions.
select seller_id
from mart_seller_scorecard
where score not between 0 and 100
   or tier is null
   or delivered_orders < 30
   or late_delivery_rate not between 0 and 1
   or late_dispatch_rate not between 0 and 1
   or low_review_rate not between 0 and 1
   or cancellation_rate not between 0 and 1
   or seller_id in (select seller_id from mart_seller_scorecard
                    group by seller_id having count(*) > 1)
