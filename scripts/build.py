"""Build the cleaned data models and run the data quality tests.

Runs, in order:
  1. sql/staging/*.sql  -> cleaned views (stg_*)
  2. sql/marts/*.sql    -> analysis tables (fct_*, dim_*)
  3. sql/tests/*.sql    -> each test returns failing rows; 0 rows = pass

Exits with a non-zero status if any test fails.

Usage:
    python scripts/build.py
"""
from pathlib import Path
import sqlite3
import sys

ROOT = Path(__file__).resolve().parents[1]
DB_PATH = ROOT / "data" / "olist.db"
SQL_DIR = ROOT / "sql"


def run_scripts(con: sqlite3.Connection, folder: str) -> None:
    for path in sorted((SQL_DIR / folder).glob("*.sql")):
        con.executescript(path.read_text())
        print(f"  built  {folder}/{path.name}")


def run_tests(con: sqlite3.Connection) -> int:
    failures = 0
    for path in sorted((SQL_DIR / "tests").glob("*.sql")):
        rows = con.execute(path.read_text()).fetchall()
        status = "PASS" if not rows else f"FAIL ({len(rows)} rows)"
        failures += bool(rows)
        print(f"  {status:<14} {path.stem}")
    return failures


def main() -> None:
    if not DB_PATH.exists():
        raise SystemExit("Database not found. Run: python scripts/load_raw.py")
    with sqlite3.connect(DB_PATH) as con:
        print("Staging:")
        run_scripts(con, "staging")
        print("Marts:")
        run_scripts(con, "marts")
        print("Tests:")
        failures = run_tests(con)
    if failures:
        print(f"\n{failures} test(s) failed.")
        sys.exit(1)
    print("\nAll tests passed.")


if __name__ == "__main__":
    main()
