from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import pandas as pd


@dataclass(frozen=True)
class LoadResult:
    df: pd.DataFrame
    missing_files: list[str]


DEFAULT_COUNTRIES: list[str] = ["Ethiopia", "Kenya", "Sudan", "Tanzania", "Nigeria"]


def repo_root() -> Path:
    """Resolve project root by locating src/climate_cleaning.py."""
    here = Path(__file__).resolve()
    for d in (here.parent, *here.parents):
        if (d / "src" / "climate_cleaning.py").is_file():
            return d
    # Fallback: assume cwd is repo root when running streamlit
    return Path.cwd().resolve()


def expected_clean_csv_paths(
    data_dir: Path,
    countries: Iterable[str] = DEFAULT_COUNTRIES,
) -> dict[str, Path]:
    return {c: data_dir / f"{c.lower()}_clean.csv" for c in countries}


def load_clean_csvs(
    paths_by_country: dict[str, Path],
) -> LoadResult:
    frames: list[pd.DataFrame] = []
    missing: list[str] = []

    for country, path in paths_by_country.items():
        if not path.is_file():
            missing.append(str(path))
            continue

        df = pd.read_csv(path)
        if "Country" not in df.columns:
            df["Country"] = country
        df["Country"] = df["Country"].astype(str)

        if "date" in df.columns:
            df["date"] = pd.to_datetime(df["date"], errors="coerce")
        elif {"YEAR", "DOY"}.issubset(df.columns):
            y = df["YEAR"].astype(int).astype(str)
            d = df["DOY"].astype(int).astype(str).str.zfill(3)
            df["date"] = pd.to_datetime(y + d, format="%Y%j", errors="coerce")
        else:
            raise ValueError(f"{path} has no 'date' and no YEAR+DOY columns.")

        frames.append(df)

    if not frames:
        empty = pd.DataFrame(columns=["Country", "date"])
        return LoadResult(df=empty, missing_files=missing)

    combined = pd.concat(frames, ignore_index=True)
    combined = combined.dropna(subset=["date"])
    combined["Year"] = combined["date"].dt.year.astype(int)
    combined["Month"] = combined["date"].dt.to_period("M").dt.to_timestamp()
    return LoadResult(df=combined, missing_files=missing)


def available_numeric_variables(df: pd.DataFrame) -> list[str]:
    exclude = {"YEAR", "DOY", "Month", "Year"}
    cols = [
        c
        for c in df.columns
        if c not in exclude and c not in {"Country", "date"} and pd.api.types.is_numeric_dtype(df[c])
    ]
    # Prefer common variables first
    preferred = ["T2M", "PRECTOTCORR", "RH2M", "T2M_MAX", "T2M_MIN"]
    ordered = [c for c in preferred if c in cols] + [c for c in cols if c not in preferred]
    return ordered


def filter_df(
    df: pd.DataFrame,
    countries: list[str],
    year_range: tuple[int, int],
) -> pd.DataFrame:
    if df.empty:
        return df
    start, end = year_range
    return df[
        (df["Country"].isin(countries))
        & (df["Year"] >= int(start))
        & (df["Year"] <= int(end))
    ].copy()


def monthly_mean(df: pd.DataFrame, value_col: str) -> pd.DataFrame:
    if df.empty:
        return df
    out = (
        df.groupby(["Country", "Month"], observed=True)[value_col]
        .mean()
        .reset_index()
        .rename(columns={"Month": "date", value_col: "value"})
    )
    return out

