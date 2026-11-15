-- Q16. What do unhappy customers complain about? Share of 1-2 star review comments
-- (delivered orders) in each unhappy segment that mention each theme. Themes come
-- from scripts/analyse_reviews.py; a comment can mention several themes, so each
-- group also gets an "Any ..." row counting comments that mention at least one of
-- its themes, plus an overall "Any theme" row.
-- written_before_delivery_pct: share of those comments submitted before the
-- order's recorded delivery date, in the "good delivery" segment.
with complaints as (
    select c.order_id, s.cluster_segment, c.answered_before_delivery
    from mart_review_comments c
    join customer_segments s on s.customer_unique_id = c.customer_unique_id
    where c.review_score <= 2
      and c.is_delivered = 1
      and s.cluster_segment in ('Delivery-failure detractors', 'Unhappy despite good delivery')
),
totals as (
    select
        sum(case when cluster_segment = 'Delivery-failure detractors' then 1 else 0 end)   as n_delivery,
        sum(case when cluster_segment = 'Unhappy despite good delivery' then 1 else 0 end) as n_good
    from complaints
),
mentions as (
    -- one row per comment per theme, plus one per comment per group and overall
    select distinct c.order_id, c.cluster_segment, c.answered_before_delivery,
           t.theme_group, t.theme
    from complaints c
    join review_themes t on t.order_id = c.order_id
    union
    select distinct c.order_id, c.cluster_segment, c.answered_before_delivery,
           t.theme_group, 'Any ' || lower(substr(t.theme_group, 4)) || ' issue'
    from complaints c
    join review_themes t on t.order_id = c.order_id
    union
    select distinct c.order_id, c.cluster_segment, c.answered_before_delivery,
           '5. All', 'Any theme'
    from complaints c
    join review_themes t on t.order_id = c.order_id
),
theme_counts as (
    select
        theme_group,
        theme,
        sum(case when cluster_segment = 'Delivery-failure detractors' then 1 else 0 end)   as delivery_mentions,
        sum(case when cluster_segment = 'Unhappy despite good delivery' then 1 else 0 end) as good_mentions,
        sum(case when cluster_segment = 'Unhappy despite good delivery'
                 then answered_before_delivery else 0 end)                               as good_before_delivery
    from mentions
    group by theme_group, theme
)
select
    theme_group,
    theme,
    delivery_mentions                                                   as delivery_failure_comments,
    round(100.0 * delivery_mentions / n_delivery, 1)                    as delivery_failure_pct,
    good_mentions                                                       as good_delivery_comments,
    round(100.0 * good_mentions / n_good, 1)                            as good_delivery_pct,
    round(100.0 * good_before_delivery / nullif(good_mentions, 0), 1)   as good_delivery_written_before_delivery_pct
from theme_counts
cross join totals
order by theme_group, theme like 'Any %', good_delivery_pct desc
