"""Pure, UI-free data helpers. Everything here is unit-tested."""
from __future__ import annotations

import pandas as pd


def clip_negative(series: pd.Series) -> pd.Series:
    """NYT occasionally revises totals downward, giving negative daily values; floor them at 0."""
    return series.clip(lower=0)


def rolling_average(df: pd.DataFrame, column: str, window: int = 7, by: str | None = None) -> pd.Series:
    """Trailing mean of ``column`` (optionally within each ``by`` group); df must be date-sorted."""
    if by is None:
        return df[column].rolling(window, min_periods=1).mean()
    return df.groupby(by, observed=True)[column].transform(lambda s: s.rolling(window, min_periods=1).mean())


def per_100k(values: pd.Series, population: pd.Series) -> pd.Series:
    """Rate per 100,000 residents; missing or zero population gives NaN."""
    return values / population.where(population > 0) * 100_000


def top_n(df: pd.DataFrame, label: str, column: str, n: int) -> pd.DataFrame:
    """Rank rows by ``column`` descending and return the top ``n`` (index starts at 1)."""
    out = df[[label, column]].sort_values(column, ascending=False).head(n).reset_index(drop=True)
    out.index += 1
    return out


def period_change(series: pd.Series, days: int = 7) -> float | None:
    """Percent change of the latest ``days``-day sum versus the previous ``days``-day sum."""
    if len(series) < 2 * days:
        return None
    current = series.iloc[-days:].sum()
    previous = series.iloc[-2 * days : -days].sum()
    if previous == 0:
        return None
    return (current - previous) / previous * 100


def summarise_us(us: pd.DataFrame, as_of: pd.Timestamp) -> dict:
    """Headline numbers for the Overview cards as of a date (empty dict if date not in data)."""
    us = us.sort_values("date")
    history = us[us["date"] <= as_of]
    if history.empty or history["date"].iloc[-1] != as_of:
        return {}
    row = history.iloc[-1]
    avg7 = history["daily_cases"].clip(lower=0).tail(7).mean()
    avg7_d = history["daily_deaths"].clip(lower=0).tail(7).mean()
    return {
        "total_cases": int(row["cases"]),
        "total_deaths": int(row["deaths"]),
        "daily_cases": int(max(row["daily_cases"], 0)),
        "daily_deaths": int(max(row["daily_deaths"], 0)),
        "avg7_cases": float(avg7),
        "avg7_deaths": float(avg7_d),
        "cases_change_pct": period_change(history["daily_cases"].clip(lower=0)),
        "deaths_change_pct": period_change(history["daily_deaths"].clip(lower=0)),
    }


def weekly_cases(us: pd.DataFrame, week_ends: pd.Series) -> pd.Series:
    """New US cases in the 7 days ending on each date in ``week_ends`` (negative revisions floored at 0).

    Dates before the first NYT record count as 0 cases. Returned series is indexed by ``week_ends``.
    """
    daily = us.set_index("date")["daily_cases"].clip(lower=0)
    full = pd.date_range(min(daily.index.min(), week_ends.min() - pd.Timedelta(days=6)), daily.index.max(), freq="D")
    rolled = daily.reindex(full, fill_value=0).rolling(7, min_periods=7).sum()
    out = rolled.reindex(pd.DatetimeIndex(week_ends))
    out.index = pd.DatetimeIndex(week_ends)
    return out


def lagged_correlation(cases: pd.Series, feature: pd.Series, lags: range | list[int]) -> pd.DataFrame:
    """Pearson r between cases ``lag`` weeks earlier and the feature now (both indexed by week)."""
    rows = []
    for lag in lags:
        pair = pd.concat([cases.shift(lag), feature], axis=1).dropna()
        r = pair.iloc[:, 0].corr(pair.iloc[:, 1]) if len(pair) > 2 else float("nan")
        rows.append({"lag_weeks": lag, "r": r, "n_weeks": len(pair)})
    return pd.DataFrame(rows)
