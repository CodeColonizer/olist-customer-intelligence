-- Q3. How many customers come back, and how much revenue do they bring?
-- repeat = more than one order; returning = orders on more than one day
-- (excludes baskets split into several orders on the same day).
select
    count(*)                                                    as customers,
    sum(is_repeat_customer)                                     as repeat_customers,
    round(100.0 * avg(is_repeat_customer), 2)                   as repeat_customer_pct,
    sum(is_returning_customer)                                  as returning_customers,
    round(100.0 * avg(is_returning_customer), 2)                as returning_customer_pct,
    round(sum(case when is_repeat_customer = 1 then total_spend end), 2) as repeat_customer_spend,
    round(100.0 * sum(case when is_repeat_customer = 1 then total_spend end)
          / sum(total_spend), 2)                                as repeat_spend_share_pct,
    round(avg(case when is_repeat_customer = 1 then total_spend end), 2) as avg_spend_repeat,
    round(avg(case when is_repeat_customer = 0 then total_spend end), 2) as avg_spend_one_time
from dim_customers
