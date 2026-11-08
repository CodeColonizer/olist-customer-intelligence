-- One row per real customer (customer_unique_id), based on delivered orders.
-- Includes RFM inputs: recency is measured from the day after the last
-- purchase in the dataset's analysis window.
drop table if exists dim_customers;
create table dim_customers as
with delivered as (
    select *
    from fct_orders
    where is_delivered = 1
),
snapshot as (
    select date(max(purchased_at), '+1 day') as snapshot_date
    from delivered
),
per_customer as (
    select
        customer_unique_id,
        min(purchased_at)          as first_order_at,
        max(purchased_at)          as last_order_at,
        count(*)                   as order_count,
        count(distinct purchase_date) as purchase_days,
        round(sum(order_value), 2) as total_spend,
        round(avg(order_value), 2) as avg_order_value,
        round(avg(review_score), 2) as avg_review_score
    from delivered
    group by customer_unique_id
),
home_state as (
    -- state of the customer's most recent order
    select customer_unique_id, customer_state
    from (
        select customer_unique_id, customer_state,
               row_number() over (partition by customer_unique_id
                                  order by purchased_at desc) as rn
        from delivered
    )
    where rn = 1
)
select
    p.customer_unique_id,
    h.customer_state,
    p.first_order_at,
    p.last_order_at,
    strftime('%Y-%m', p.first_order_at)                            as cohort_month,
    p.order_count,
    case when p.order_count > 1 then 1 else 0 end                  as is_repeat_customer,
    -- Same-day "repeat" orders are often one basket split across sellers,
    -- so a returning customer is one who bought on more than one day.
    p.purchase_days,
    case when p.purchase_days > 1 then 1 else 0 end                as is_returning_customer,
    p.total_spend,
    p.avg_order_value,
    p.avg_review_score,
    cast(julianday(s.snapshot_date) - julianday(date(p.last_order_at)) as integer)
                                                                   as recency_days
from per_customer p
join home_state h on h.customer_unique_id = p.customer_unique_id
cross join snapshot s;

create unique index idx_dc_customer on dim_customers(customer_unique_id);
