from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Iterable

import pandas as pd

DEFAULT_COUNTRIES: list[str] = ["Ethiopia", "Kenya", "Sudan", "Tanzania", "Nigeria"]

GDRIVE_FOLDER_ENV = "GDRIVE_FOLDER_URL"


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


def _extract_gdrive_folder_id(folder_url_or_id: str) -> str:
    s = folder_url_or_id.strip()
    # Accept raw ID
    if re.fullmatch(r"[A-Za-z0-9_-]{10,}", s) and "/" not in s:
        return s
    m = re.search(r"/folders/([A-Za-z0-9_-]+)", s)
    if m:
        return m.group(1)
    raise ValueError(
        "Could not parse Google Drive folder id. "
        "Expected a URL like https://drive.google.com/drive/folders/<id> or the raw <id>."
    )


def try_download_clean_csvs_from_gdrive(data_dir: Path) -> bool:
    """
    If GDRIVE_FOLDER_URL is set and local cleaned CSVs are missing, download the folder
    contents into data_dir using gdown.

    The Drive folder must be publicly accessible (anyone with link).
    """
    folder = os.getenv(GDRIVE_FOLDER_ENV, "").strip()
    if not folder:
        return False

    try:
        folder_id = _extract_gdrive_folder_id(folder)
    except ValueError:
        return False

    try:
        import gdown  # type: ignore
    except Exception:
        return False

    data_dir.mkdir(parents=True, exist_ok=True)
    url = f"https://drive.google.com/drive/folders/{folder_id}"

    # gdown will create a subfolder by default; we download into data_dir and then
    # rely on expected filenames to be present (either directly or within one level).
    try:
        gdown.download_folder(url=url, output=str(data_dir), quiet=True, use_cookies=False)
    except Exception:
        return False

    # If files landed inside a child folder, move any *_clean.csv up one level.
    for p in list(data_dir.rglob("*_clean.csv")):
        if p.parent == data_dir:
            continue
        dest = data_dir / p.name
        if not dest.exists():
            try:
                p.replace(dest)
            except Exception:
                pass

    # Success if we now have at least one expected file
    return any((data_dir / f"{c.lower()}_clean.csv").is_file() for c in DEFAULT_COUNTRIES)


def gdrive_diagnostics(data_dir: Path) -> dict:
    """
    Small diagnostics payload to help debug Streamlit Cloud deployments.
    Never includes file contents.
    """
    folder = os.getenv(GDRIVE_FOLDER_ENV, "").strip()
    files = sorted([p.name for p in data_dir.rglob("*.csv")]) if data_dir.exists() else []
    expected = [f"{c.lower()}_clean.csv" for c in DEFAULT_COUNTRIES]
    present = {name: (data_dir / name).is_file() for name in expected}
    return {
        "env_set": bool(folder),
        "env_value_prefix": (folder[:40] + "...") if folder else "",
        "data_dir": str(data_dir),
        "csv_files_found": files[:50],
        "expected_present": present,
    }


def load_clean_csvs(
    paths_by_country: dict[str, Path],
) -> tuple[pd.DataFrame, list[str]]:
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
        return empty, missing

    combined = pd.concat(frames, ignore_index=True)
    combined = combined.dropna(subset=["date"])
    combined["Year"] = combined["date"].dt.year.astype(int)
    combined["Month"] = combined["date"].dt.to_period("M").dt.to_timestamp()
    return combined, missing


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

