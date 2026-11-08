-- One row per customer (delivered orders) with the behavioural features used
-- for segmentation, plus rule-based RFM scores and segments.
--
-- RFM in this dataset: 97% of customers bought once, so Frequency barely
-- varies. Recency and Monetary are scored in quintiles (1 = worst, 5 = best);
-- Frequency is captured as "returning" (bought on more than one day).
drop table if exists mart_customer_features;
create table mart_customer_features as
with delivered as (
    select *
    from fct_orders
    where is_delivered = 1
),
behaviour as (
    select
        customer_unique_id,
        round(avg(delivery_days), 2)                       as avg_delivery_days,
        round(avg(is_late), 4)                             as late_order_rate,
        max(is_late)                                       as experienced_late,
        round(avg(coalesce(max_installments, 1)), 2)       as avg_installments,
        max(case when review_score <= 2 then 1 else 0 end) as gave_low_review,
        round(avg(freight_value / nullif(order_value, 0)), 4) as avg_freight_share
    from delivered
    group by customer_unique_id
),
top_category as (
    -- the category the customer spent most on
    select customer_unique_id, category
    from (
        select
            o.customer_unique_id,
            i.category,
            row_number() over (
                partition by o.customer_unique_id
                order by sum(i.price) desc, i.category
            ) as rn
        from fct_order_items i
        join delivered o on o.order_id = i.order_id
        group by o.customer_unique_id, i.category
    )
    where rn = 1
),
scored as (
    select
        c.customer_unique_id,
        c.customer_state,
        s.region,
        c.cohort_month,
        c.first_order_at,
        c.last_order_at,
        c.recency_days,
        c.order_count,
        c.purchase_days,
        c.is_returning_customer,
        c.total_spend,
        c.avg_order_value,
        c.avg_review_score,
        b.gave_low_review,
        b.avg_delivery_days,
        b.late_order_rate,
        b.experienced_late,
        b.avg_installments,
        b.avg_freight_share,
        t.category                                   as top_category,
        -- Quintile scores from percent_rank, so tied values always get the
        -- same score. Lower recency (more recent) = better score.
        min(5, 1 + cast(5 * percent_rank() over (order by c.recency_days desc) as integer))
                                                     as r_score,
        min(5, 1 + cast(5 * percent_rank() over (order by c.total_spend) as integer))
                                                     as m_score
    from dim_customers c
    join behaviour b      on b.customer_unique_id = c.customer_unique_id
    left join dim_states s on s.state_code = c.customer_state
    left join top_category t on t.customer_unique_id = c.customer_unique_id
)
select
    *,
    case
        when is_returning_customer = 1         then '1. Returning customers'
        when r_score >= 4 and m_score >= 4     then '2. Recent big spenders'
        when r_score >= 4                      then '3. Recent small spenders'
        when m_score >= 4                      then '4. Lapsing big spenders'
        else                                        '5. Lapsing small spenders'
    end as rfm_segment
from scored;

create unique index idx_mcf_customer on mart_customer_features(customer_unique_id);
