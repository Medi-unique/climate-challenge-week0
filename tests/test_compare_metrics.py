"""Tests for cross-country metrics."""

import pandas as pd

from src.compare_metrics import max_consecutive_dry_days, vulnerability_table


def test_max_consecutive_dry_days() -> None:
    s = pd.Series([0.0, 0.0, 2.0, 0.0, 0.0, 0.0])
    assert max_consecutive_dry_days(s, dry_threshold_mm=1.0) == 3


def test_vulnerability_table_shapes() -> None:
    rng = pd.date_range("2015-01-01", periods=800, freq="D")
    df = pd.DataFrame(
        {
            "Country": ["A"] * len(rng) + ["B"] * len(rng),
            "date": list(rng) + list(rng),
            "T2M": 25.0,
            "T2M_MAX": 32.0,
            "PRECTOTCORR": 2.0,
        }
    )
    vt = vulnerability_table(df)
    assert "vulnerability_score" in vt.columns
    assert len(vt) == 2
