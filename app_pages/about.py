import streamlit as st

from src.data_loader import load_hospital, load_regions, load_states, load_us

st.title("Data & About")

us, states, hos = load_us(), load_states(), load_hospital()

st.markdown(
    f"""
An interactive Streamlit dashboard exploring the US COVID-19 pandemic: cases and deaths, regional
patterns, and hospital impact.

**Data freshness**
- Cases and deaths (NYT): through **{us['date'].max():%b %d, %Y}**. The NYT stopped updating this dataset in March 2023.
- Hospital capacity (HHS): through **{hos['date'].max():%b %d, %Y}**.

**Notes**
- Daily values are first differences of cumulative totals. Negative values (caused by retroactive revisions) are floored at 0.
- Per-100k figures use 2020 Census resident population.
- 7-day averages are trailing.

**Sources**
- [New York Times COVID-19 data](https://github.com/nytimes/covid-19-data) (cases and deaths)
- [HHS COVID-19 Reported Patient Impact and Hospital Capacity by State Timeseries](https://healthdata.gov/dataset/COVID-19-Reported-Patient-Impact-and-Hospital-Capa/g62h-syeh)
- [Our World in Data: COVID-19 hospitalizations](https://ourworldindata.org/covid-hospitalizations)
- [US Census regions and divisions](https://github.com/cphalpert/census-regions)
"""
)

st.subheader("Download data")
c1, c2, c3, c4 = st.columns(4)
c1.download_button("US daily (CSV)", us.to_csv(index=False), "us_daily.csv", "text/csv")
c2.download_button("States daily (CSV)", states.to_csv(index=False), "states_daily.csv", "text/csv")
c3.download_button("Regions (CSV)", load_regions().to_csv(index=False), "regions.csv", "text/csv")
c4.download_button("Hospital (CSV)", hos.to_csv(index=False), "hospital_state_daily.csv", "text/csv")
