"""Cached, read-only access to the files in ``data/``. The app imports only from here."""
from __future__ import annotations

import pandas as pd
import streamlit as st

from src import config
from src.metrics import clip_negative, per_100k


@st.cache_data(show_spinner=False)
def load_us() -> pd.DataFrame:
    df = pd.read_csv(config.US_FILE, parse_dates=["date"])
    for col in ("daily_cases", "daily_deaths"):
        df[col] = clip_negative(df[col])
    return df.sort_values("date").reset_index(drop=True)


@st.cache_data(show_spinner=False)
def load_states() -> pd.DataFrame:
    """State-level NYT data with population-adjusted columns and region."""
    df = pd.read_csv(config.STATES_FILE, parse_dates=["Date"])
    for col in ("daily_cases", "daily_deaths"):
        df[col] = clip_negative(df[col])
    pop = pd.read_csv(config.POPULATION_FILE)
    df = df.merge(pop, on="State", how="left")
    df["cases_per_100k"] = per_100k(df["Total_Cases"], df["Population"])
    df["deaths_per_100k"] = per_100k(df["Total_Deaths"], df["Population"])
    return df.sort_values(["State", "Date"]).reset_index(drop=True)


@st.cache_data(show_spinner=False)
def load_regions() -> pd.DataFrame:
    return pd.read_csv(config.REGIONS_FILE)


@st.cache_data(show_spinner=False)
def load_hospital() -> pd.DataFrame:
    df = pd.read_parquet(config.HOSPITAL_FILE)
    df["state_name"] = df["state"].map(config.STATE_CODES)
    return df


@st.cache_data(show_spinner=False)
def load_world_hospital() -> pd.DataFrame:
    return pd.read_csv(config.WORLD_HOSPITAL_FILE, parse_dates=["Day"])
