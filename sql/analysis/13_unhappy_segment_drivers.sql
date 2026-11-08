-- Q13. Customers who were unhappy despite good delivery: which product
-- categories are over-represented? Compares each category's share of this segment
-- with its share of all customers (index > 100 = over-represented).
with seg as (
    select f.top_category, s.cluster_segment
    from mart_customer_features f
    join customer_segments s on s.customer_unique_id = f.customer_unique_id
),
counts as (
    select
        top_category,
        count(*)                                                        as all_customers,
        sum(case when cluster_segment = 'Unhappy despite good delivery' then 1 else 0 end) as unhappy_customers
    from seg
    group by top_category
)
select
    top_category,
    all_customers,
    unhappy_customers,
    round(100.0 * unhappy_customers / all_customers, 1)                 as unhappy_rate_pct,
    round(100.0 * (1.0 * unhappy_customers / (select sum(unhappy_customers) from counts))
          / (1.0 * all_customers / (select sum(all_customers) from counts)), 0) as over_representation_index
from counts
where all_customers >= 500   -- ignore small categories
order by unhappy_rate_pct desc
limit 15
