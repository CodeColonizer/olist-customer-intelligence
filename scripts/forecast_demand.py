"""Forecast monthly demand (items ordered) for the largest product categories.

Input:  mart_category_demand (built by scripts/build.py)
Output: demand_forecasts table in the database,
        outputs/tables/forecast_backtest.csv, outputs/tables/category_demand_forecast.csv,
        outputs/charts/14_forecast_backtest.png, outputs/charts/15_category_forecasts.png

Design:
  * Series: the 12 categories with the most items ordered in Jan-Aug 2018 (71%
    of items), plus the marketplace total. Monthly, Jan 2017 to Aug 2018: only
    20 complete months, so methods are deliberately simple.
  * Methods: naive (last month), 3-month moving average, simple exponential
    smoothing, damped-trend exponential smoothing (Holt), and top-down (forecast
    the total, then split it by each category's share of the last 3 months).
  * Backtest: rolling origin. Train on data up to Feb, Mar, Apr and May 2018 and
    forecast the next 1-3 months each time, so every method is scored on the
    same 12 out-of-sample category-months per origin. The method with the lowest
    WAPE (weighted absolute percentage error) across categories is used.
  * Uncertainty: 80% intervals come from the chosen method's own backtest
    errors (10th-90th percentile of actual / forecast, per horizon).
  * Black Friday: none of these methods can learn a once-a-year spike from one
    year of history. November is therefore shown twice: the baseline forecast,
    and a scenario that applies the November 2017 uplift over October 2017,
    shrunk towards the marketplace-wide uplift for smaller categories.

Usage:
    python scripts/forecast_demand.py
"""
from pathlib import Path
import sqlite3

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DB_PATH = ROOT / "data" / "olist.db"
TABLES_DIR = ROOT / "outputs" / "tables"
CHARTS_DIR = ROOT / "outputs" / "charts"

TOP_N = 12
HORIZON = 3
BACKTEST_ORIGINS = ["2018-02", "2018-03", "2018-04", "2018-05"]   # last training month
FORECAST_MONTHS = ["2018-09", "2018-10", "2018-11"]
TOTAL = "All categories"
BF_PRIOR_ITEMS = 200      # Black Friday shrinkage: prior worth 200 October items

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


# ---------------------------------------------------------------- methods
def naive(y: np.ndarray, h: int) -> np.ndarray:
    return np.repeat(y[-1], h)


def moving_average(y: np.ndarray, h: int, k: int = 3) -> np.ndarray:
    return np.repeat(y[-k:].mean(), h)


def simple_smoothing(y: np.ndarray, h: int) -> np.ndarray:
    """Simple exponential smoothing; alpha chosen by one-step-ahead squared error."""
    best = (np.inf, y[-1])
    for alpha in np.linspace(0.05, 0.95, 19):
        level, sse = y[0], 0.0
        for value in y[1:]:
            sse += (value - level) ** 2
            level = alpha * value + (1 - alpha) * level
        best = min(best, (sse, level), key=lambda t: t[0])
    return np.repeat(best[1], h)


def damped_trend(y: np.ndarray, h: int, phi: float = 0.9) -> np.ndarray:
    """Holt's linear method with a damped trend; alpha and beta chosen by
    one-step-ahead squared error, damping fixed at 0.9."""
    best = (np.inf, None)
    for alpha in np.linspace(0.1, 0.9, 9):
        for beta in (0.05, 0.1, 0.2, 0.3):
            level, trend, sse = y[0], y[1] - y[0], 0.0
            for value in y[1:]:
                sse += (value - (level + phi * trend)) ** 2
                new_level = alpha * value + (1 - alpha) * (level + phi * trend)
                trend = beta * (new_level - level) + (1 - beta) * phi * trend
                level = new_level
            if sse < best[0]:
                steps = np.cumsum(phi ** np.arange(1, h + 1))
                best = (sse, level + steps * trend)
    return np.maximum(best[1], 0)


METHODS = {
    "Naive (last month)": naive,
    "3-month moving average": moving_average,
    "Exponential smoothing": simple_smoothing,
    "Damped trend": damped_trend,
}
TOP_DOWN = "Top-down (total x recent share)"


def forecast_all(history: pd.DataFrame, method: str, h: int) -> pd.DataFrame:
    """Forecast every column of `history` (months x series) h months ahead."""
    if method == TOP_DOWN:
        total = damped_trend(history[TOTAL].to_numpy(float), h)
        recent = history.tail(3).sum()
        share = recent / recent[TOTAL]
        return pd.DataFrame({s: total * share[s] for s in history.columns})
    fn = METHODS[method]
    return pd.DataFrame({s: fn(history[s].to_numpy(float), h) for s in history.columns})


