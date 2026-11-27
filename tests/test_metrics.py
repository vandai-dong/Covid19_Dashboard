import numpy as np
import pandas as pd
import pytest

from src.metrics import (
    clip_negative,
    lagged_correlation,
    per_100k,
    period_change,
    rolling_average,
    summarise_us,
    top_n,
    weekly_cases,
)


def test_clip_negative():
    assert clip_negative(pd.Series([-5, 0, 3])).tolist() == [0, 0, 3]


def test_rolling_average_trailing_and_min_periods():
    df = pd.DataFrame({"v": [1, 2, 3, 4]})
    assert rolling_average(df, "v", window=2).tolist() == [1.0, 1.5, 2.5, 3.5]


def test_rolling_average_by_group_does_not_leak_between_groups():
    df = pd.DataFrame({"g": ["a", "a", "b", "b"], "v": [10, 20, 100, 200]})
    assert rolling_average(df, "v", window=2, by="g").tolist() == [10.0, 15.0, 100.0, 150.0]


def test_per_100k_and_missing_population():
    out = per_100k(pd.Series([50, 10]), pd.Series([100_000, 0]))
    assert out.iloc[0] == 50
    assert pd.isna(out.iloc[1])


def test_top_n_ranks_from_one():
    df = pd.DataFrame({"State": list("abc"), "x": [1, 9, 5]})
    out = top_n(df, "State", "x", 2)
    assert out["State"].tolist() == ["b", "c"]
    assert out.index.tolist() == [1, 2]


def test_period_change():
    s = pd.Series([10] * 7 + [20] * 7)
    assert period_change(s, 7) == 100
    assert period_change(pd.Series([1, 2, 3]), 7) is None
    assert period_change(pd.Series([0] * 7 + [5] * 7), 7) is None


def _us(days=20):
    dates = pd.date_range("2021-01-01", periods=days)
    return pd.DataFrame(
        {"date": dates, "cases": range(days), "deaths": range(days), "daily_cases": [1] * days, "daily_deaths": [-1] + [1] * (days - 1)}
    )


def test_summarise_us_floors_negative_and_handles_missing_date():
    us = _us()
    s = summarise_us(us, us["date"].iloc[-1])
    assert s["total_cases"] == 19 and s["daily_cases"] == 1
    assert s["cases_change_pct"] == 0
    assert summarise_us(us, pd.Timestamp("1999-01-01")) == {}
    first = summarise_us(us, us["date"].iloc[0])
    assert first["daily_deaths"] == 0  # negative revision floored
    assert first["cases_change_pct"] is None  # not enough history


@pytest.mark.parametrize("n", [0, 5])
def test_top_n_handles_small_inputs(n):
    df = pd.DataFrame({"State": ["a"], "x": [1]})
    assert len(top_n(df, "State", "x", n)) == min(n, 1)


def test_weekly_cases_is_trailing_7_day_sum_and_floors_negatives():
    dates = pd.date_range("2020-01-21", periods=21)
    us = pd.DataFrame({"date": dates, "daily_cases": [1] * 20 + [-5]})
    weeks = pd.Series(pd.to_datetime(["2020-01-03", "2020-01-27", "2020-02-10"]))
    out = weekly_cases(us, weeks)
    assert out.index.tolist() == weeks.tolist()
    assert out.iloc[0] == 0   # before the first NYT record
    assert out.iloc[1] == 7   # Jan 21-27 inclusive
    assert out.iloc[2] == 6   # Feb 4-10: six 1s, and the -5 revision on Feb 10 is floored to 0


def test_lagged_correlation_peaks_at_true_lag():
    idx = pd.date_range("2020-03-06", periods=30, freq="7D")
    cases = pd.Series(np.sin(np.arange(30) / 3), index=idx)
    feature = cases.shift(2)  # feature follows cases by 2 weeks
    out = lagged_correlation(cases, feature, range(0, 5)).set_index("lag_weeks")
    assert out["r"].idxmax() == 2
    assert out.loc[2, "r"] == pytest.approx(1.0)
    assert lagged_correlation(cases.iloc[:2], feature.iloc[:2], [0])["r"].isna().all()
