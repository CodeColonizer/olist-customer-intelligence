-- One row per order, with typed timestamps and delivery timing fields.
-- Delivery fields are only populated for delivered orders that have a
-- customer delivery date (8 delivered orders are missing one).
drop view if exists stg_orders;
create view stg_orders as
select
    order_id,
    customer_id,
    order_status,
    datetime(order_purchase_timestamp)        as purchased_at,
    datetime(order_approved_at)               as approved_at,
    datetime(order_delivered_carrier_date)    as delivered_to_carrier_at,
    datetime(order_delivered_customer_date)   as delivered_at,
    date(order_estimated_delivery_date)       as estimated_delivery_date,
    date(order_purchase_timestamp)            as purchase_date,
    strftime('%Y-%m', order_purchase_timestamp) as purchase_month,
    case
        when order_status = 'delivered' and order_delivered_customer_date is not null
        then 1 else 0
    end                                       as is_delivered,
    case
        when order_status = 'delivered' and order_delivered_customer_date is not null
        then round(julianday(order_delivered_customer_date)
                   - julianday(order_purchase_timestamp), 2)
    end                                       as delivery_days,
    case
        when order_status = 'delivered' and order_delivered_customer_date is not null
        then round(julianday(order_estimated_delivery_date)
                   - julianday(order_purchase_timestamp), 2)
    end                                       as estimated_delivery_days,
    case
        when order_status = 'delivered' and order_delivered_customer_date is not null
        then cast(julianday(date(order_delivered_customer_date))
                  - julianday(date(order_estimated_delivery_date)) as integer)
    end                                       as days_late,
    case
        when order_status = 'delivered' and order_delivered_customer_date is not null
        then case when date(order_delivered_customer_date)
                       > date(order_estimated_delivery_date) then 1 else 0 end
    end                                       as is_late
from raw_orders;