# ---------------------------------------------------------------- pipeline
def load_series(con: sqlite3.Connection) -> tuple[pd.DataFrame, list[str], float]:
    demand = pd.read_sql_query("select month, category, items from mart_category_demand", con)
    wide = demand.pivot(index="month", columns="category", values="items").sort_index()
    totals_2018 = wide.loc["2018-01":"2018-08"].sum()
    top = totals_2018.nlargest(TOP_N).index.tolist()
    coverage = totals_2018[top].sum() / totals_2018.sum()
    series = wide[top].copy()
    series[TOTAL] = wide.sum(axis=1)
    return series, top, coverage


def backtest(series: pd.DataFrame, top: list[str]) -> tuple[pd.DataFrame, pd.DataFrame]:
    rows = []
    for method in list(METHODS) + [TOP_DOWN]:
        for origin in BACKTEST_ORIGINS:
            history = series.loc[:origin]
            actual = series.loc[origin:].iloc[1:HORIZON + 1]
            pred = forecast_all(history, method, HORIZON)
            for step in range(HORIZON):
                for s in series.columns:
                    rows.append({"method": method, "origin": origin, "horizon": step + 1,
                                 "month": actual.index[step], "series": s,
                                 "actual": actual[s].iloc[step], "forecast": pred[s].iloc[step]})
    errors = pd.DataFrame(rows)

    def score(df: pd.DataFrame) -> pd.Series:
        return pd.Series({
            "wape_pct": 100 * (df["forecast"] - df["actual"]).abs().sum() / df["actual"].sum(),
            "bias_pct": 100 * (df["forecast"] - df["actual"]).sum() / df["actual"].sum(),
        })

    cats = errors[errors["series"].isin(top)]
    summary = cats.groupby("method").apply(score, include_groups=False)
    for h in range(1, HORIZON + 1):
        summary[f"wape_h{h}_pct"] = (cats[cats["horizon"] == h]
                                     .groupby("method").apply(score, include_groups=False)["wape_pct"])
    summary["total_wape_pct"] = (errors[errors["series"] == TOTAL]
                                 .groupby("method").apply(score, include_groups=False)["wape_pct"])
    summary = summary.sort_values("wape_pct").round(1).reset_index()
    return summary, errors


def black_friday_uplift(series: pd.DataFrame) -> pd.Series:
    """November 2017 / October 2017, shrunk towards the total uplift."""
    oct_, nov = series.loc["2017-10"], series.loc["2017-11"]
    overall = nov[TOTAL] / oct_[TOTAL]
    uplift = (nov + BF_PRIOR_ITEMS * overall) / (oct_ + BF_PRIOR_ITEMS)
    uplift[TOTAL] = overall
    return uplift


def chart_backtest(summary: pd.DataFrame, best: str) -> None:
    d = summary.iloc[::-1]
    fig, ax = plt.subplots(figsize=(10, 3.8))
    colors = [BLUE if m == best else GRID for m in d["method"]]
    ax.barh(d["method"], d["wape_pct"], color=colors, height=0.6)
    for y, v in enumerate(d["wape_pct"]):
        ax.text(v + 0.4, y, f"{v:.1f}%", va="center", color=INK_2, fontsize=9)
    ax.set_xlim(0, d["wape_pct"].max() * 1.2)
    ax.xaxis.set_major_formatter(matplotlib.ticker.PercentFormatter(decimals=0))
    ax.grid(axis="y", visible=False)
    ax.set_xlabel("Forecast error (WAPE, lower is better)")
    ax.set_title("Backtest: which forecasting method is most accurate?", pad=22)
    ax.text(0, 1.02, f"Top {TOP_N} categories, 1-3 months ahead, from 4 forecast origins (Mar-Aug 2018)",
            transform=ax.transAxes, color=INK_2, fontsize=9.5, va="bottom")
    fig.savefig(CHARTS_DIR / "14_forecast_backtest.png")
    plt.close(fig)


