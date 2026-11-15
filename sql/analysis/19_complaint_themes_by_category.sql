-- Q19. For customers unhappy despite good delivery, what goes wrong in each
-- category? Share of 1-2 star comments (delivered orders) mentioning each
-- order-accuracy and product theme, by the order's main category (categories
-- with 150+ such comments). Themes come from scripts/analyse_reviews.py.
with complaints as (
    select c.order_id, c.category
    from mart_review_comments c
    join customer_segments s on s.customer_unique_id = c.customer_unique_id
    where c.review_score <= 2
      and c.is_delivered = 1
      and s.cluster_segment = 'Unhappy despite good delivery'
),
flags as (
    select
        c.order_id,
        c.category,
        max(case when t.theme = 'Items or parts missing' then 1 else 0 end)           as missing_items,
        max(case when t.theme = 'Wrong item sent' then 1 else 0 end)                  as wrong_item,
        max(case when t.theme = 'Defective or damaged' then 1 else 0 end)             as defective,
        max(case when t.theme = 'Poor quality or not as described' then 1 else 0 end) as poor_quality
    from complaints c
    left join review_themes t on t.order_id = c.order_id
    group by c.order_id, c.category
)
select
    category,
    count(*)                                        as complaints,
    round(100.0 * avg(missing_items), 1)            as missing_items_pct,
    round(100.0 * avg(wrong_item), 1)               as wrong_item_pct,
    round(100.0 * avg(defective), 1)                as defective_pct,
    round(100.0 * avg(poor_quality), 1)             as poor_quality_pct,
    case
        when max(avg(missing_items), avg(wrong_item), avg(defective), avg(poor_quality)) = avg(missing_items) then 'Items or parts missing'
        when max(avg(missing_items), avg(wrong_item), avg(defective), avg(poor_quality)) = avg(wrong_item)    then 'Wrong item sent'
        when max(avg(missing_items), avg(wrong_item), avg(defective), avg(poor_quality)) = avg(defective)     then 'Defective or damaged'
        else 'Poor quality or not as described'
    end                                             as top_theme
from flags
group by category
having count(*) >= 150
order by complaints desc
