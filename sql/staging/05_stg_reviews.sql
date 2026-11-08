-- 547 orders have more than one review. Keep the most recently answered
-- review per order so each order has at most one score.
drop view if exists stg_reviews;
create view stg_reviews as
with ranked as (
    select
        review_id,
        order_id,
        cast(review_score as integer)        as review_score,
        nullif(trim(review_comment_title), '')   as review_title,
        nullif(trim(review_comment_message), '') as review_message,
        datetime(review_creation_date)       as review_created_at,
        datetime(review_answer_timestamp)    as review_answered_at,
        row_number() over (
            partition by order_id
            order by review_answer_timestamp desc, review_creation_date desc, review_id
        ) as rn
    from raw_order_reviews
)
select
    review_id,
    order_id,
    review_score,
    review_title,
    review_message,
    case when review_message is not null then 1 else 0 end as has_comment,
    review_created_at,
    review_answered_at
from ranked
where rn = 1;
