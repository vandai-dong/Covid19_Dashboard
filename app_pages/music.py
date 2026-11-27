import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from plotly.subplots import make_subplots

from src import config
from src.charts import line_chart, show, style
from src.data_loader import load_music_hist, load_music_stats, load_music_weekly, load_us
from src.metrics import lagged_correlation, weekly_cases

LABELS = {
    "danceability": "Danceability",
    "energy": "Energy",
    "speechiness": "Speechiness",
    "acousticness": "Acousticness",
    "instrumentalness": "Instrumentalness",
    "liveness": "Liveness",
    "valence": "Valence (positivity)",
    "tempo": "Tempo (BPM)",
    "duration_s": "Duration (s)",
}
SPLIT = pd.Timestamp(config.MUSIC_SPLIT_DATE)
COLORS = {"before": "#4c78a8", "during": "#d1495b"}

st.title("Music & COVID-19")
st.caption(
    "Did the audio profile of Spotify's global weekly Top 200 change after COVID-19 was declared a pandemic? "
    "This page uses a fixed analysis window; the sidebar date range does not apply."
)

weekly, stats, hist = load_music_weekly(), load_music_stats(), load_music_hist()
first_week, last_week = weekly["week"].min(), weekly["week"].max()
n_before = weekly.loc[weekly["period"] == "before", "week"].nunique()
n_during = weekly.loc[weekly["period"] == "during", "week"].nunique()

with st.expander("Method and data", expanded=False):
    st.markdown(
        f"""
- **Data:** Spotify global weekly Top 200, {first_week:%b %d, %Y} to {last_week:%b %d, %Y}
  ({n_before} weekly charts before, {n_during} during), joined to Spotify audio features.
  Source: [younver/spotify-top-200-dataset](https://github.com/younver/spotify-top-200-dataset).
- **Split:** {SPLIT:%b %d, %Y}, when the WHO declared COVID-19 a pandemic. Charts dated on or after it are "during".
- **Unit of analysis:** unique tracks per period. A song that charted in both periods counts in both
  (the original notebook removed these songs, which biased the comparison).
- **Tests:** Welch t-test per feature, with Benjamini-Hochberg adjustment across the {len(stats)} features. Mann-Whitney U
  is a robustness check. Cohen's d is the effect size.
- **Not included:** track popularity (a snapshot taken years after the chart date, so older tracks read as 0)
  and the song recommender from the earlier project (it needs track-level data, which is not redistributed).
"""
    )

# ----------------------------------------------------------------- headline
significant = stats[stats["p_adj"] < 0.05]
biggest = stats.loc[stats["cohens_d"].abs().idxmax()]
if significant.empty:
    st.success(
        f"**No feature changed significantly** after adjusting for {len(stats)} comparisons. "
        f"The largest effect was for {LABELS[biggest['feature']]} (Cohen's d = {biggest['cohens_d']:+.2f}), which is small."
    )
else:
    names = ", ".join(LABELS[f] for f in significant["feature"])
    st.warning(f"**{len(significant)} of {len(stats)} features changed significantly** (adjusted p < 0.05): {names}.")

# --------------------------------------------------------------- table
st.subheader("Before vs during")
table = stats.assign(Feature=stats["feature"].map(LABELS))[
    ["Feature", "mean_before", "mean_during", "cohens_d", "p_adj", "p_welch"]
]
st.dataframe(
    table,
    hide_index=True,
    width="stretch",
    column_config={
        "mean_before": st.column_config.NumberColumn("Mean before", format="%.3f"),
        "mean_during": st.column_config.NumberColumn("Mean during", format="%.3f"),
        "cohens_d": st.column_config.NumberColumn("Cohen's d", format="%+.3f"),
        "p_welch": st.column_config.NumberColumn("p (raw)", format="%.3f"),
        "p_adj": st.column_config.NumberColumn("p (adjusted)", help="Benjamini-Hochberg across all features", format="%.3f"),
    },
)
st.caption("Read the adjusted p-value: with several features tested at once, some raw p-values below 0.05 are expected by chance.")

# ------------------------------------------------------------ explorer
st.subheader("Explore a feature")
feature = st.selectbox("Feature", config.MUSIC_FEATURES, format_func=LABELS.get)
row = stats.set_index("feature").loc[feature]

