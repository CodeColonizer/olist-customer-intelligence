"""Segment customers with k-means clustering.

Input:  mart_customer_features (built by scripts/build.py)
Output: customer_segments table in the database (one row per customer),
        outputs/tables/cluster_selection.csv, outputs/charts/06_cluster_selection.png

Features (one row per customer, delivered orders):
  recency_days       days since last purchase
  total_spend        log-transformed, because spend is heavily right-skewed
  avg_review_score   missing reviews (0.6% of customers) filled with the median
  avg_delivery_days  how long their orders took to arrive
  avg_installments   how many instalments they pay in (a proxy for basket size
                     and financing behaviour)

Frequency is deliberately left out: 97% of customers bought once, so it carries
almost no information for clustering. It is covered by the RFM segments instead.

Usage:
    python scripts/segment_customers.py
"""
from pathlib import Path
import sqlite3

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score
from sklearn.preprocessing import StandardScaler

ROOT = Path(__file__).resolve().parents[1]
DB_PATH = ROOT / "data" / "olist.db"
TABLES_DIR = ROOT / "outputs" / "tables"
CHARTS_DIR = ROOT / "outputs" / "charts"

FEATURES = ["recency_days", "total_spend", "avg_review_score",
            "avg_delivery_days", "avg_installments"]
K_RANGE = range(2, 9)
CHOSEN_K = 5            # see docs/phase2_findings.md for why 5 rather than 3
SEED = 42
SILHOUETTE_SAMPLE = 15_000

BLUE, INK, INK_2, GRID, SURFACE = "#2a78d6", "#0b0b0b", "#52514e", "#e4e3df", "#fcfcfb"


def prepare(df: pd.DataFrame) -> np.ndarray:
    X = df[FEATURES].copy()
    X["total_spend"] = np.log1p(X["total_spend"])
    X["avg_review_score"] = X["avg_review_score"].fillna(X["avg_review_score"].median())
    return StandardScaler().fit_transform(X)


def compare_k(Xs: np.ndarray) -> pd.DataFrame:
    rng = np.random.default_rng(SEED)
    sample = rng.choice(len(Xs), SILHOUETTE_SAMPLE, replace=False)
    rows = []
    for k in K_RANGE:
        km = KMeans(n_clusters=k, n_init=10, random_state=SEED).fit(Xs)
        rows.append({
            "k": k,
            "inertia": round(km.inertia_, 0),
            "silhouette": round(silhouette_score(Xs[sample], km.labels_[sample]), 3),
        })
    return pd.DataFrame(rows)


def name_clusters(profile: pd.DataFrame) -> dict[int, str]:
    """Name clusters from their average profile rather than their label number,
    so names stay correct even if the algorithm numbers clusters differently."""
    names = {}
    remaining = list(profile.index)

    def take(cluster: int, name: str) -> None:
        names[cluster] = name
        remaining.remove(cluster)

    take(profile.loc[remaining, "avg_installments"].idxmax(), "High-value instalment buyers")
    take(profile.loc[remaining, "avg_delivery_days"].idxmax(), "Delivery-failure detractors")
    take(profile.loc[remaining, "avg_review_score"].idxmin(), "Unhappy despite good delivery")
    take(profile.loc[remaining, "recency_days"].idxmin(), "Recent satisfied one-timers")
    take(remaining[0], "Lapsed satisfied one-timers")
    return names


def chart_selection(sel: pd.DataFrame) -> None:
    plt.rcParams.update({"font.size": 10, "savefig.dpi": 150, "savefig.bbox": "tight"})
    fig, ax = plt.subplots(figsize=(10, 4))
    fig.patch.set_facecolor(SURFACE)
    ax.set_facecolor(SURFACE)
    ax.plot(sel["k"], sel["silhouette"], color=BLUE, linewidth=2, marker="o", markersize=6)
    chosen = sel.loc[sel["k"] == CHOSEN_K, "silhouette"].iloc[0]
    ax.annotate(f"Chosen: k = {CHOSEN_K}\n(clearer business segments)",
                (CHOSEN_K, chosen), xytext=(CHOSEN_K + 0.6, chosen + 0.035),
                color=INK_2, fontsize=9, arrowprops={"arrowstyle": "-", "color": INK_2})
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    for side in ("left", "bottom"):
        ax.spines[side].set_color(GRID)
    ax.grid(axis="y", color=GRID)
    ax.tick_params(colors=INK_2)
    ax.set_xlabel("Number of clusters (k)", color=INK_2)
    ax.set_ylim(0, sel["silhouette"].max() + 0.08)
    ax.set_title("Silhouette score by number of clusters", loc="left",
                 fontsize=13, fontweight="bold", color=INK, pad=22)
    ax.text(0, 1.02, "Higher = better-separated clusters (15,000-customer sample)",
            transform=ax.transAxes, color=INK_2, fontsize=9.5, va="bottom")
    fig.savefig(CHARTS_DIR / "06_cluster_selection.png")
    plt.close(fig)


def main() -> None:
    TABLES_DIR.mkdir(parents=True, exist_ok=True)
    CHARTS_DIR.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(DB_PATH) as con:
        df = pd.read_sql_query("select * from mart_customer_features", con)
        Xs = prepare(df)

        print("Comparing cluster counts...")
        sel = compare_k(Xs)
        sel.to_csv(TABLES_DIR / "cluster_selection.csv", index=False)
        print(sel.to_string(index=False))
        chart_selection(sel)

        km = KMeans(n_clusters=CHOSEN_K, n_init=10, random_state=SEED).fit(Xs)
        df["cluster"] = km.labels_
        profile = df.groupby("cluster")[FEATURES].mean()
        df["cluster_segment"] = df["cluster"].map(name_clusters(profile))

        out = df[["customer_unique_id", "cluster_segment"]]
        assert out["customer_unique_id"].is_unique
        assert out["cluster_segment"].notna().all()
        assert len(out) == len(df)
        out.to_sql("customer_segments", con, if_exists="replace", index=False)
        con.execute("create unique index if not exists idx_cs_customer "
                    "on customer_segments(customer_unique_id)")

    print(f"\nk = {CHOSEN_K} segments written to customer_segments:")
    print(df["cluster_segment"].value_counts().to_string())


if __name__ == "__main__":
    main()
