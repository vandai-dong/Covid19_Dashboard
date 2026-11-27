import pandas as pd
import plotly.express as px
import streamlit as st

from src.charts import empty_state, line_chart, show, style
from src.config import AGE_BANDS
from src.data_loader import load_hospital, load_world_hospital
from src.ui import get_date_range

st.title("Hospitals")
st.caption("HHS state-level hospital capacity and patient-impact reporting, plus an international comparison.")

start, end = get_date_range()
hos = load_hospital()
hos = hos[(hos["admission_date"] >= start) & (hos["admission_date"] <= end)]
if hos.empty:
    empty_state("No hospital data in that date range.")

tab_adm, tab_cap, tab_staff, tab_world = st.tabs(["Admissions by age", "ICU & bed use", "Staff shortages", "US vs world"])

with tab_adm:
    age_cols = [f"admission_{b}" for b in AGE_BANDS]
    adm = hos.groupby("admission_date", as_index=False)[age_cols].sum()
    adm = adm.melt(id_vars="admission_date", var_name="Age group", value_name="Admissions")
    adm["Age group"] = adm["Age group"].str.removeprefix("admission_")
    show(line_chart(adm, "admission_date", "Admissions", color="Age group", y_label="Adult confirmed admissions"))
    st.caption("Adults with confirmed COVID-19 admitted the previous day, summed across reporting states.")

with tab_cap:
    cap = hos.groupby("admission_date", as_index=False)[["icu_beds", "icu_covid_patients", "inpatient_beds", "inpatient_beds_covid"]].sum()
    cap = cap[(cap["icu_beds"] > 0) & (cap["inpatient_beds"] > 0)]
    if cap.empty:
        st.info("No capacity data reported in this range.")
    else:
        cap["ICU beds used by COVID patients (%)"] = cap["icu_covid_patients"] / cap["icu_beds"] * 100
        cap["Inpatient beds used by COVID patients (%)"] = cap["inpatient_beds_covid"] / cap["inpatient_beds"] * 100
        long = cap.melt(
            id_vars="admission_date",
            value_vars=["ICU beds used by COVID patients (%)", "Inpatient beds used by COVID patients (%)"],
            var_name="Measure", value_name="Share of beds (%)",
        )
        show(line_chart(long, "admission_date", "Share of beds (%)", color="Measure", y_label="Share of beds (%)"))

with tab_staff:
    shortage_day = pd.Timestamp(
        st.date_input("Date", value=min(end, hos["date"].max()).date(), min_value=start.date(), max_value=end.date(), key="shortage_day")
    )
    day = hos[hos["date"] == shortage_day].dropna(subset=["staff_shortage_hospitals"])
    if day.empty:
        st.info("No staffing-shortage reports for that date (reporting began mid-2020).")
    else:
        fig = px.choropleth(
            day, locations="state", locationmode="USA-states", scope="usa", color="staff_shortage_hospitals",
            color_continuous_scale="Blues", range_color=(0, max(day["staff_shortage_hospitals"].max(), 1)),
            labels={"staff_shortage_hospitals": "Hospitals reporting a critical staffing shortage"},
            hover_name="state_name",
        )
        show(style(fig, height=420))

with tab_world:
    world = load_world_hospital()
    countries = sorted(set(world["Entity"]) - {"United States"})
    chosen = st.multiselect("Compare the US with", countries, default=[c for c in ["Australia"] if c in countries])
    w = world[world["Entity"].isin(["United States", *chosen]) & (world["Day"] >= start) & (world["Day"] <= end)]
    if w.empty:
        st.info("No data in this date range.")
    else:
        show(line_chart(w, "Day", "Daily hospital occupancy", color="Entity", y_label="COVID-19 patients in hospital"))
        st.caption("Source: Our World in Data.")
