"""Predict which first-time customers will buy again within 180 days.

Input:  mart_repeat_purchase (built by scripts/build.py)
Output: outputs/tables/model_*.csv, outputs/charts/09-10_*.png and the
        repeat_purchase_scores table (scores for recent customers whose
        180-day window has not finished yet)

Design:
  * Time-based split: train on customers whose first purchase was Jan-Sep 2017,
    test on Oct 2017 - Mar 2018. This mimics real use (train on the past,
    predict the future) and avoids leaking future patterns into training.
  * Features describe only the first purchase day: basket, payment, delivery
    experience and review. See sql/marts/09_mart_repeat_purchase.sql.
  * Models: a no-skill baseline, logistic regression and gradient boosting.
    The regularisation strength of the logistic regression is chosen by
    cross-validation on the training period only.
  * Explainability: permutation importance on the test period (how much the
    test AUC drops when a feature is shuffled) and odds ratios from the
    logistic regression (direction of each effect).

Usage:
    python scripts/train_repeat_model.py
"""
from pathlib import Path
import sqlite3
import warnings

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.ticker as mtick
import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.impute import SimpleImputer
from sklearn.inspection import permutation_importance
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import average_precision_score, roc_auc_score
from sklearn.model_selection import StratifiedKFold, cross_val_score
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

warnings.filterwarnings("ignore", category=UserWarning)

ROOT = Path(__file__).resolve().parents[1]
DB_PATH = ROOT / "data" / "olist.db"
TABLES_DIR = ROOT / "outputs" / "tables"
CHARTS_DIR = ROOT / "outputs" / "charts"

SEED = 42
SPLIT_DATE = "2017-10-01"          # train: first purchase before; test: on/after
TARGET = "returned_180d"
NUMERIC = [
    "installments", "basket_orders", "basket_items", "basket_sellers",
    "basket_value", "basket_freight", "freight_share",
    "delivery_days", "estimated_delivery_days", "days_late", "was_late",
    "review_score", "review_missing", "review_has_comment",
    "first_hour", "first_weekday",
]
CATEGORICAL = ["payment_type", "region", "category"]
FEATURES = NUMERIC + CATEGORICAL
LOG_COLUMNS = ["basket_value", "basket_freight"]   # heavily right-skewed

# readable names for charts and tables
LABELS = {
    "installments": "Instalments", "basket_orders": "Orders in first basket",
    "basket_items": "Items in first basket", "basket_sellers": "Sellers in first basket",
    "basket_value": "Basket value", "basket_freight": "Freight cost",
    "freight_share": "Freight share of basket", "delivery_days": "Delivery time",
    "estimated_delivery_days": "Promised delivery time", "days_late": "Days late (vs promise)",
    "was_late": "Delivered late", "review_score": "Review score",
    "review_missing": "Left no review", "review_has_comment": "Wrote a review comment",
    "first_hour": "Hour of purchase", "first_weekday": "Day of week",
    "payment_type": "Payment method", "region": "Region", "category": "Product category",
}

BLUE, ORANGE, INK, INK_2, GRID, SURFACE = (
    "#2a78d6", "#eb6834", "#0b0b0b", "#52514e", "#e4e3df", "#fcfcfb")
plt.rcParams.update({
    "figure.facecolor": SURFACE, "axes.facecolor": SURFACE, "axes.edgecolor": GRID,
    "axes.labelcolor": INK_2, "axes.titlecolor": INK, "axes.titlesize": 13,
    "axes.titleweight": "bold", "axes.titlelocation": "left",
    "axes.spines.top": False, "axes.spines.right": False, "axes.grid": True,
    "grid.color": GRID, "grid.linewidth": 0.8, "xtick.color": INK_2, "ytick.color": INK_2,
    "font.family": ["Inter", "DejaVu Sans"], "font.size": 10,
    "savefig.dpi": 150, "savefig.bbox": "tight", "axes.axisbelow": True,
})


def load() -> pd.DataFrame:
    with sqlite3.connect(DB_PATH) as con:
        df = pd.read_sql_query("select * from mart_repeat_purchase", con)
    for col in LOG_COLUMNS:
        df[col] = np.log1p(df[col])
    return df


def preprocessor() -> ColumnTransformer:
    return ColumnTransformer([
        ("num", Pipeline([("impute", SimpleImputer(strategy="median")),
                          ("scale", StandardScaler())]), NUMERIC),
        ("cat", OneHotEncoder(handle_unknown="infrequent_if_exist", min_frequency=200),
         CATEGORICAL),
    ])


