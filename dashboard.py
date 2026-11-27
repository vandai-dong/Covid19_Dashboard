"""Streamlit entry point:  streamlit run dashboard.py"""
import streamlit as st

st.set_page_config(page_title="US COVID-19 Dashboard", page_icon=":material/coronavirus:", layout="wide")

from src.ui import sidebar_date_range  # noqa: E402  (must follow set_page_config)

pages = [
    st.Page("app_pages/overview.py", title="Overview", icon=":material/dashboard:", default=True),
    st.Page("app_pages/trends.py", title="Trends", icon=":material/show_chart:"),
    st.Page("app_pages/regions.py", title="Regions", icon=":material/compare_arrows:"),
    st.Page("app_pages/map.py", title="Map", icon=":material/map:"),
    st.Page("app_pages/hospitals.py", title="Hospitals", icon=":material/local_hospital:"),
    st.Page("app_pages/music.py", title="Music & COVID", icon=":material/music_note:"),
    st.Page("app_pages/about.py", title="Data & About", icon=":material/info:"),
]

sidebar_date_range()
st.navigation(pages).run()