left, right = st.columns(2)
with left:
    st.markdown("**Distribution of unique tracks**")
    h = hist[hist["feature"] == feature]
    fig = go.Figure()
    for period in ("before", "during"):
        g = h[h["period"] == period]
        fig.add_bar(
            x=(g["bin_left"] + g["bin_right"]) / 2,
            y=g["density"],
            width=(g["bin_right"] - g["bin_left"]),
            name=period.title(),
            marker_color=COLORS[period],
            opacity=0.6,
        )
        fig.add_vline(x=row[f"mean_{period}"], line_dash="dash", line_color=COLORS[period])
    fig.update_layout(barmode="overlay", xaxis_title=LABELS[feature], yaxis_title="Density")
    show(style(fig, height=340))
with right:
    st.markdown("**Weekly average across the Top 200**")
    weighted = st.toggle("Weight by streams", help="Weights each track by its weekly streams instead of counting each equally.")
    w = weekly[weekly["feature"] == feature]
    fig = line_chart(w, "week", "weighted_mean" if weighted else "mean", y_label=LABELS[feature], height=340)
    fig.add_shape(type="line", x0=SPLIT, x1=SPLIT, y0=0, y1=1, yref="paper", line=dict(dash="dash", color="gray"))
    fig.add_annotation(x=SPLIT, y=1, yref="paper", text="Pandemic declared", showarrow=False, yshift=10, font=dict(size=11))
    show(fig)

# --------------------------------------------------------- COVID overlay
st.subheader("Compared with US COVID-19 cases")
us = load_us()
w = weekly[weekly["feature"] == feature].sort_values("week").reset_index(drop=True)
w["cases"] = weekly_cases(us, w["week"]).to_numpy()
col = "weighted_mean" if weighted else "mean"

lag = st.slider(
    "Lag (weeks): compare music this week with cases N weeks earlier", 0, 12, 0,
    help="Tests whether listening follows case waves with a delay.",
)
shifted = w["cases"].shift(lag)

fig = make_subplots(specs=[[{"secondary_y": True}]])
fig.add_scatter(x=w["week"], y=w[col], name=LABELS[feature], line=dict(color=COLORS["before"]), secondary_y=False)
fig.add_scatter(x=w["week"], y=shifted, name=f"US weekly cases (lag {lag}w)", line=dict(color=COLORS["during"], dash="dot"), secondary_y=True)
fig.update_yaxes(title_text=LABELS[feature], secondary_y=False)
fig.update_yaxes(title_text="US new cases per week", secondary_y=True)
show(style(fig, height=400))

covid_weeks = w["week"] >= us["date"].min()
cases_s = w.loc[covid_weeks].set_index("week")["cases"]
feature_s = w.loc[covid_weeks].set_index("week")[col]
levels = lagged_correlation(cases_s, feature_s, [lag]).iloc[0]
changes = lagged_correlation(cases_s.diff(), feature_s.diff(), [lag]).iloc[0]


def fmt(r: float) -> str:
    return "n/a" if pd.isna(r) else f"{r:+.2f}"


c1, c2, c3 = st.columns(3)
c1.metric("r (levels)", fmt(levels["r"]), help="Dominated by shared trends and seasonality; do not read as an effect.")
c2.metric("r (week-to-week changes)", fmt(changes["r"]), help="Removes shared trends, so it is the more conservative check.")
c3.metric("Weeks compared", int(levels["n_weeks"]))
st.caption(
    "Global music against US cases, so a loose comparison. A strong correlation in levels is expected from "
    "seasonality alone: the winter 2020 case surge coincides with holiday-season charts. Correlation is not causation. "
    f"Music data ends {last_week:%b %d, %Y}, before the US case data does. Case counts cover the 7 days ending on "
    "each chart date (Friday), assuming the chart date is the end of its week."
)

st.subheader("Limitations")
st.markdown(
    """
- Top-200 charts describe what is streamed most, not what any individual listens to.
- Streaming volume and listener mix changed during 2020, which can shift charts independently of taste.
- Songs on the charts for many weeks count once, so the unit is "songs that charted", not "plays".
- Songs in both periods are not independent samples; the Mann-Whitney column is a sanity check, not a fix.
- The source dataset's licence does not clear Spotify's own terms, so this repo ships only aggregates.
"""
)