def logistic(C: float) -> Pipeline:
    return Pipeline([("pre", preprocessor()),
                     ("model", LogisticRegression(C=C, max_iter=3000))])


def boosting() -> Pipeline:
    return Pipeline([("pre", preprocessor()),
                     ("model", HistGradientBoostingClassifier(
                         learning_rate=0.04, max_iter=300, max_leaf_nodes=15,
                         min_samples_leaf=100, l2_regularization=1.0,
                         random_state=SEED))])


def choose_C(train: pd.DataFrame) -> tuple[float, pd.DataFrame]:
    cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=SEED)
    rows = []
    for C in (0.01, 0.03, 0.1, 0.3, 1.0):
        scores = cross_val_score(logistic(C), train[FEATURES], train[TARGET],
                                 cv=cv, scoring="roc_auc")
        rows.append({"C": C, "cv_auc_mean": scores.mean(), "cv_auc_std": scores.std()})
    table = pd.DataFrame(rows)
    return float(table.loc[table["cv_auc_mean"].idxmax(), "C"]), table


def bootstrap_auc(y: np.ndarray, s: np.ndarray, n: int = 1000) -> tuple[float, float]:
    rng = np.random.default_rng(SEED)
    aucs = []
    for _ in range(n):
        idx = rng.integers(0, len(y), len(y))
        if y[idx].min() != y[idx].max():
            aucs.append(roc_auc_score(y[idx], s[idx]))
    return float(np.percentile(aucs, 2.5)), float(np.percentile(aucs, 97.5))


