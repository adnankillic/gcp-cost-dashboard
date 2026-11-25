"""Shared helpers: data loading, colors, filters and chart builders."""

from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

DATA_DIR = Path(__file__).parent / "data"
TIB = 1024**4
GIB = 1024**3

# Categorical palette, fixed order. Max 7 named series, the rest goes to "Other".
PALETTE = ["#257de0", "#f47230", "#00b894", "#f2a600", "#ee7fac", "#008a17", "#6a4ce2"]
OTHER_COLOR = "#b4b4b4"
NET_COLOR = PALETTE[0]
CREDIT_COLOR = PALETTE[1]
MAX_SERIES = len(PALETTE)


# ---------- data ----------

@st.cache_data
def load_bq_daily() -> pd.DataFrame:
    df = pd.read_csv(DATA_DIR / "bq_cost_daily.csv", parse_dates=["creation_date"])
    return df.rename(columns={"creation_date": "date"})


@st.cache_data
def load_bq_top_jobs() -> pd.DataFrame:
    df = pd.read_csv(DATA_DIR / "bq_top_jobs.csv", parse_dates=["creation_date", "query_time"])
    return df.rename(columns={"creation_date": "date"})


@st.cache_data
def load_gcp_daily() -> pd.DataFrame:
    df = pd.read_csv(DATA_DIR / "gcp_cost_daily.csv", parse_dates=["usage_date"])
    return df.rename(columns={"usage_date": "date"})


# ---------- filters ----------

def grain_and_dates(df: pd.DataFrame, key: str):
    """Sidebar controls for grain and date range. Returns (grain, start, end)."""
    grain = st.sidebar.radio("Grain", ["Daily", "Monthly"], horizontal=True, key=f"{key}_grain")
    min_d, max_d = df["date"].min().date(), df["date"].max().date()
    picked = st.sidebar.date_input(
        "Date range", (min_d, max_d), min_value=min_d, max_value=max_d, key=f"{key}_dates"
    )
    start, end = (picked if isinstance(picked, tuple) and len(picked) == 2 else (min_d, max_d))
    return grain, pd.Timestamp(start), pd.Timestamp(end)


def multi_filter(df: pd.DataFrame, col: str, label: str, key: str) -> pd.DataFrame:
    options = sorted(df[col].dropna().unique())
    picked = st.sidebar.multiselect(label, options, placeholder="All", key=f"{key}_{col}")
    return df[df[col].isin(picked)] if picked else df


def add_period(df: pd.DataFrame, grain: str) -> pd.DataFrame:
    df = df.copy()
    if grain == "Monthly":
        df["period"] = df["date"].dt.to_period("M").dt.to_timestamp()
    else:
        df["period"] = df["date"]
    return df


def period_count(start: pd.Timestamp, end: pd.Timestamp, grain: str) -> int:
    if grain == "Monthly":
        return (end.year - start.year) * 12 + end.month - start.month + 1
    return (end - start).days + 1


# ---------- colors ----------

def color_map(full_df: pd.DataFrame, col: str, value: str) -> dict:
    """Color follows the entity: rank on the full (unfiltered) data, so
    filters never repaint a series. Top N get palette slots, rest are Other."""
    order = full_df.groupby(col)[value].sum().sort_values(ascending=False).index.tolist()
    return {name: PALETTE[i] for i, name in enumerate(order[:MAX_SERIES])}


def fold_other(df: pd.DataFrame, col: str, cmap: dict) -> pd.DataFrame:
    df = df.copy()
    df[col] = df[col].where(df[col].isin(cmap.keys()), "Other")
    return df


# ---------- formatting ----------

def usd(x: float) -> str:
    return f"${x:,.2f}"


def kpi_row(items: list[tuple[str, str]]):
    cols = st.columns(len(items))
    for c, (label, value) in zip(cols, items):
        c.metric(label, value)


# ---------- charts ----------

