-- Modelling dataset for the repeat-purchase model: one row per customer.
--
-- Question: from what happened on a customer's FIRST purchase, can we predict
-- whether they come back and buy again on a later day within 180 days?
--
-- Leakage rules:
--   * features describe only the first purchase day (the "first basket")
--     and how that basket was delivered and reviewed;
--   * the label only counts orders on a LATER day (same-day split baskets are
--     not repeat purchases), excluding cancelled/unavailable orders;
--   * the label is only filled in for customers whose first purchase is at
--     least 180 days before the end of the data (last delivered purchase:
--     2018-08-29), so every labelled customer had a full 180-day window to
--     return. More recent customers (has_full_window = 0) have no label; the
--     trained model scores them instead.
drop table if exists mart_repeat_purchase;
create table mart_repeat_purchase as
with params as (
    select
        180 as window_days,
        date(max(purchased_at)) as data_end
    from fct_orders
    where is_delivered = 1
),
first_day as (
    select customer_unique_id, min(purchase_date) as first_date
    from fct_orders
    where is_delivered = 1
    group by customer_unique_id
),
basket_orders as (
    -- every delivered order the customer placed on their first purchase day
    select o.*
    from fct_orders o
    join first_day f
      on f.customer_unique_id = o.customer_unique_id
     and o.purchase_date = f.first_date
    where o.is_delivered = 1
),
largest_order as (
    -- payment details come from the biggest order in the basket
    select customer_unique_id, primary_payment_type, purchased_at
    from (
        select customer_unique_id, primary_payment_type, purchased_at,
               row_number() over (partition by customer_unique_id
                                  order by order_value desc, order_id) as rn
        from basket_orders
    )
    where rn = 1
),
basket_category as (
    select customer_unique_id, category
    from (
        select o.customer_unique_id, i.category,
               row_number() over (partition by o.customer_unique_id
                                  order by sum(i.price) desc, i.category) as rn
        from basket_orders o
        join fct_order_items i on i.order_id = o.order_id
        group by o.customer_unique_id, i.category
    )
    where rn = 1
),
basket as (
    select
        customer_unique_id,
        count(*)                                         as basket_orders,
        sum(item_count)                                  as basket_items,
        max(seller_count)                                as basket_sellers,
        round(sum(items_value), 2)                       as basket_value,
        round(sum(freight_value), 2)                     as basket_freight,
        max(coalesce(max_installments, 1))               as installments,
        round(avg(delivery_days), 2)                     as delivery_days,
        round(avg(estimated_delivery_days), 2)           as estimated_delivery_days,
        max(days_late)                                   as days_late,
        max(is_late)                                     as was_late,
        avg(review_score)                                as review_score,
        max(review_has_comment)                          as review_has_comment,
        max(customer_state)                              as customer_state
    from basket_orders
    group by customer_unique_id
),
later_orders as (
    -- valid orders on a later day than the first purchase
    select f.customer_unique_id, min(o.purchase_date) as second_date
    from first_day f
    join fct_orders o
      on o.customer_unique_id = f.customer_unique_id
     and o.purchase_date > f.first_date
     and o.order_status not in ('canceled', 'unavailable')
    group by f.customer_unique_id
)
select
    f.customer_unique_id,
    f.first_date,
    strftime('%Y-%m', f.first_date)                                as first_month,
    cast(strftime('%m', f.first_date) as integer)                  as first_month_number,
    cast(strftime('%w', l.purchased_at) as integer)                as first_weekday,
    cast(strftime('%H', l.purchased_at) as integer)                as first_hour,
    b.customer_state,
    s.region,
    coalesce(c.category, 'unknown')                                as category,
    l.primary_payment_type                                         as payment_type,
    b.installments,
    b.basket_orders,
    b.basket_items,
    b.basket_sellers,
    b.basket_value,
    b.basket_freight,
    round(b.basket_freight / nullif(b.basket_value + b.basket_freight, 0), 4) as freight_share,
    b.delivery_days,
    b.estimated_delivery_days,
    b.days_late,
    b.was_late,
    round(b.review_score, 2)                                       as review_score,
    case when b.review_score is null then 1 else 0 end             as review_missing,
    coalesce(b.review_has_comment, 0)                              as review_has_comment,
    case
        when julianday(f.first_date) <= julianday(p.data_end) - p.window_days
        then 1 else 0
    end                                                            as has_full_window,
    case
        when julianday(f.first_date) > julianday(p.data_end) - p.window_days then null
        when lo.second_date is not null
         and julianday(lo.second_date) - julianday(f.first_date) <= p.window_days
        then 1 else 0
    end                                                            as returned_180d,
    cast(julianday(lo.second_date) - julianday(f.first_date) as integer) as days_to_return
from first_day f
cross join params p
join basket b              on b.customer_unique_id = f.customer_unique_id
join largest_order l       on l.customer_unique_id = f.customer_unique_id
left join basket_category c on c.customer_unique_id = f.customer_unique_id
left join dim_states s     on s.state_code = b.customer_state
left join later_orders lo  on lo.customer_unique_id = f.customer_unique_id
where f.first_date >= '2017-01-01';                                -- skip the sparse 2016 launch period

create unique index idx_mrp_customer on mart_repeat_purchase(customer_unique_id);
