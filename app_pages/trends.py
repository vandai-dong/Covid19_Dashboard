import streamlit as st

from src.charts import empty_state, line_chart, show
from src.data_loader import load_states, load_us
from src.metrics import per_100k, rolling_average
from src.ui import get_date_range

st.title("Trends")
st.caption("Compare the US and individual states over time.")

start, end = get_date_range()
us, states = load_us(), load_states()

c1, c2, c3 = st.columns([2, 1, 1])
with c1:
    selected = st.multiselect("States (leave empty for US total)", sorted(states["State"].unique()), default=["California", "New York", "Texas"])
with c2:
    outcome = st.radio("Outcome", ["Cases", "Deaths"], horizontal=True)
with c3:
    measure = st.radio("Measure", ["Daily (7-day avg)", "Cumulative"], horizontal=True)
c4, c5 = st.columns(2)
with c4:
    normalise = st.toggle("Per 100,000 residents", value=bool(selected), disabled=not selected)
with c5:
    log_y = st.toggle("Log scale")

daily_col = "daily_cases" if outcome == "Cases" else "daily_deaths"
total_col = "cases" if outcome == "Cases" else "deaths"

if selected:
    df = states[states["State"].isin(selected)].rename(columns={"Total_Cases": "cases", "Total_Deaths": "deaths", "Date": "date"})
    df = df.sort_values(["State", "date"])
    series = "State"
else:
    df = us.assign(State="United States")
    series = "State"

value = "value"
if measure.startswith("Daily"):
    df[value] = rolling_average(df, daily_col, 7, by=series)
else:
    df[value] = df[total_col]
if normalise and selected:
    df[value] = per_100k(df[value], df["Population"])

df = df[(df["date"] >= start) & (df["date"] <= end)]
if df.empty:
    empty_state("No case data in that date range. NYT data ends on " f"{us['date'].max():%b %d, %Y}.")

label = f"{outcome} ({'per 100k' if normalise and selected else 'count'})"
show(line_chart(df, "date", value, color=series, y_label=label, log_y=log_y, height=460))

with st.expander("Show data"):
    st.dataframe(df[["date", series, value]].rename(columns={value: label}), width="stretch", hide_index=True)
