"""Run every query in sql/analysis, save the results and draw the charts.

Outputs:
  outputs/tables/<query>.csv   one CSV per analysis query
  outputs/charts/*.png         charts used in the README and findings

Usage:
    python scripts/run_analysis.py
"""
from pathlib import Path
import sqlite3

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.ticker as mtick
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DB_PATH = ROOT / "data" / "olist.db"
ANALYSIS_DIR = ROOT / "sql" / "analysis"
TABLES_DIR = ROOT / "outputs" / "tables"
CHARTS_DIR = ROOT / "outputs" / "charts"

# Chart styling: one primary hue, one highlight hue, recessive axes.
BLUE = "#2a78d6"
RED = "#e34948"
ORANGE = "#eb6834"
INK = "#0b0b0b"
INK_2 = "#52514e"
GRID = "#e4e3df"
SURFACE = "#fcfcfb"

plt.rcParams.update({
    "figure.facecolor": SURFACE,
    "axes.facecolor": SURFACE,
    "axes.edgecolor": GRID,
    "axes.labelcolor": INK_2,
    "axes.titlecolor": INK,
    "axes.titlesize": 13,
    "axes.titleweight": "bold",
    "axes.titlelocation": "left",
    "axes.spines.top": False,
    "axes.spines.right": False,
    "axes.grid": True,
    "grid.color": GRID,
    "grid.linewidth": 0.8,
    "xtick.color": INK_2,
    "ytick.color": INK_2,
    "font.size": 10,
    "savefig.dpi": 150,
    "savefig.bbox": "tight",
})


def run_queries(con: sqlite3.Connection) -> dict[str, pd.DataFrame]:
    results = {}
    for path in sorted(ANALYSIS_DIR.glob("*.sql")):
        df = pd.read_sql_query(path.read_text(), con)
        df.to_csv(TABLES_DIR / f"{path.stem}.csv", index=False)
        results[path.stem] = df
        print(f"  saved  outputs/tables/{path.stem}.csv ({len(df)} rows)")
    return results


def subtitle(ax, text: str) -> None:
    ax.text(0, 1.02, text, transform=ax.transAxes, color=INK_2, fontsize=9.5, va="bottom")


def chart_monthly_revenue(df: pd.DataFrame) -> None:
    fig, ax = plt.subplots(figsize=(10, 4.2))
    x = range(len(df))
    ax.plot(x, df["revenue"] / 1000, color=BLUE, linewidth=2, marker="o", markersize=4)
    ax.set_xticks(list(x)[::2])
    ax.set_xticklabels(df["purchase_month"].iloc[::2], rotation=0)
    ax.yaxis.set_major_formatter(mtick.StrMethodFormatter("R${x:,.0f}k"))
    ax.set_ylim(0, 1100)
    ax.grid(axis="x", visible=False)
    peak = df["revenue"].idxmax()
    ax.annotate("Black Friday\n(Nov 2017)", (peak, df.loc[peak, "revenue"] / 1000),
                xytext=(peak - 4.6, 880),
                color=INK_2, fontsize=9, arrowprops={"arrowstyle": "-", "color": INK_2})
    ax.set_title("Monthly revenue, delivered orders", pad=22)
    subtitle(ax, "Product revenue excluding freight, Jan 2017 to Aug 2018")
    fig.savefig(CHARTS_DIR / "01_monthly_revenue.png")
    plt.close(fig)


def chart_delivery_vs_reviews(df: pd.DataFrame) -> None:
    labels = [s.split(". ", 1)[1] for s in df["delivery_timing"]]
    colors = [RED if "late" in s else BLUE for s in labels]
    fig, ax = plt.subplots(figsize=(10, 4.2))
    bars = ax.bar(labels, df["low_review_pct"], color=colors, width=0.6)
    for bar, v in zip(bars, df["low_review_pct"]):
        ax.text(bar.get_x() + bar.get_width() / 2, v + 1.5, f"{v:.0f}%",
                ha="center", color=INK, fontsize=9.5)
    ax.yaxis.set_major_formatter(mtick.PercentFormatter(decimals=0))
    ax.set_ylim(0, 90)
    ax.grid(axis="x", visible=False)
    ax.set_title("Share of 1-2 star reviews by delivery timing", pad=22)
    subtitle(ax, "Delivered orders with a review; timing compared with the estimated delivery date")
    fig.savefig(CHARTS_DIR / "02_low_reviews_by_delivery.png")
    plt.close(fig)


def chart_seller_concentration(df: pd.DataFrame) -> None:
    fig, ax = plt.subplots(figsize=(10, 4.2))
    labels = [f"Top {d * 10}%" for d in df["seller_decile"]]
    ax.plot(labels, df["cumulative_share_pct"], color=BLUE, linewidth=2, marker="o", markersize=5)
    for i in (0, 2):
        v = df["cumulative_share_pct"].iloc[i]
        ax.text(i, v - 7, f"{v:.0f}%", ha="center", color=INK, fontsize=9.5)
    ax.yaxis.set_major_formatter(mtick.PercentFormatter(decimals=0))
    ax.set_ylim(0, 105)
    ax.grid(axis="x", visible=False)
    ax.set_title("Cumulative share of revenue by seller rank", pad=22)
    subtitle(ax, "Sellers ranked by revenue on delivered orders, grouped into deciles")
    fig.savefig(CHARTS_DIR / "03_seller_concentration.png")
    plt.close(fig)


