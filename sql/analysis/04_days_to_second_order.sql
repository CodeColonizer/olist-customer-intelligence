-- Q4. For customers who return, how long until their second order?
with ranked as (
    select
        customer_unique_id,
        purchased_at,
        row_number() over (partition by customer_unique_id order by purchased_at) as n
    from fct_orders
    where is_delivered = 1
),
gaps as (
    select
        julianday(s.purchased_at) - julianday(f.purchased_at) as days_to_second
    from ranked f
    join ranked s on s.customer_unique_id = f.customer_unique_id and s.n = 2
    where f.n = 1
)
select
    case
        when days_to_second < 1   then '0. same day'
        when days_to_second <= 30 then '1. 1-30 days'
        when days_to_second <= 90 then '2. 31-90 days'
        when days_to_second <= 180 then '3. 91-180 days'
        else '4. 180+ days'
    end                                   as time_to_second_order,
    count(*)                              as customers,
    round(100.0 * count(*) / sum(count(*)) over (), 1) as pct
from gaps
group by 1
order by 1
