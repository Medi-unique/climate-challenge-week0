"""Unit tests for NASA POWER cleaning helpers."""

from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from src.climate_cleaning import (
    add_time_columns,
    find_data_start_row,
    flag_zscore_outliers,
    impute_and_drop_sparse_rows,
    replace_sentinels,
    treat_duplicates,
)


def test_find_data_start_row(tmp_path: Path) -> None:
    csv = tmp_path / "sample.csv"
    csv.write_text("meta line\nYEAR,DOY,T2M\n2020,1,25.0\n", encoding="utf-8")
    assert find_data_start_row(csv) == 1


def test_add_time_columns() -> None:
    df = pd.DataFrame({"YEAR": [2020, 2020], "DOY": [1, 366]})
    out = add_time_columns(df)
    assert out["date"].iloc[0] == pd.Timestamp("2020-01-01")
    assert out["Month"].iloc[0] == 1


def test_replace_sentinels() -> None:
    df = pd.DataFrame({"YEAR": [2020], "T2M": [-999.0], "PRECTOTCORR": [1.0]})
    out = replace_sentinels(df)
    assert np.isnan(out["T2M"].iloc[0])


def test_treat_duplicates() -> None:
    df = pd.DataFrame({"a": [1, 1], "b": [2, 2]})
    clean, n = treat_duplicates(df)
    assert n == 1
    assert len(clean) == 1


def test_impute_and_drop_sparse_rows() -> None:
    df = pd.DataFrame(
        {
            "T2M": [1.0, np.nan, np.nan],
            "PRECTOTCORR": [np.nan, np.nan, np.nan],
            "RH2M": [np.nan, np.nan, np.nan],
        }
    )
    clean, n_drop = impute_and_drop_sparse_rows(df, weather_cols=list(df.columns))
    assert n_drop >= 1


def test_flag_zscore_outliers() -> None:
    rng = np.random.default_rng(0)
    x = rng.normal(size=500)
    df = pd.DataFrame({"T2M": x})
    out = flag_zscore_outliers(df, columns=["T2M"], threshold=3.0)
    assert "z_outlier_T2M" in out.columns
