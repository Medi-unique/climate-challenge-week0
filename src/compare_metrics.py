"""Cross-country metrics for compare_countries notebook and Streamlit."""

from __future__ import annotations

import numpy as np
import pandas as pd
from scipy import stats


def monthly_avg_t2m(df: pd.DataFrame) -> pd.DataFrame:
    """Monthly mean T2M by country."""
    g = df.groupby(["Country", df["date"].dt.to_period("M")], observed=True)["T2M"].mean()
    out = g.reset_index()
    out["date"] = out["date"].dt.to_timestamp()
    return out


def country_summary_stats(df: pd.DataFrame, col: str) -> pd.DataFrame:
    """Mean, median, std of a column by country."""
    agg = df.groupby("Country", observed=True)[col].agg(["mean", "median", "std"])
    return agg.rename(columns={"mean": "mean", "median": "median", "std": "std"})


def annual_heat_days(df: pd.DataFrame, threshold_c: float = 35.0) -> pd.DataFrame:
    """Count days per year with T2M_MAX > threshold."""
    tmp = df.copy()
    tmp["Year"] = tmp["date"].dt.year
    mask = tmp["T2M_MAX"] > threshold_c
    return (
        tmp.loc[mask]
        .groupby(["Country", "Year"], observed=True)
        .size()
        .reset_index(name="heat_days")
    )


def max_consecutive_dry_days(series: pd.Series, dry_threshold_mm: float = 1.0) -> int:
    """Longest run of consecutive days with precipitation < threshold."""
    dry = (series.fillna(0) < dry_threshold_mm).to_numpy()
    if not dry.any():
        return 0
    max_run = run = 0
    for flag in dry:
        if flag:
            run += 1
            max_run = max(max_run, run)
        else:
            run = 0
    return int(max_run)


def annual_max_dry_streak(df: pd.DataFrame, dry_threshold_mm: float = 1.0) -> pd.DataFrame:
    """For each country and calendar year, longest consecutive dry spell (PRECTOTCORR < 1 mm)."""
    tmp = df.copy()
    tmp["Year"] = tmp["date"].dt.year
    rows = []
    for (country, year), part in tmp.groupby(["Country", "Year"], observed=True):
        part = part.sort_values("date")
        streak = max_consecutive_dry_days(part["PRECTOTCORR"], dry_threshold_mm)
        rows.append({"Country": country, "Year": year, "max_dry_streak_days": streak})
    return pd.DataFrame(rows)


def kruskal_t2m_by_country_daily(df: pd.DataFrame) -> tuple[float, float]:
    """Kruskal–Wallis on daily T2M across countries (large N — interpret with care)."""
    groups = [g["T2M"].dropna().to_numpy() for _, g in df.groupby("Country", observed=True)]
    res = stats.kruskal(*groups)
    return float(res.statistic), float(res.pvalue)


def kruskal_t2m_by_country_annual_mean(df: pd.DataFrame) -> tuple[float, float]:
    """Kruskal–Wallis on annual mean T2M (one value per country per year)."""
    tmp = df.copy()
    tmp["Year"] = tmp["date"].dt.year
    annual = tmp.groupby(["Country", "Year"], observed=True)["T2M"].mean().reset_index()
    groups = [g["T2M"].to_numpy() for _, g in annual.groupby("Country", observed=True)]
    res = stats.kruskal(*groups)
    return float(res.statistic), float(res.pvalue)


def linear_trend_c_per_decade(dates: pd.Series, values: pd.Series) -> float:
    """OLS slope of values vs time, returned as change per decade."""
    x = dates.map(pd.Timestamp.toordinal).to_numpy(dtype=float)
    y = values.to_numpy(dtype=float)
    mask = np.isfinite(x) & np.isfinite(y)
    if mask.sum() < 2:
        return float("nan")
    slope, _intercept, _r, _p, _se = stats.linregress(x[mask], y[mask])
    return float(slope * 3652.5)  # ~365.25 * 10


def vulnerability_table(df: pd.DataFrame) -> pd.DataFrame:
    """
    Composite ranking using transparent pillars (higher score = more stressed).

    Pillars: warming rate (annual mean T2M), rainfall variability (CV of annual precip),
    heat exposure (mean annual heat days), drought stress (mean annual max dry streak).
    """
    tmp = df.copy()
    tmp["Year"] = tmp["date"].dt.year

    heat = annual_heat_days(tmp)
    dry = annual_max_dry_streak(tmp)

    rows = []
    for country in sorted(tmp["Country"].unique()):
        sub = tmp[tmp["Country"] == country]
        ann_temp = sub.groupby("Year", observed=True)["T2M"].mean()
        ann_precip = sub.groupby("Year", observed=True)["PRECTOTCORR"].sum()

        warming = linear_trend_c_per_decade(
            pd.to_datetime(ann_temp.index.astype(str) + "-07-01"),
            ann_temp,
        )
        precip_cv = float(ann_precip.std() / ann_precip.mean()) if ann_precip.mean() else np.nan

        h = heat[heat["Country"] == country]["heat_days"]
        d = dry[dry["Country"] == country]["max_dry_streak_days"]

        rows.append(
            {
                "Country": country,
                "warming_c_per_decade": warming,
                "precip_cv": precip_cv,
                "mean_annual_heat_days": float(h.mean()) if len(h) else 0.0,
                "mean_max_dry_streak": float(d.mean()) if len(d) else 0.0,
            }
        )

    vt = pd.DataFrame(rows)

    def norm(series: pd.Series) -> pd.Series:
        s = series.replace([np.inf, -np.inf], np.nan)
        lo, hi = s.min(), s.max()
        if hi == lo or pd.isna(hi):
            return pd.Series(0.0, index=s.index)
        return (s - lo) / (hi - lo)

    vt["score_warming"] = norm(vt["warming_c_per_decade"].fillna(0))
    vt["score_precip"] = norm(vt["precip_cv"].fillna(0))
    vt["score_heat"] = norm(vt["mean_annual_heat_days"])
    vt["score_dry"] = norm(vt["mean_max_dry_streak"])

    weights = {"score_warming": 0.3, "score_precip": 0.3, "score_heat": 0.2, "score_dry": 0.2}
    vt["vulnerability_score"] = sum(vt[k] * w for k, w in weights.items())
    vt["rank"] = vt["vulnerability_score"].rank(ascending=False, method="min").astype(int)
    return vt.sort_values("vulnerability_score", ascending=False).reset_index(drop=True)
