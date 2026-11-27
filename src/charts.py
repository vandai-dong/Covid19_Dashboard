"""Shared Plotly figure builders / small UI helpers."""
from __future__ import annotations

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

TEMPLATE = "plotly_white"


def style(fig: go.Figure, height: int = 380) -> go.Figure:
    fig.update_layout(template=TEMPLATE, height=height, margin=dict(l=0, r=0, t=30, b=0), legend_title_text="")
    return fig


def line_chart(
    df: pd.DataFrame,
    x: str,
    y: str,
    *,
    color: str | None = None,
    y_label: str,
    log_y: bool = False,
    height: int = 380,
) -> go.Figure:
    fig = px.line(df, x=x, y=y, color=color, log_y=log_y)
    fig.update_xaxes(title_text="Date")
    fig.update_yaxes(title_text=y_label)
    fig.update_traces(hovertemplate="%{fullData.name}<br>%{x|%b %d, %Y}<br>" + y_label + ": %{y:,.1f}<extra></extra>")
    return style(fig, height)


def show(fig: go.Figure) -> None:
    st.plotly_chart(fig, width="stretch")


def metric_card(label: str, value: int | float, delta_pct: float | None = None, *, inverse: bool = True) -> None:
    """KPI tile; for COVID metrics a rise is bad so deltas are inverse-coloured by default."""
    delta = None if delta_pct is None else f"{delta_pct:+.1f}% vs prior 7 days"
    st.metric(label, f"{value:,.0f}", delta, delta_color="inverse" if inverse else "normal")


def empty_state(message: str) -> None:
    st.info(message)
    st.stop()
