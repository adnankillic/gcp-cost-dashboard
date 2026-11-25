import streamlit as st

from common import (GIB, TIB, add_period, color_map, grain_and_dates, kpi_row,
                    load_bq_daily, load_bq_top_jobs, multi_filter, period_count,
                    stacked_bar, usd)

st.title("BigQuery Cost")
st.caption("Sample data, Aug to Oct 2026. Cost = billed bytes x $6.25 per TiB (on-demand pricing).")

full = load_bq_daily()
jobs = load_bq_top_jobs()

st.sidebar.header("Filters")
grain, start, end = grain_and_dates(full, "bq")
df = full[(full["date"] >= start) & (full["date"] <= end)]
df = multi_filter(df, "user_type", "User type", "bq")
df = multi_filter(df, "user_alias", "User", "bq")
df = multi_filter(df, "statement_type", "Statement type", "bq")
df = add_period(df, grain)

if df.empty:
    st.info("No data for these filters.")
    st.stop()

# KPIs
n_periods = period_count(start, end, grain)
kpi_row([
    ("Bytes processed", f"{df['bytes_processed'].sum() / TIB:,.2f} TiB"),
    ("Cost", usd(df["cost_usd"].sum())),
    (f"Avg {'daily' if grain == 'Daily' else 'monthly'} cost", usd(df["cost_usd"].sum() / n_periods)),
    ("Query count", f"{df['query_count'].sum():,}"),
])

# Cost over time by user
st.subheader(f"{grain} cost by user")
user_colors = color_map(full, "user_alias", "cost_usd")
st.plotly_chart(stacked_bar(df, "user_alias", "cost_usd", user_colors, grain), width="stretch", key="bigquery_chart_1")

# Cost by statement type
st.subheader(f"{grain} cost by statement type")
type_colors = color_map(full, "statement_type", "cost_usd")
st.plotly_chart(stacked_bar(df, "statement_type", "cost_usd", type_colors, grain), width="stretch", key="bigquery_chart_2")

# User table
st.subheader("User cost")
users = (
    df.groupby(["user_alias", "user_type"], as_index=False)
    .agg(bytes_processed=("bytes_processed", "sum"), cost_usd=("cost_usd", "sum"), query_count=("query_count", "sum"))
    .sort_values("cost_usd", ascending=False)
)
users["gib_processed"] = users["bytes_processed"] / GIB
users["cost_share"] = users["cost_usd"] / users["cost_usd"].sum()
users["cost_per_query"] = users["cost_usd"] / users["query_count"]
st.dataframe(
    users[["user_alias", "user_type", "gib_processed", "cost_usd", "cost_share", "query_count", "cost_per_query"]],
    hide_index=True, width="stretch",
    column_config={
        "user_alias": "User",
        "user_type": "Type",
        "gib_processed": st.column_config.NumberColumn("GiB processed", format="%.0f"),
        "cost_usd": st.column_config.NumberColumn("Cost", format="$%.2f"),
        "cost_share": st.column_config.ProgressColumn("Share", format="percent", min_value=0, max_value=1),
        "query_count": st.column_config.NumberColumn("Queries", format="%d"),
        "cost_per_query": st.column_config.NumberColumn("Cost / query", format="$%.4f"),
    },
)

# Top jobs
st.subheader("Most expensive queries")
st.caption("Top 500 jobs of the whole period by cost. Query text is replaced with a sample per statement type.")
j = jobs[(jobs["date"] >= start) & (jobs["date"] <= end)]
for col in ["user_type", "user_alias", "statement_type"]:
    picked = st.session_state.get(f"bq_{col}")
    if picked:
        j = j[j[col].isin(picked)]
j = j.sort_values("cost_usd", ascending=False).copy()
j["gib_processed"] = j["total_bytes_processed"] / GIB
j["slot_sec"] = j["total_slot_ms"] / 1000
st.dataframe(
    j[["query_time", "user_alias", "statement_type", "is_child_job", "gib_processed", "slot_sec", "cost_usd", "statement_text", "job_id"]],
    hide_index=True, width="stretch", height=420,
    column_config={
        "query_time": st.column_config.DatetimeColumn("Time", format="YYYY-MM-DD HH:mm"),
        "user_alias": "User",
        "statement_type": "Type",
        "is_child_job": st.column_config.CheckboxColumn("Script step"),
        "gib_processed": st.column_config.NumberColumn("GiB processed", format="%.1f"),
        "slot_sec": st.column_config.NumberColumn("Slot sec", format="%.0f"),
        "cost_usd": st.column_config.NumberColumn("Cost", format="$%.2f"),
        "statement_text": st.column_config.TextColumn("Query (sample)", width="large"),
        "job_id": "Job id",
    },
)
