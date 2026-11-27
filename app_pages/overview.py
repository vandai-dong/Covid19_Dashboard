import pandas as pd
import streamlit as st

from src.charts import empty_state, metric_card
from src.data_loader import load_states, load_us
from src.metrics import summarise_us, top_n

st.title("Overview")
st.caption("US COVID-19 headline numbers and the hardest-hit states on a given day.")

us, states = load_us(), load_states()
lo, hi = us["date"].min(), us["date"].max()

as_of = pd.Timestamp(st.date_input("As of date", value=hi.date(), min_value=lo.date(), max_value=hi.date()))
summary = summarise_us(us, as_of)
if not summary:
    empty_state("No data for that date.")

c1, c2, c3, c4 = st.columns(4)
with c1:
    metric_card("Total cases", summary["total_cases"])
with c2:
    metric_card("New cases (7-day avg)", summary["avg7_cases"], summary["cases_change_pct"])
with c3:
    metric_card("Total deaths", summary["total_deaths"])
with c4:
    metric_card("New deaths (7-day avg)", summary["avg7_deaths"], summary["deaths_change_pct"])

st.divider()
left, right = st.columns([3, 1])
with left:
    st.subheader("Top states")
with right:
    n = st.selectbox("Show top", [5, 10, 15], index=1)
per_capita = st.toggle("Per 100,000 residents", help="Normalises by 2020 Census population.")

day = states[states["Date"] == as_of]
if day.empty:
    empty_state("No state data for that date.")

if per_capita:
    day = day.dropna(subset=["Population"])
    day = day.assign(
        daily_cases=day["daily_cases"] / day["Population"] * 1e5,
        daily_deaths=day["daily_deaths"] / day["Population"] * 1e5,
    )
    tables = {
        "Total cases": "cases_per_100k",
        "Daily cases": "daily_cases",
        "Total deaths": "deaths_per_100k",
        "Daily deaths": "daily_deaths",
    }
else:
    tables = {
        "Total cases": "Total_Cases",
        "Daily cases": "daily_cases",
        "Total deaths": "Total_Deaths",
        "Daily deaths": "daily_deaths",
    }

cols = st.columns(2)
for i, (title, column) in enumerate(tables.items()):
    with cols[i % 2]:
        st.markdown(f"**{title}**")
        table = top_n(day, "State", column, n).rename(columns={column: title})
        st.dataframe(
            table,
            width="stretch",
            column_config={title: st.column_config.NumberColumn(format="%.1f" if per_capita else "%d")},
        )
