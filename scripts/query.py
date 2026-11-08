"""Run ad-hoc SQL against the project database and print the results.

Usage:
    python scripts/query.py "select count(*) from fct_orders"
    python scripts/query.py path/to/file.sql
"""
from pathlib import Path
import sqlite3
import sys

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DB_PATH = ROOT / "data" / "olist.db"


def main() -> None:
    if len(sys.argv) != 2:
        raise SystemExit(__doc__)
    arg = sys.argv[1]
    # A .sql file holds one statement; inline text may hold several separated by ';'.
    statements = [Path(arg).read_text()] if arg.endswith(".sql") else [
        s.strip() for s in arg.split(";") if s.strip()
    ]
    pd.set_option("display.width", 200)
    pd.set_option("display.max_columns", 30)
    with sqlite3.connect(DB_PATH) as con:
        for statement in statements:
            print(pd.read_sql_query(statement, con).to_string(index=False))
            print()


if __name__ == "__main__":
    main()
