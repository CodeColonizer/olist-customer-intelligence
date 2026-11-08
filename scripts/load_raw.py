"""Load the raw Olist CSV files into a local SQLite database.

Each CSV becomes a `raw_<name>` table, loaded as-is (no cleaning) so the
raw layer always matches the source files. Cleaning happens in the SQL
staging layer (see sql/staging).

Usage:
    python scripts/load_raw.py
"""
from pathlib import Path
import sqlite3

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = ROOT / "data" / "raw"
DB_PATH = ROOT / "data" / "olist.db"

# source file -> raw table name
FILES = {
    "olist_customers_dataset.csv": "raw_customers",
    "olist_geolocation_dataset.csv": "raw_geolocation",
    "olist_order_items_dataset.csv": "raw_order_items",
    "olist_order_payments_dataset.csv": "raw_order_payments",
    "olist_order_reviews_dataset.csv": "raw_order_reviews",
    "olist_orders_dataset.csv": "raw_orders",
    "olist_products_dataset.csv": "raw_products",
    "olist_sellers_dataset.csv": "raw_sellers",
    "product_category_name_translation.csv": "raw_category_translation",
}

# Zip code prefixes have leading zeros, so they must stay text.
TEXT_COLUMNS = {
    "customer_zip_code_prefix": str,
    "seller_zip_code_prefix": str,
    "geolocation_zip_code_prefix": str,
}


def main() -> None:
    missing = [f for f in FILES if not (RAW_DIR / f).exists()]
    if missing:
        raise SystemExit(
            "Missing raw files in data/raw: " + ", ".join(missing)
            + "\nDownload the Olist dataset from Kaggle (see README)."
        )

    DB_PATH.unlink(missing_ok=True)
    with sqlite3.connect(DB_PATH) as con:
        for filename, table in FILES.items():
            df = pd.read_csv(RAW_DIR / filename, dtype=TEXT_COLUMNS)
            df.to_sql(table, con, index=False)
            print(f"{table:<26} {len(df):>9,} rows")
    print(f"\nDatabase written to {DB_PATH.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
