-- Payments rolled up to one row per order.
-- primary_payment_type = the method that covered the largest share of the order.
drop view if exists stg_payments;
create view stg_payments as
with ranked as (
    select
        order_id,
        payment_type,
        payment_installments,
        payment_value,
        row_number() over (
            partition by order_id
            order by payment_value desc, payment_sequential
        ) as rn
    from raw_order_payments
)
select
    order_id,
    round(sum(payment_value), 2)                     as payment_value,
    count(*)                                         as payment_count,
    max(payment_installments)                        as max_installments,
    max(case when rn = 1 then payment_type end)      as primary_payment_type
from ranked
group by order_id;
