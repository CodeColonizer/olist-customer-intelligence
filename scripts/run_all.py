"""Run the full pipeline from raw CSVs to analysis outputs and Power BI files.

Steps:
  1. load_raw.py           CSVs -> SQLite raw tables
  2. build.py              staging views, marts, data quality tests
  3. segment_customers.py  k-means customer segments
  4. train_repeat_model.py repeat-purchase model, explainability, scores
  5. analyse_reviews.py    complaint themes from review text
  6. forecast_demand.py    category demand backtest and forecasts
  7. run_analysis.py       analysis tables and charts
  8. export_powerbi.py     star-schema CSVs for Power BI

Usage:
    python scripts/run_all.py
"""
from pathlib import Path
import subprocess
import sys

SCRIPTS = Path(__file__).resolve().parent
STEPS = [
    "load_raw.py",
    "build.py",
    "segment_customers.py",
    "train_repeat_model.py",
    "analyse_reviews.py",
    "forecast_demand.py",
    "run_analysis.py",
    "export_powerbi.py",
]


def main() -> None:
    for step in STEPS:
        print(f"\n=== {step} ===")
        result = subprocess.run([sys.executable, str(SCRIPTS / step)])
        if result.returncode != 0:
            raise SystemExit(f"\nStopped: {step} failed.")
    print("\nPipeline complete.")


if __name__ == "__main__":
    main()
