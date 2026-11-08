"""Export a star-schema data model for the Power BI dashboard.

Writes CSV files to powerbi/data/ (git-ignored; regenerate with this script):

  fact_orders.csv       one row per order
  fact_order_items.csv  one row per order item
  dim_customers.csv     one row per customer, with RFM and k-means segments
  dim_sellers.csv       one row per seller, with performance metrics
  dim_products.csv      one row per product
  dim_states.csv        one row per Brazilian state, with region
  dim_date.csv          one row per calendar day (mark as date table in Power BI)

See docs/powerbi_guide.md for relationships, measures and page layouts.

Usage:
    python scripts/export_powerbi.py
"""
from pathlib import Path
import sqlite3

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DB_PATH = ROOT / "data" / "olist.db"
OUT_DIR = ROOT / "powerbi" / "data"

QUERIES = {
    "fact_orders": """
        select
            order_id,
            customer_unique_id,
            customer_state,
            order_status,
            purchase_date,
            purchase_month,
            item_count,
            seller_count,
            items_value,
            freight_value,
            order_value,
            payment_value,
            primary_payment_type,
            max_installments,
            is_delivered,
            delivery_days,
            estimated_delivery_days,
            days_late,
            is_late,
            case
                when is_delivered = 0 then null
                when days_late <= -10 then '1. 10+ days early'
                when days_late <= -1  then '2. 1-9 days early'
                when days_late = 0    then '3. On the estimated day'
                when days_late <= 3   then '4. 1-3 days late'
                when days_late <= 7   then '5. 4-7 days late'
                else '6. 8+ days late'
            end as delivery_timing,
            review_score,
            case when review_score is null then null
                 when review_score <= 2 then 1 else 0 end as is_low_review,
            case when purchase_month between '2017-01' and '2018-08'
                 then 1 else 0 end as in_trend_window
        from fct_orders
    """,
    "fact_order_items": """
        select
            order_id,
            order_item_id,
            product_id,
            seller_id,
            category,
            order_status,
            case when order_status = 'delivered' then 1 else 0 end as is_delivered,
            price,
            freight_value,
            item_total
        from fct_order_items
    """,
    "dim_customers": """
        select
            f.customer_unique_id,
            f.customer_state       as home_state,
            f.region               as home_region,
            f.cohort_month,
            date(f.first_order_at) as first_order_date,
            date(f.last_order_at)  as last_order_date,
            f.recency_days,
            f.order_count,
            f.purchase_days,
            f.is_returning_customer,
            f.total_spend,
            f.avg_order_value,
            f.avg_review_score,
            f.gave_low_review,
            f.avg_delivery_days,
            f.experienced_late,
            f.avg_installments,
            f.top_category,
            f.r_score,
            f.m_score,
            f.rfm_segment,
            s.cluster_segment
        from mart_customer_features f
        left join customer_segments s on s.customer_unique_id = f.customer_unique_id

        union all

        -- customers whose orders were never delivered (cancelled, unavailable,
        -- in transit) still need a row so every order links to a customer
        select
            o.customer_unique_id,
            max(o.customer_state), max(st.region), null, null, null, null,
            0, 0, 0, 0, null, null, null, null, null, null, null, null, null,
            'No delivered orders', 'No delivered orders'
        from fct_orders o
        left join dim_states st on st.state_code = o.customer_state
        where o.customer_unique_id not in (select customer_unique_id from mart_customer_features)
        group by o.customer_unique_id
    """,
    "dim_sellers": """
        select
            d.*,
            s.state_name as seller_state_name,
            s.region     as seller_region,
            case when d.order_count >= 30 then 1 else 0 end as is_established
        from dim_sellers d
        left join dim_states s on s.state_code = d.seller_state
    """,
    "dim_products": "select * from dim_products",
    "dim_states": """
        select
            state_code,
            state_name,
            region,
            state_name || ', Brazil' as map_location
        from dim_states
    """,
}


def tidy_integers(df: pd.DataFrame) -> pd.DataFrame:
    """Store whole-number columns as integers (1 rather than 1.0), keeping blanks."""
    for col in df.select_dtypes("float").columns:
        values = df[col].dropna()
        if len(values) and (values % 1 == 0).all():
            df[col] = df[col].astype("Int64")
    return df


def build_date_table(con: sqlite3.Connection) -> pd.DataFrame:
    start, end = con.execute(
        "select min(purchase_date), max(purchase_date) from fct_orders").fetchone()
    # whole years, so time intelligence (e.g. same period last year) works
    dates = pd.date_range(f"{start[:4]}-01-01", f"{end[:4]}-12-31", freq="D")
    return pd.DataFrame({
        "date": dates.strftime("%Y-%m-%d"),
        "year": dates.year,
        "quarter": "Q" + dates.quarter.astype(str),
        "month_number": dates.month,
        "month_name": dates.strftime("%b"),
        "year_month": dates.strftime("%Y-%m"),
        "weekday_number": dates.dayofweek + 1,
        "weekday_name": dates.strftime("%a"),
        "is_weekend": (dates.dayofweek >= 5).astype(int),
        "in_trend_window": ((dates >= "2017-01-01") & (dates <= "2018-08-31")).astype(int),
    })


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(DB_PATH) as con:
        missing = {"customer_segments", "mart_customer_features"} - {
            r[0] for r in con.execute("select name from sqlite_master where type='table'")}
        if missing:
            raise SystemExit("Run build.py and segment_customers.py first.")
        for name, sql in QUERIES.items():
            df = tidy_integers(pd.read_sql_query(sql, con))
            df.to_csv(OUT_DIR / f"{name}.csv", index=False)
            print(f"  {name:<18} {len(df):>8,} rows")
        dates = build_date_table(con)
    dates.to_csv(OUT_DIR / "dim_date.csv", index=False)
    print(f"  {'dim_date':<18} {len(dates):>8,} rows")
    print(f"\nPower BI files written to {OUT_DIR.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
