import streamlit as st

from common import (CREDIT_COLOR, add_period, color_map, grain_and_dates, kpi_row,
                    load_gcp_daily, multi_filter, net_vs_credits, period_count,
                    ranking_bar, stacked_bar, usd)

st.title("GCP All Services Cost")
st.caption("Sample data, Aug to Oct 2026. Net cost = cost - credits. All values in USD.")

full = load_gcp_daily()

st.sidebar.header("Filters")
grain, start, end = grain_and_dates(full, "gcp")
df = full[(full["date"] >= start) & (full["date"] <= end)]
df = multi_filter(df, "service_description", "Service", "gcp")
df = multi_filter(df, "sku_description", "SKU", "gcp")
df = multi_filter(df, "project_alias", "Project", "gcp")
df = multi_filter(df, "location", "Region", "gcp")
df = add_period(df, grain)

if df.empty:
    st.info("No data for these filters.")
    st.stop()

# KPIs
n_periods = period_count(start, end, grain)
kpi_row([
    ("Cost", usd(df["cost_usd"].sum())),
    ("Credits", usd(df["credits_usd"].sum())),
    ("Net cost", usd(df["net_cost_usd"].sum())),
    (f"Avg {'daily' if grain == 'Daily' else 'monthly'} net cost", usd(df["net_cost_usd"].sum() / n_periods)),
])

st.subheader(f"{grain} net cost and credits")
st.plotly_chart(net_vs_credits(df, grain), width="stretch", key="gcp_chart_1")

st.subheader(f"{grain} net cost by service")
st.caption("Top 7 services, the rest is grouped as Other.")
svc_colors = color_map(full, "service_description", "net_cost_usd")
st.plotly_chart(stacked_bar(df, "service_description", "net_cost_usd", svc_colors, grain), width="stretch", key="gcp_chart_2")

st.subheader(f"{grain} net cost by SKU")
st.caption("Top 7 SKUs, the rest is grouped as Other.")
sku_colors = color_map(full, "sku_description", "net_cost_usd")
st.plotly_chart(stacked_bar(df, "sku_description", "net_cost_usd", sku_colors, grain), width="stretch", key="gcp_chart_3")

st.subheader(f"{grain} net cost by project")
proj_colors = color_map(full, "project_alias", "net_cost_usd")
st.plotly_chart(stacked_bar(df, "project_alias", "net_cost_usd", proj_colors, grain), width="stretch", key="gcp_chart_4")

rows = [
    ("Service", "service_description"),
    ("SKU", "sku_description"),
]
for i, (label, col) in enumerate(rows):
    left, right = st.columns(2)
    with left:
        st.subheader(f"{label} net cost")
        st.plotly_chart(ranking_bar(df, col, "net_cost_usd"), width="stretch", key=f"gcp_rank_net_{i}")
    with right:
        st.subheader(f"{label} credits")
        st.plotly_chart(ranking_bar(df, col, "credits_usd", color=CREDIT_COLOR), width="stretch", key=f"gcp_rank_credit_{i}")

with st.expander("Data table"):
    table = (
        df.groupby(["service_description", "sku_description"], as_index=False)[["cost_usd", "credits_usd", "net_cost_usd"]]
        .sum().sort_values("net_cost_usd", ascending=False)
    )
    st.dataframe(
        table, hide_index=True, width="stretch",
        column_config={
            "service_description": "Service",
            "sku_description": "SKU",
            "cost_usd": st.column_config.NumberColumn("Cost", format="$%.2f"),
            "credits_usd": st.column_config.NumberColumn("Credits", format="$%.2f"),
            "net_cost_usd": st.column_config.NumberColumn("Net cost", format="$%.2f"),
        },
    )
