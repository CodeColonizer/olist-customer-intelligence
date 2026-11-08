-- Q6. Which product categories drive revenue, and how well are they served?
-- Delivered orders only. An order can contain several categories, so order-level
-- metrics (late rate, review) are attached to every category in the order.
with cat_items as (
    select category, order_id, sum(price) as revenue, count(*) as items
    from fct_order_items
    where order_status = 'delivered'
    group by category, order_id
)
select
    c.category,
    count(*)                                         as orders,
    sum(c.items)                                     as items,
    round(sum(c.revenue), 2)                         as revenue,
    round(100.0 * sum(c.revenue) / sum(sum(c.revenue)) over (), 2) as revenue_share_pct,
    round(sum(c.revenue) / count(*), 2)              as revenue_per_order,
    round(100.0 * avg(o.is_late), 1)                 as late_pct,
    round(avg(o.review_score), 2)                    as avg_review_score
from cat_items c
join fct_orders o on o.order_id = c.order_id
group by c.category
order by revenue desc
limit 15
