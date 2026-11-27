import numpy as np
import pandas as pd
import pytest

from src import config
from src.music_etl import build_music_hist, build_music_stats, build_music_tracks, build_music_weekly


def _raw(rows):
    """rows: (week 'M/D/YYYY', track_id, pivot, streams)"""
    df = pd.DataFrame(rows, columns=["week", "track_id", "pivot", "streams"])
    for f in config.MUSIC_FEATURES:
        df["duration" if f == "duration_s" else f] = 500.0
    return df


def test_tracks_filter_pivot_window_and_assign_period():
    raw = _raw(
        [
            ("3/6/2020", "a", 0, 10),    # before split
            ("3/13/2020", "a", 0, 10),   # first chart after the split -> during
            ("3/13/2020", "a", 1, 10),   # second artist on the same track: dropped
            ("11/30/2018", "b", 0, 10),  # before the analysis window: dropped
            ("1/1/2021", "c", 0, 10),    # after the analysis window: dropped
        ]
    )
    out = build_music_tracks(raw)
    assert out[["track_id", "period"]].values.tolist() == [["a", "before"], ["a", "during"]]
    assert out["duration_s"].eq(0.5).all()  # milliseconds converted to seconds
    assert "duration" not in out.columns
    assert "pivot" not in out.columns


def test_weekly_weighted_mean_uses_streams():
    tracks = pd.DataFrame(
        {"week": pd.Timestamp("2019-01-04"), "period": "before", "track_id": ["a", "b"], "streams": [1, 3]}
    )
    for f in config.MUSIC_FEATURES:
        tracks[f] = [0.0, 1.0]
    row = build_music_weekly(tracks).query("feature == 'energy'").iloc[0]
    assert row["mean"] == pytest.approx(0.5)
    assert row["weighted_mean"] == pytest.approx(0.75)
    assert row["n_tracks"] == 2


def _tracks(before, during):
    rows = [("before", f"b{i}", v) for i, v in enumerate(before)] + [("during", f"d{i}", v) for i, v in enumerate(during)]
    df = pd.DataFrame(rows, columns=["period", "track_id", "v"])
    df["week"] = pd.Timestamp("2019-01-04")
    df["streams"] = 1
    for f in config.MUSIC_FEATURES:
        df[f] = df["v"]
    return df.drop(columns="v")


def test_stats_known_welch_result_and_adjustment():
    stats = build_music_stats(_tracks([1, 2, 3, 4, 5], [3, 4, 5, 6, 7]))
    row = stats.iloc[0]
    assert row["diff"] == pytest.approx(2.0)
    assert row["cohens_d"] == pytest.approx(2 / np.sqrt(2.5))
    assert row["p_welch"] == pytest.approx(0.0805, abs=1e-3)  # t = 2, df = 8
    assert (stats["p_adj"] >= stats["p_welch"] - 1e-12).all() and (stats["p_adj"] <= 1).all()
    assert len(stats) == len(config.MUSIC_FEATURES)


def test_stats_counts_track_once_per_period_and_keeps_overlap():
    tracks = pd.concat([_tracks([1, 2], [3, 4]), _tracks([1], [])])  # b0 appears in two weeks
    tracks.loc[tracks.index[-1], "week"] = pd.Timestamp("2019-01-11")
    stats = build_music_stats(tracks)
    assert stats.loc[0, "n_before"] == 2  # duplicate weekly appearance collapsed

    both = pd.concat([_tracks([1, 2], [3, 4]), _tracks([], [])])
    both = pd.concat([both, both[both["track_id"] == "b0"].assign(period="during")])
    s = build_music_stats(both)
    assert s.loc[0, "n_before"] == 2 and s.loc[0, "n_during"] == 3  # b0 kept in both periods


def test_hist_density_integrates_to_one_per_period():
    rng = np.random.default_rng(0)
    tracks = _tracks(rng.random(200), rng.random(150))
    hist = build_music_hist(tracks)
    area = (hist["density"] * (hist["bin_right"] - hist["bin_left"])).groupby([hist["feature"], hist["period"]]).sum()
    assert np.allclose(area, 1.0)
