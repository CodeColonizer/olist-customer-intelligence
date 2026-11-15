-- Repeat-purchase dataset: one row per customer; labelled rows have a full
-- 180-day window and a binary label; returns fall inside the window;
-- customers without a full window have no label.
select customer_unique_id
from mart_repeat_purchase
where (has_full_window = 1 and returned_180d not in (0, 1))
   or (has_full_window = 0 and returned_180d is not null)
   or (returned_180d = 1 and (days_to_return < 1 or days_to_return > 180))
   or (has_full_window = 1
       and first_date > date((select max(purchased_at) from fct_orders where is_delivered = 1), '-180 days'))
   or customer_unique_id in (
        select customer_unique_id from mart_repeat_purchase
        group by customer_unique_id having count(*) > 1)
