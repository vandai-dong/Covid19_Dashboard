"""Cross-page UI state: the sidebar date range lives in ``st.session_state`` so every page shares it."""
from __future__ import annotations

import pandas as pd
import streamlit as st

from src.data_loader import load_hospital, load_us

KEY = "date_range"


def bounds() -> tuple[pd.Timestamp, pd.Timestamp]:
    us, hos = load_us(), load_hospital()
    return min(us["date"].min(), hos["date"].min()), max(us["date"].max(), hos["date"].max())


def sidebar_date_range() -> None:
    """Render the shared date filter. Call once from the entry script."""
    lo, hi = bounds()
    us_end = load_us()["date"].max()
    st.sidebar.header("Filters")
    st.sidebar.date_input(
        "Date range",
        value=(load_us()["date"].min().date(), us_end.date()),
        min_value=lo.date(),
        max_value=hi.date(),
        key=KEY,
        help="Applies to the Trends, Regions and Hospitals pages.",
    )
    st.sidebar.caption(
        f"Case/death data (NYT) ends {us_end:%b %d, %Y}. Hospital data (HHS) runs to {hi:%b %d, %Y}."
    )


def get_date_range() -> tuple[pd.Timestamp, pd.Timestamp]:
    """Current (start, end). While the user has picked only one end of the range, stop the page."""
    us = load_us()
    value = st.session_state.get(KEY, (us["date"].min().date(), us["date"].max().date()))
    if not isinstance(value, (tuple, list)) or len(value) != 2:
        st.info("Pick both a start and an end date in the sidebar.")
        st.stop()
    start, end = pd.Timestamp(value[0]), pd.Timestamp(value[1])
    return start, end
