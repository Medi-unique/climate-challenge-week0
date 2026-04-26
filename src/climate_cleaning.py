"""Load and clean NASA POWER daily CSV exports (Week 0 challenge)."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

SENTINEL = -999
ZSCORE_COLUMNS = [
    "T2M",
    "T2M_MAX",
    "T2M_MIN",
    "PRECTOTCORR",
    "RH2M",
    "WS2M",
    "WS2M_MAX",
]


def find_data_start_row(path: str | Path, header_token: str = "YEAR") -> int:
    """Return 0-based line index where the comma-separated data header begins."""
    path = Path(path)
    with path.open(encoding="utf-8", errors="replace") as handle:
        for idx, line in enumerate(handle):
            stripped = line.lstrip()
            if stripped.startswith(header_token) and header_token in stripped.split(",")[0]:
                return idx
    raise ValueError(f"Could not find '{header_token}' header row in {path}")


def load_nasa_power_csv(csv_path: str | Path, country: str) -> pd.DataFrame:
    """
    Read a NASA POWER CSV, skipping preamble metadata lines before the YEAR row.

    Parameters
    ----------
    csv_path:
        Path to the country export (e.g. data/ethiopia.csv). Do not commit CSVs to Git.
    country:
        Human-readable country label stored in the Country column.
    """
    csv_path = Path(csv_path)
    skiprows = find_data_start_row(csv_path)
    df = pd.read_csv(csv_path, skiprows=skiprows)
    df["Country"] = country
    return df


def add_time_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Add parsed date and calendar month from YEAR + DOY (Julian day of year)."""
    out = df.copy()
    y = out["YEAR"].astype(int).astype(str)
    d = out["DOY"].astype(int).astype(str).str.zfill(3)
    out["date"] = pd.to_datetime(y + d, format="%Y%j")
    out["Month"] = out["date"].dt.month
    return out


def replace_sentinels(df: pd.DataFrame, sentinel: float = SENTINEL) -> pd.DataFrame:
    """Replace NASA POWER missing / out-of-range sentinel values with NaN."""
    out = df.copy()
    numeric = out.select_dtypes(include=[np.number]).columns
    for col in numeric:
        out[col] = out[col].replace(sentinel, np.nan)
    return out


def treat_duplicates(df: pd.DataFrame) -> tuple[pd.DataFrame, int]:
    """Drop duplicate rows; return cleaned frame and duplicate count."""
    n_dup = int(df.duplicated().sum())
    return df.drop_duplicates().reset_index(drop=True), n_dup


def summarize_missing(df: pd.DataFrame) -> pd.Series:
    """Return percentage of missing values per column (0–100)."""
    return df.isna().mean() * 100


def flag_zscore_outliers(
    df: pd.DataFrame,
    columns: list[str] | None = None,
    threshold: float = 3.0,
) -> pd.DataFrame:
    """
    Add boolean columns z_outlier_<var> where |z| > threshold for each numeric column.

    Z-scores use column mean/std on the post-sentinels frame (NaNs ignored per column).
    """
    cols = columns or [c for c in ZSCORE_COLUMNS if c in df.columns]
    out = df.copy()
    for col in cols:
        series = pd.to_numeric(out[col], errors="coerce")
        mu = series.mean()
        sigma = series.std(ddof=0)
        if sigma == 0 or np.isnan(sigma):
            out[f"z_outlier_{col}"] = False
            continue
        z = (series - mu) / sigma
        out[f"z_outlier_{col}"] = z.abs() > threshold
    return out


def impute_and_drop_sparse_rows(
    df: pd.DataFrame,
    weather_cols: list[str] | None = None,
    max_row_missing_frac: float = 0.30,
) -> tuple[pd.DataFrame, int]:
    """
    Forward-fill small gaps in weather variables, then drop rows with excessive missingness.

    Returns
    -------
    cleaned_df, n_dropped_rows
    """
    meta = {"YEAR", "DOY", "Country", "date", "Month"}
    if weather_cols is None:
        weather_cols = [
            c
            for c in df.columns
            if c not in meta and not str(c).startswith("z_outlier_")
        ]
    out = df.copy()
    out[weather_cols] = out[weather_cols].ffill()

    row_missing_frac = out[weather_cols].isna().mean(axis=1)
    mask_bad = row_missing_frac > max_row_missing_frac
    n_drop = int(mask_bad.sum())
    out = out.loc[~mask_bad].reset_index(drop=True)
    return out, n_drop


def export_clean_csv(df: pd.DataFrame, path: str | Path) -> None:
    """Write cleaned data to data/ (gitignored)."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=False)