def chart_forecasts(series: pd.DataFrame, fc: pd.DataFrame, panels: list[str]) -> None:
    fig, axes = plt.subplots(2, 3, figsize=(12, 6.4), sharex=True)
    hist_x = np.arange(len(series))
    fc_x = np.arange(len(series), len(series) + len(FORECAST_MONTHS))
    for ax, s in zip(axes.flat, panels):
        f = fc[fc["series"] == s]
        ax.plot(hist_x, series[s], color=BLUE, linewidth=1.8)
        ax.fill_between(fc_x, f["low_80"], f["high_80"], color=ORANGE, alpha=0.18, linewidth=0)
        ax.plot(np.r_[hist_x[-1], fc_x], np.r_[series[s].iloc[-1], f["baseline_forecast"]],
                color=ORANGE, linewidth=1.8, linestyle="--")
        nov = f[f["month"] == FORECAST_MONTHS[-1]]
        ax.plot(fc_x[-1], nov["black_friday_scenario"], marker="o", color=ORANGE, markersize=5)
        ax.set_title(s.replace("_", " ").capitalize(), fontsize=10.5, pad=6)
        ax.set_ylim(0, max(series[s].max(), f["high_80"].max(), nov["black_friday_scenario"].max()) * 1.1)
        ax.grid(axis="x", visible=False)
        ax.yaxis.set_major_formatter(matplotlib.ticker.StrMethodFormatter("{x:,.0f}"))
    ticks = [0, 6, 12, 18, 22]
    labels = list(series.index) + FORECAST_MONTHS
    for ax in axes[-1]:
        ax.set_xticks(ticks)
        ax.set_xticklabels([pd.Period(labels[t]).strftime("%b %y") for t in ticks])
    fig.suptitle("Monthly items ordered: history and forecast", x=0.01, ha="left",
                 fontsize=13, fontweight="bold", color=INK, y=1.03)
    fig.text(0.01, 0.975, "Blue = actual. Dashed = baseline forecast Sep-Nov 2018, shaded = 80% range. "
             "Dot = November with a Black Friday uplift like 2017.",
             ha="left", color=INK_2, fontsize=9.5)
    fig.tight_layout()
    fig.savefig(CHARTS_DIR / "15_category_forecasts.png")
    plt.close(fig)


def main() -> None:
    TABLES_DIR.mkdir(parents=True, exist_ok=True)
    CHARTS_DIR.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(DB_PATH) as con:
        series, top, coverage = load_series(con)
        print(f"Forecasting {TOP_N} categories ({coverage:.0%} of Jan-Aug 2018 items) and the total")

        summary, errors = backtest(series, top)
        summary.to_csv(TABLES_DIR / "forecast_backtest.csv", index=False)
        best = summary["method"].iloc[0]
        print("\nBacktest (WAPE and bias across top categories, %):")
        print(summary.to_string(index=False))
        print(f"\nChosen method: {best}")

        # 80% interval from the chosen method's backtest errors, by horizon
        chosen = errors[(errors["method"] == best) & errors["series"].isin(top)]
        ratio = (chosen["actual"] / chosen["forecast"]).groupby(chosen["horizon"])
        low, high = ratio.quantile(0.10), ratio.quantile(0.90)

        pred = forecast_all(series, best, len(FORECAST_MONTHS))
        uplift = black_friday_uplift(series)
        rows = []
        for s in [TOTAL] + top:
            for step, month in enumerate(FORECAST_MONTHS):
                f = float(pred[s].iloc[step])
                is_nov = month.endswith("-11")
                rows.append({
                    "series": s, "month": month, "horizon": step + 1,
                    "recent_monthly_avg": round(series[s].tail(3).mean(), 0),
                    "baseline_forecast": round(f, 0),
                    "low_80": round(f * low[step + 1], 0),
                    "high_80": round(f * high[step + 1], 0),
                    "black_friday_uplift": round(uplift[s], 2) if is_nov else None,
                    "black_friday_scenario": round(f * uplift[s], 0) if is_nov else None,
                })
        fc = pd.DataFrame(rows)
        fc.to_csv(TABLES_DIR / "category_demand_forecast.csv", index=False)
        fc.assign(method=best).to_sql("demand_forecasts", con, if_exists="replace", index=False)

    chart_backtest(summary, best)
    chart_forecasts(series, fc, [TOTAL] + top[:5])
    print(f"\n80% interval (actual / forecast) by horizon: "
          + ", ".join(f"h{h}: {low[h]:.2f}-{high[h]:.2f}" for h in low.index))
    print("\nForecasts written to demand_forecasts:")
    print(fc.to_string(index=False))


if __name__ == "__main__":
    main()
