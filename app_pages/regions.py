import streamlit as st

from src.charts import empty_state, line_chart, show
from src.config import REGION_ORDER
from src.data_loader import load_states
from src.metrics import per_100k, rolling_average
from src.ui import get_date_range

st.title("Regional comparison")
st.caption("US Census regions: Northeast, Midwest, South, West (territories grouped as Other).")

start, end = get_date_range()
states = load_states()

c1, c2 = st.columns(2)
with c1:
    outcome = st.radio("Outcome", ["Cases", "Deaths"], horizontal=True)
with c2:
    basis = st.radio("Basis", ["Per 100,000 residents", "Raw count"], horizontal=True)

daily_col = "daily_cases" if outcome == "Cases" else "daily_deaths"
df = states[(states["Date"] >= start) & (states["Date"] <= end)]
if df.empty:
    empty_state("No case data in that date range.")

# Territories have no state-level population in every row, so only normalise where population is known.
if basis.startswith("Per"):
    df = df.dropna(subset=["Population"])
region = df.groupby(["Region", "Date"], as_index=False).agg(value=(daily_col, "sum"), Population=("Population", "sum"))
region["Region"] = region["Region"].astype("category").cat.set_categories(REGION_ORDER)
region = region.sort_values(["Region", "Date"])
region["value"] = rolling_average(region, "value", 7, by="Region")
if basis.startswith("Per"):
    region["value"] = per_100k(region["value"], region["Population"])

label = f"Daily {outcome.lower()} (7-day avg{', per 100k' if basis.startswith('Per') else ''})"
show(line_chart(region, "Date", "value", color="Region", y_label=label, height=460))

latest = region[region["Date"] == region["Date"].max()].sort_values("value", ascending=False)
st.markdown(f"**Latest in range ({latest['Date'].max():%b %d, %Y})**")
st.dataframe(
    latest[["Region", "value"]].rename(columns={"value": label}),
    width="stretch",
    hide_index=True,
)
