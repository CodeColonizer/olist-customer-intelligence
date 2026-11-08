-- Q10. How do customers pay?
select
    primary_payment_type,
    count(*)                                            as orders,
    round(100.0 * count(*) / sum(count(*)) over (), 1)  as pct_of_orders,
    round(avg(order_value), 2)                          as avg_order_value,
    round(avg(max_installments), 1)                     as avg_installments
from fct_orders
where is_delivered = 1 and primary_payment_type is not null
group by primary_payment_type
order by orders desc