def _layout(fig: go.Figure, height: int = 380) -> go.Figure:
    fig.update_layout(
        height=height,
        margin=dict(l=10, r=10, t=10, b=10),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, x=0, title=None, traceorder="normal"),
        hovermode="x unified",
        bargap=0.25,
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
    )
    fig.update_yaxes(tickprefix="$", gridcolor="rgba(128,128,128,0.15)", zeroline=False)
    fig.update_xaxes(showgrid=False)
    return fig


def stacked_bar(df: pd.DataFrame, col: str, value: str, cmap: dict, grain: str) -> go.Figure:
    """Stacked bar over time. Biggest series at the bottom, Other on top."""
    data = fold_other(df, col, cmap).groupby(["period", col], as_index=False)[value].sum()
    order = [k for k in cmap if k in set(data[col])]
    if "Other" in set(data[col]):
        order.append("Other")

    fig = go.Figure()
    for name in order:
        part = data[data[col] == name]
        fig.add_bar(
            x=part["period"], y=part[value], name=name,
            marker_color=cmap.get(name, OTHER_COLOR),
            marker_line_width=1, marker_line_color="rgba(255,255,255,0.9)",
            hovertemplate=f"{name}: $%{{y:,.2f}}<extra></extra>",
        )

    if grain == "Monthly":
        totals = data.groupby("period")[value].sum()
        fig.add_scatter(
            x=totals.index, y=totals.values, mode="text",
            text=[usd(v) for v in totals.values], textposition="top center",
            showlegend=False, hoverinfo="skip", textfont=dict(size=11),
        )
    fig.update_layout(barmode="stack")
    _time_axis(fig, grain)
    return _layout(fig)


def net_vs_credits(df: pd.DataFrame, grain: str) -> go.Figure:
    data = df.groupby("period", as_index=False)[["net_cost_usd", "credits_usd"]].sum()
    fig = go.Figure()
    fig.add_bar(x=data["period"], y=data["net_cost_usd"], name="Net cost",
                marker_color=NET_COLOR, hovertemplate="Net cost: $%{y:,.2f}<extra></extra>")
    fig.add_bar(x=data["period"], y=data["credits_usd"], name="Credits",
                marker_color=CREDIT_COLOR, hovertemplate="Credits: $%{y:,.2f}<extra></extra>")
    if grain == "Monthly":
        fig.update_traces(texttemplate="$%{y:,.0f}", textposition="outside")
    fig.update_layout(barmode="group")
    _time_axis(fig, grain)
    return _layout(fig, 340)


def ranking_bar(df: pd.DataFrame, col: str, value: str, top: int = 15, color: str = NET_COLOR, height: int | None = None) -> go.Figure:
    data = df.groupby(col, as_index=False)[value].sum()
    data = data[data[value].abs() > 0.005].nlargest(top, value).iloc[::-1]
    labels = [n if len(n) <= 38 else n[:36] + "..." for n in data[col]]
    fig = go.Figure(go.Bar(
        x=data[value], y=labels, customdata=data[col], orientation="h", marker_color=color,
        text=[usd(v) for v in data[value]], textposition="outside", cliponaxis=False,
        hovertemplate="%{customdata}: $%{x:,.2f}<extra></extra>",
    ))
    fig = _layout(fig, height or max(220, 26 * len(data) + 40))
    fig.update_layout(hovermode="closest", showlegend=False, margin=dict(l=10, r=60, t=10, b=10))
    fig.update_xaxes(tickprefix="$", showgrid=True, gridcolor="rgba(128,128,128,0.15)", nticks=5)
    fig.update_yaxes(tickprefix="", showgrid=False)
    return fig


def _time_axis(fig: go.Figure, grain: str):
    if grain == "Monthly":
        fig.update_xaxes(dtick="M1", tickformat="%b %Y")
    else:
        fig.update_xaxes(tickformat="%b %d")

