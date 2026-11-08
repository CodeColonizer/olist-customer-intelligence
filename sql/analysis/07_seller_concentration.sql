-- Q7. How concentrated is revenue among sellers?
with ranked as (
    select
        seller_id,
        revenue,
        ntile(10) over (order by revenue desc) as decile
    from dim_sellers
    where revenue > 0
)
select
    decile                                                      as seller_decile,
    count(*)                                                    as sellers,
    round(sum(revenue), 2)                                      as revenue,
    round(100.0 * sum(revenue) / sum(sum(revenue)) over (), 1)  as revenue_share_pct,
    round(100.0 * sum(sum(revenue)) over (order by decile)
          / sum(sum(revenue)) over (), 1)                       as cumulative_share_pct
from ranked
group by decile
order by decile
