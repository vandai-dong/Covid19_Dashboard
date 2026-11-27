import pandas as pd
import plotly.express as px
import streamlit as st

from src.charts import empty_state, show, style
from src.config import NAME_TO_CODE
from src.data_loader import load_states

st.title("Map")
st.caption("Cumulative cases or deaths per 100,000 residents by state. The 50 states and DC are drawn; territories are listed in the table below.")

states = load_states()
lo, hi = states["Date"].min(), states["Date"].max()

c1, c2, c3 = st.columns([1, 1, 2])
with c1:
    outcome = st.radio("Outcome", ["Cases", "Deaths"], horizontal=True)
with c2:
    animate = st.toggle("Animate by month")
with c3:
    as_of = pd.Timestamp(st.date_input("As of date", value=hi.date(), min_value=lo.date(), max_value=hi.date(), disabled=animate))

column = "cases_per_100k" if outcome == "Cases" else "deaths_per_100k"
label = f"{outcome} per 100k"
states = states.assign(code=states["State"].map(NAME_TO_CODE)).rename(columns={column: label})

if animate:
    # Month-end snapshots keep the animation light (~38 frames).
    months = states.assign(month=states["Date"].dt.to_period("M"))
    frame = months.sort_values("Date").groupby(["month", "State"], as_index=False).last()
    frame["Month"] = frame["month"].astype(str)
    frame = frame.dropna(subset=[label])
    fig = px.choropleth(
        frame, locations="code", locationmode="USA-states", color=label, animation_frame="Month",
        scope="usa", color_continuous_scale="Reds", range_color=(0, frame[label].max()), hover_name="State",
    )
else:
    day = states[states["Date"] == as_of].dropna(subset=[label])
    if day.empty:
        empty_state("No data for that date.")
    fig = px.choropleth(
        day, locations="code", locationmode="USA-states", color=label, scope="usa",
        color_continuous_scale="Reds", range_color=(0, day[label].max()), hover_name="State",
        hover_data={"code": False, label: ":,.0f"},
    )
show(style(fig, height=520))

if not animate:
    st.markdown(f"**All jurisdictions, {as_of:%b %d, %Y}**")
    table = day.sort_values(label, ascending=False)[["State", "Region", "Population", label]]
    st.dataframe(table, width="stretch", hide_index=True, column_config={label: st.column_config.NumberColumn(format="%.0f"), "Population": st.column_config.NumberColumn(format="%d")})
