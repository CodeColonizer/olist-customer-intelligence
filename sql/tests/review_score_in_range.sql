-- Review scores are between 1 and 5.
select order_id, review_score from fct_orders where review_score is not null and review_score not between 1 and 5