def chart_state_delivery(df: pd.DataFrame) -> None:
    top = df.sort_values("orders", ascending=False).head(15).sort_values("late_pct")
    fig, ax = plt.subplots(figsize=(10, 5))
    colors = [RED if v >= 10 else BLUE for v in top["late_pct"]]
    ax.barh(top["customer_state"], top["late_pct"], color=colors, height=0.6)
    for y, (v, r) in enumerate(zip(top["late_pct"], top["avg_review_score"])):
        ax.text(v + 0.3, y, f"{v:.1f}%  (avg review {r:.2f})", va="center", color=INK_2, fontsize=9)
    ax.xaxis.set_major_formatter(mtick.PercentFormatter(decimals=0))
    ax.set_xlim(0, top["late_pct"].max() * 1.45)
    ax.grid(axis="y", visible=False)
    ax.set_title("Late delivery rate in the 15 largest customer states", pad=22)
    subtitle(ax, "Red = 10% or more of orders delivered after the estimated date")
    fig.savefig(CHARTS_DIR / "04_late_rate_by_state.png")
    plt.close(fig)


def chart_categories(df: pd.DataFrame) -> None:
    top = df.head(10).iloc[::-1]
    fig, ax = plt.subplots(figsize=(10, 4.8))
    ax.barh(top["category"].str.replace("_", " "), top["revenue"] / 1000, color=BLUE, height=0.6)
    for y, (v, s) in enumerate(zip(top["revenue"] / 1000, top["revenue_share_pct"])):
        ax.text(v + 10, y, f"{s:.1f}%", va="center", color=INK_2, fontsize=9)
    ax.xaxis.set_major_formatter(mtick.StrMethodFormatter("R${x:,.0f}k"))
    ax.grid(axis="y", visible=False)
    ax.set_title("Top 10 categories by revenue", pad=22)
    subtitle(ax, "Delivered orders; labels show share of total revenue")
    fig.savefig(CHARTS_DIR / "05_top_categories.png")
    plt.close(fig)


def chart_share_comparison(df: pd.DataFrame, label_col: str, title: str,
                           sub: str, filename: str) -> None:
    """Grouped bars: each segment's share of customers vs share of revenue."""
    d = df.iloc[::-1].reset_index(drop=True)
    labels = [s.split(". ", 1)[-1] for s in d[label_col]]
    y = range(len(d))
    h = 0.36
    fig, ax = plt.subplots(figsize=(10, 4.8))
    ax.barh([i + h / 2 + 0.02 for i in y], d["customer_share_pct"], height=h,
            color=BLUE, label="Share of customers")
    ax.barh([i - h / 2 - 0.02 for i in y], d["revenue_share_pct"], height=h,
            color=ORANGE, label="Share of revenue")
    for i in y:
        ax.text(d["customer_share_pct"][i] + 0.5, i + h / 2 + 0.02,
                f"{d['customer_share_pct'][i]:.1f}%", va="center", color=INK_2, fontsize=9)
        ax.text(d["revenue_share_pct"][i] + 0.5, i - h / 2 - 0.02,
                f"{d['revenue_share_pct'][i]:.1f}%", va="center", color=INK_2, fontsize=9)
    ax.set_yticks(list(y))
    ax.set_yticklabels(labels)
    ax.xaxis.set_major_formatter(mtick.PercentFormatter(decimals=0))
    ax.set_xlim(0, max(d["customer_share_pct"].max(), d["revenue_share_pct"].max()) * 1.15)
    ax.grid(axis="y", visible=False)
    ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.07), ncol=2, frameon=False)
    ax.set_title(title, pad=22)
    subtitle(ax, sub)
    fig.savefig(CHARTS_DIR / filename)
    plt.close(fig)


def main() -> None:
    if not DB_PATH.exists():
        raise SystemExit("Database not found. Run load_raw.py and build.py first.")
    TABLES_DIR.mkdir(parents=True, exist_ok=True)
    CHARTS_DIR.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(DB_PATH) as con:
        print("Queries:")
        r = run_queries(con)
    print("Charts:")
    chart_monthly_revenue(r["01_monthly_growth"])
    chart_delivery_vs_reviews(r["05_delivery_vs_reviews"])
    chart_seller_concentration(r["07_seller_concentration"])
    chart_state_delivery(r["09_state_delivery"])
    chart_categories(r["06_category_performance"])
    chart_share_comparison(
        r["11_rfm_segments"], "rfm_segment", "RFM segments: customers vs revenue",
        "Recent = last order within ~6 months; big spenders = top 40% by total spend",
        "07_rfm_segments.png")
    chart_share_comparison(
        r["12_customer_clusters"], "cluster_segment", "Behavioural segments: customers vs revenue",
        "k-means clustering on recency, spend, reviews, delivery time and instalments",
        "08_customer_clusters.png")
    for p in sorted(CHARTS_DIR.glob("*.png")):
        print(f"  saved  outputs/charts/{p.name}")


if __name__ == "__main__":
    main()