def evaluate(name: str, y: np.ndarray, s: np.ndarray) -> dict:
    top10 = np.argsort(-s)[: len(s) // 10]
    top20 = np.argsort(-s)[: len(s) // 5]
    lo, hi = bootstrap_auc(y, s) if s.std() > 0 else (0.5, 0.5)
    return {
        "model": name,
        "test_roc_auc": round(roc_auc_score(y, s), 3) if s.std() > 0 else 0.5,
        "auc_95ci_low": round(lo, 3),
        "auc_95ci_high": round(hi, 3),
        "test_pr_auc": round(average_precision_score(y, s), 4),
        "base_rate": round(y.mean(), 4),
        "top10pct_return_rate": round(y[top10].mean(), 4),
        "top10pct_lift": round(y[top10].mean() / y.mean(), 2),
        "top20pct_share_of_returners": round(y[top20].sum() / y.sum(), 3),
    }


def lift_table(y: np.ndarray, s: np.ndarray) -> pd.DataFrame:
    d = pd.DataFrame({"y": y, "s": s})
    d["decile"] = pd.qcut(d["s"].rank(method="first", ascending=False), 10,
                          labels=range(1, 11)).astype(int)
    t = d.groupby("decile").agg(customers=("y", "size"), returners=("y", "sum"))
    t["return_rate"] = (t["returners"] / t["customers"]).round(4)
    t["lift"] = (t["return_rate"] / y.mean()).round(2)
    t["cumulative_share_of_returners"] = (t["returners"].cumsum() / y.sum()).round(3)
    return t.reset_index()


def odds_ratios(model: Pipeline) -> pd.DataFrame:
    """Odds ratio per 1 standard deviation for numeric features."""
    coefs = model.named_steps["model"].coef_[0][: len(NUMERIC)]
    return (pd.DataFrame({"feature": [LABELS[f] for f in NUMERIC],
                          "odds_ratio_per_sd": np.exp(coefs).round(3)})
            .sort_values("odds_ratio_per_sd", ascending=False))


def chart_importance(imp: pd.DataFrame) -> None:
    d = imp.head(10).iloc[::-1]
    fig, ax = plt.subplots(figsize=(10, 4.6))
    ax.barh(d["feature"], d["auc_drop"], xerr=d["auc_drop_std"], color=BLUE,
            height=0.6, error_kw={"ecolor": INK_2, "elinewidth": 1, "capsize": 2})
    ax.axvline(0, color=INK_2, linewidth=0.8)
    ax.grid(axis="y", visible=False)
    ax.set_xlabel("Drop in test AUC when the feature is shuffled")
    ax.set_title("What the repeat-purchase model relies on", pad=22)
    ax.text(0, 1.02, "Permutation importance, logistic regression, test period (Oct 2017 - Mar 2018)",
            transform=ax.transAxes, color=INK_2, fontsize=9.5, va="bottom")
    fig.savefig(CHARTS_DIR / "09_model_feature_importance.png")
    plt.close(fig)


def chart_lift(lift: pd.DataFrame, base_rate: float) -> None:
    fig, ax = plt.subplots(figsize=(10, 4.2))
    bars = ax.bar(lift["decile"].astype(str), lift["return_rate"] * 100, color=BLUE, width=0.6)
    for b, v in zip(bars, lift["return_rate"] * 100):
        ax.text(b.get_x() + b.get_width() / 2, v + 0.05, f"{v:.1f}%",
                ha="center", color=INK, fontsize=9)
    ax.axhline(base_rate * 100, color=ORANGE, linewidth=1.5, linestyle="--")
    ax.text(9.6, base_rate * 100 + 0.08, f"Average {base_rate:.1%}", color=ORANGE,
            ha="right", fontsize=9)
    ax.yaxis.set_major_locator(mtick.MultipleLocator(1))
    ax.yaxis.set_major_formatter(mtick.PercentFormatter(decimals=0))
    ax.set_ylim(0, max(lift["return_rate"].max() * 100 * 1.25, base_rate * 100 * 2))
    ax.grid(axis="x", visible=False)
    ax.set_xlabel("Customers ranked by predicted likelihood to return (1 = most likely 10%)")
    ax.set_title("Actual 180-day return rate by model score decile", pad=22)
    ax.text(0, 1.02, "Test period: first purchases Oct 2017 - Mar 2018",
            transform=ax.transAxes, color=INK_2, fontsize=9.5, va="bottom")
    fig.savefig(CHARTS_DIR / "10_model_lift.png")
    plt.close(fig)


def main() -> None:
    TABLES_DIR.mkdir(parents=True, exist_ok=True)
    CHARTS_DIR.mkdir(parents=True, exist_ok=True)
    df = load()
    labelled = df[df["has_full_window"] == 1]
    train = labelled[labelled["first_date"] < SPLIT_DATE]
    test = labelled[labelled["first_date"] >= SPLIT_DATE]
    y_test = test[TARGET].to_numpy()
    print(f"Train: {len(train):,} customers, {train[TARGET].mean():.2%} returned")
    print(f"Test:  {len(test):,} customers, {test[TARGET].mean():.2%} returned")

    best_C, cv_table = choose_C(train)
    cv_table.round(4).to_csv(TABLES_DIR / "model_cv_regularisation.csv", index=False)
    print(f"Chosen C = {best_C} (cross-validated on the training period)")

    logreg = logistic(best_C).fit(train[FEATURES], train[TARGET])
    gbm = boosting().fit(train[FEATURES], train[TARGET])
    scores = {
        "No-skill baseline": np.full(len(test), train[TARGET].mean()),
        "Logistic regression": logreg.predict_proba(test[FEATURES])[:, 1],
        "Gradient boosting": gbm.predict_proba(test[FEATURES])[:, 1],
    }
    metrics = pd.DataFrame([evaluate(n, y_test, s) for n, s in scores.items()])
    metrics.to_csv(TABLES_DIR / "model_metrics.csv", index=False)
    print("\n" + metrics.to_string(index=False))

    lift = lift_table(y_test, scores["Logistic regression"])
    lift.to_csv(TABLES_DIR / "model_lift_by_decile.csv", index=False)
    chart_lift(lift, y_test.mean())

    perm = permutation_importance(logreg, test[FEATURES], y_test, scoring="roc_auc",
                                  n_repeats=20, random_state=SEED)
    imp = (pd.DataFrame({"feature": [LABELS[f] for f in FEATURES],
                         "auc_drop": perm.importances_mean,
                         "auc_drop_std": perm.importances_std})
           .sort_values("auc_drop", ascending=False).round(4))
    imp.to_csv(TABLES_DIR / "model_feature_importance.csv", index=False)
    chart_importance(imp)
    odds_ratios(logreg).to_csv(TABLES_DIR / "model_odds_ratios.csv", index=False)

    # Score recent customers with a model refit on all labelled customers.
    final = logistic(best_C).fit(labelled[FEATURES], labelled[TARGET])
    recent = df[df["has_full_window"] == 0].copy()
    recent["return_probability"] = final.predict_proba(recent[FEATURES])[:, 1].round(4)
    recent["score_decile"] = pd.qcut(recent["return_probability"].rank(method="first",
                                     ascending=False), 10, labels=range(1, 11)).astype(int)
    out = recent[["customer_unique_id", "first_date", "return_probability", "score_decile"]]
    assert out["customer_unique_id"].is_unique and out["return_probability"].between(0, 1).all()
    with sqlite3.connect(DB_PATH) as con:
        out.to_sql("repeat_purchase_scores", con, if_exists="replace", index=False)
    print(f"\nScored {len(out):,} recent customers -> repeat_purchase_scores")


if __name__ == "__main__":
    main()
