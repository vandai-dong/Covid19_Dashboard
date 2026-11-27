"""Music & COVID pipeline: Spotify weekly global Top 200 + audio features, before vs during COVID-19.

Source: https://github.com/younver/spotify-top-200-dataset (GPL-3.0 per the repo; the underlying Spotify
data is subject to Spotify's Developer Terms). To respect that, only *derived aggregates* are written to
``data/`` (weekly means, per-period statistics, histogram bins). No track-level rows are ever committed.

    python -m src.etl --skip-core --music --download-music
"""
from __future__ import annotations

import logging

import numpy as np
import pandas as pd

from src import config
from src.etl import _atomic_write, _download

log = logging.getLogger("etl")

RAW_COLUMNS = ["track_id", "week", "pivot", "streams", "duration", *config.MUSIC_FEATURES[:-1]]  # duration (ms) -> duration_s
HIST_BINS = 30


def build_music_tracks(raw: pd.DataFrame) -> pd.DataFrame:
    """One row per (week, track) inside the analysis window, labelled before/during.

    The source has one row per artist on a track; ``pivot == 0`` marks the first artist, so keeping it
    counts each track once per week. Charts are dated Fridays.
    """
    df = raw[raw["pivot"] == 0].copy()
    df["week"] = pd.to_datetime(df["week"], format="%m/%d/%Y")
    df["duration_s"] = df["duration"] / 1000
    lo, hi = pd.Timestamp(config.MUSIC_WINDOW[0]), pd.Timestamp(config.MUSIC_WINDOW[1])
    df = df[(df["week"] >= lo) & (df["week"] <= hi)]
    df["period"] = np.where(df["week"] < pd.Timestamp(config.MUSIC_SPLIT_DATE), "before", "during")
    keep = ["week", "period", "track_id", "streams", *config.MUSIC_FEATURES]
    return df[keep].sort_values(["week", "track_id"]).reset_index(drop=True)


def build_music_weekly(tracks: pd.DataFrame) -> pd.DataFrame:
    """Per week and feature: plain mean across the 200 charting tracks, and stream-weighted mean."""
    rows = []
    for week, g in tracks.groupby("week"):
        weights = g["streams"].to_numpy(dtype=float)
        for feature in config.MUSIC_FEATURES:
            values = g[feature].to_numpy(dtype=float)
            rows.append(
                {
                    "week": week,
                    "period": g["period"].iloc[0],
                    "feature": feature,
                    "mean": values.mean(),
                    "weighted_mean": np.average(values, weights=weights),
                    "n_tracks": len(g),
                }
            )
    return pd.DataFrame(rows)


def build_music_stats(tracks: pd.DataFrame) -> pd.DataFrame:
    """Before-vs-during comparison per feature on *unique tracks* per period.

    Each song counts once per period and songs charting in both periods are kept in both
    (the original notebook dropped them, biasing the comparison). Welch t-test, Mann-Whitney U,
    Cohen's d, and Benjamini-Hochberg adjusted p-values across features.
    """
    from scipy import stats  # ETL-only dependency (requirements-dev.txt)

    unique = tracks.drop_duplicates(["period", "track_id"])
    rows = []
    for feature in config.MUSIC_FEATURES:
        b = unique.loc[unique["period"] == "before", feature].to_numpy(dtype=float)
        d = unique.loc[unique["period"] == "during", feature].to_numpy(dtype=float)
        welch = stats.ttest_ind(d, b, equal_var=False)
        mwu = stats.mannwhitneyu(d, b, alternative="two-sided")
        pooled = np.sqrt(((len(b) - 1) * b.var(ddof=1) + (len(d) - 1) * d.var(ddof=1)) / (len(b) + len(d) - 2))
        rows.append(
            {
                "feature": feature,
                "n_before": len(b),
                "n_during": len(d),
                "mean_before": b.mean(),
                "mean_during": d.mean(),
                "sd_before": b.std(ddof=1),
                "sd_during": d.std(ddof=1),
                "diff": d.mean() - b.mean(),
                "cohens_d": (d.mean() - b.mean()) / pooled,
                "p_welch": welch.pvalue,
                "p_mannwhitney": mwu.pvalue,
            }
        )
    out = pd.DataFrame(rows)
    out["p_adj"] = stats.false_discovery_control(out["p_welch"].to_numpy(), method="bh")
    return out


def build_music_hist(tracks: pd.DataFrame, bins: int = HIST_BINS) -> pd.DataFrame:
    """Density histograms per feature and period on shared bin edges (unique tracks)."""
    unique = tracks.drop_duplicates(["period", "track_id"])
    rows = []
    for feature in config.MUSIC_FEATURES:
        edges = np.histogram_bin_edges(unique[feature].to_numpy(dtype=float), bins=bins)
        for period, g in unique.groupby("period"):
            density, _ = np.histogram(g[feature].to_numpy(dtype=float), bins=edges, density=True)
            rows.extend(
                {"feature": feature, "period": period, "bin_left": lo, "bin_right": hi, "density": dens}
                for lo, hi, dens in zip(edges[:-1], edges[1:], density, strict=True)
            )
    return pd.DataFrame(rows)


def run_music(download: bool = False) -> None:
    if download or not config.MUSIC_RAW_FILE.exists():
        _download(config.MUSIC_URL, config.MUSIC_RAW_FILE)
    raw = pd.read_csv(config.MUSIC_RAW_FILE, sep=";", usecols=RAW_COLUMNS)
    tracks = build_music_tracks(raw)
    weeks = tracks["week"].nunique()
    if weeks != 108:
        raise ValueError(f"Expected 108 weekly charts in the analysis window, found {weeks}")
    weekly, stats_df, hist = build_music_weekly(tracks), build_music_stats(tracks), build_music_hist(tracks)
    _atomic_write(config.MUSIC_WEEKLY_FILE, lambda p: weekly.to_csv(p, index=False, float_format='%.6g'))
    _atomic_write(config.MUSIC_STATS_FILE, lambda p: stats_df.to_csv(p, index=False, float_format='%.6g'))
    _atomic_write(config.MUSIC_HIST_FILE, lambda p: hist.to_csv(p, index=False, float_format='%.6g'))
    log.info("Wrote music aggregates: %d weeks, %d feature comparisons", weeks, len(stats_df))
