"""Business-facing Olist dashboard backed by the Gold layer or CSV exports."""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st
from plotly.subplots import make_subplots

sys.path.append(str(Path(__file__).resolve().parents[1]))

from _shared import (  # noqa: E402
    COLOR_SEQUENCE,
    DANGER,
    PRIMARY,
    SUCCESS,
    WARNING,
    apply_theme,
    brl,
    load_csv_or_db,
    pct,
    safe_sum,
)

st.set_page_config(
    page_title="Olist Business Dashboard",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.title("Olist Business Dashboard")
st.caption(
    "Answers: how is revenue trending, which categories and sellers drive it, "
    "and how reliable is delivery?"
)

needs_data: list[str] = []


@st.cache_data(ttl=300)
def load_view(name: str) -> pd.DataFrame:
    return load_csv_or_db(name)


try:
    sales = load_view("vw_sales_daily")
    delivery = load_view("vw_delivery_performance")
    rfm = load_view("vw_customer_rfm")
    category = load_view("vw_category_performance")
    seller = load_view("vw_seller_performance")
except Exception as exc:
    st.error(f"Could not load dashboard data: {exc}")
    st.stop()

sales["order_date"] = pd.to_datetime(sales["order_date"], errors="coerce")
delivery["month"] = pd.to_datetime(delivery["month"], errors="coerce")
for column in ("orders", "gross_value", "revenue", "freight"):
    if column in sales.columns:
        sales[column] = pd.to_numeric(sales[column], errors="coerce").fillna(0)
for column in ("delivered_orders", "late_orders", "late_rate_pct", "avg_delivery_days"):
    delivery[column] = pd.to_numeric(delivery[column], errors="coerce")
category["revenue"] = pd.to_numeric(category["revenue"], errors="coerce").fillna(0)
category["avg_review_score"] = pd.to_numeric(
    category["avg_review_score"], errors="coerce"
)
for column in ("revenue", "orders", "items", "freight"):
    seller[column] = pd.to_numeric(seller[column], errors="coerce").fillna(0)
for column in ("avg_review_score", "late_rate_pct"):
    seller[column] = pd.to_numeric(seller[column], errors="coerce")

# --- Sidebar filters -------------------------------------------------------
st.sidebar.header("Filters")
st.sidebar.caption(
    "Date filters apply to sales and delivery. Category applies to the "
    "category view. State applies to sellers. RFM is a snapshot and is not "
    "date-filtered."
)

valid_dates = sales["order_date"].dropna()
if valid_dates.empty:
    st.error("No sales rows are available.")
    st.stop()

min_date = valid_dates.min().date()
max_date = valid_dates.max().date()
date_range = st.sidebar.date_input(
    "Date range",
    value=(min_date, max_date),
    min_value=min_date,
    max_value=max_date,
)

category_options = sorted(category["category"].dropna().unique().tolist())
selected_categories = st.sidebar.multiselect(
    "Category", options=category_options, default=[]
)

state_options = sorted(seller["seller_state"].dropna().unique().tolist())
selected_states = st.sidebar.multiselect(
    "Seller state", options=state_options, default=[]
)

if isinstance(date_range, (tuple, list)) and len(date_range) == 2:
    start_date, end_date = date_range
else:
    start_date = end_date = date_range

sales_filtered = sales[
    (sales["order_date"].dt.date >= start_date)
    & (sales["order_date"].dt.date <= end_date)
].copy()
delivery_filtered = delivery[
    (delivery["month"].dt.date >= start_date)
    & (delivery["month"].dt.date <= end_date)
].copy()

# Category filters cannot be applied to sales/delivery/RFM: those views have no
# category column. State filters cannot be applied to sales/delivery/RFM either.
category_filtered = (
    category[category["category"].isin(selected_categories)].copy()
    if selected_categories
    else category.copy()
)
seller_filtered = (
    seller[seller["seller_state"].isin(selected_states)].copy()
    if selected_states
    else seller.copy()
)

if sales_filtered.empty:
    needs_data.append("vw_sales_daily (date range)")
if delivery_filtered.empty:
    needs_data.append("vw_delivery_performance (date range)")
if category_filtered.empty:
    needs_data.append("vw_category_performance (category filter)")
if seller_filtered.empty:
    needs_data.append("vw_seller_performance (state filter)")

# --- KPI calculations ------------------------------------------------------
total_revenue = safe_sum(sales_filtered["gross_value"])
total_orders = safe_sum(sales_filtered["orders"])
aov = total_revenue / total_orders if total_orders else None

delivery_sorted = delivery_filtered.sort_values("month")
if not delivery_sorted.empty:
    latest_delivery = delivery_sorted.iloc[-1]
    late_rate = float(latest_delivery["late_rate_pct"])
    latest_month_label = pd.Timestamp(latest_delivery["month"]).strftime("%b %Y")
    if len(delivery_sorted) >= 2:
        previous_delivery = delivery_sorted.iloc[-2]
        late_delta = late_rate - float(previous_delivery["late_rate_pct"])
        late_delta_text = f"{late_delta:+.2f} pp vs prior month"
    else:
        late_delta_text = None
else:
    late_rate = None
    latest_month_label = "<TBD>"
    late_delta_text = None
    needs_data.append("Late delivery rate")

rfm_raw = "customer_unique_id" in rfm.columns
if rfm.empty:
    unique_customers = None
    segment_counts = pd.DataFrame(columns=["segment", "customer_count"])
    needs_data.append("vw_customer_rfm")
elif rfm_raw:
    unique_customers = int(rfm["customer_unique_id"].nunique())
    segment_counts = (
        rfm.groupby("segment", as_index=False)
        .agg(customer_count=("customer_unique_id", "count"))
        .sort_values("customer_count", ascending=False)
    )
else:
    unique_customers = int(
        pd.to_numeric(
            rfm.get("customer_count", pd.Series(dtype=float)), errors="coerce"
        )
        .fillna(0)
        .sum()
    )
    segment_counts = rfm.copy()

sales_filtered["month"] = sales_filtered["order_date"].dt.to_period("M").dt.to_timestamp()
monthly = (
    sales_filtered.groupby("month", as_index=False)
    .agg(gross_value=("gross_value", "sum"), orders=("orders", "sum"))
    .sort_values("month")
)
monthly["aov"] = monthly["gross_value"] / monthly["orders"].replace(
    0, float("nan")
)

if len(monthly) >= 2:
    current_month = monthly.iloc[-1]
    previous_month = monthly.iloc[-2]
    revenue_delta = float(current_month["gross_value"] - previous_month["gross_value"])
    orders_delta = int(current_month["orders"] - previous_month["orders"])
    aov_delta = (
        float(current_month["aov"] - previous_month["aov"])
        if pd.notna(current_month["aov"]) and pd.notna(previous_month["aov"])
        else None
    )
    revenue_delta_text = f"{brl(revenue_delta)} vs prior month"
    orders_delta_text = f"{orders_delta:+,} vs prior month"
    aov_delta_text = f"{brl(aov_delta)} vs prior month" if aov_delta is not None else None
else:
    revenue_delta_text = None
    orders_delta_text = None
    aov_delta_text = None

# --- KPI row ---------------------------------------------------------------
has_sales = not sales_filtered.empty
revenue_value = brl(total_revenue) if has_sales else "<TBD>"
orders_value = f"{int(total_orders):,}" if has_sales else "<TBD>"
aov_value = brl(aov) if has_sales and aov is not None else "<TBD>"
unique_value = f"{unique_customers:,}" if unique_customers is not None else "<TBD>"

kpi_columns = st.columns(5)
kpi_columns[0].metric(
    "Total Revenue",
    revenue_value,
    revenue_delta_text,
)
kpi_columns[1].metric(
    "Total Orders",
    orders_value,
    orders_delta_text,
)
kpi_columns[2].metric(
    "Average Order Value",
    aov_value,
    aov_delta_text,
)
kpi_columns[3].metric(
    f"Late Delivery Rate ({latest_month_label})",
    pct(late_rate) if late_rate is not None else "<TBD>",
    late_delta_text,
    delta_color="inverse",
)
kpi_columns[4].metric(
    "Unique Customers",
    unique_value,
    help="RFM snapshot; date, category, and state filters do not apply.",
)
st.caption(
    "Headline value for the selected period, with month-over-month deltas "
    "where a previous period exists."
)

# --- Chart row 1 -----------------------------------------------------------
left, right = st.columns(2)

with left:
    st.subheader("Monthly revenue trend")
    if monthly.empty:
        st.info("<TBD> — no sales rows match the date range.")
    else:
        revenue_fig = px.line(
            monthly,
            x="month",
            y="gross_value",
            markers=True,
            color_discrete_sequence=[PRIMARY],
            labels={"month": "Month", "gross_value": "Gross value (BRL)"},
        )
        revenue_fig = apply_theme(revenue_fig, title="Monthly gross value")
        st.plotly_chart(revenue_fig, use_container_width=True)
    st.caption("Answers: is revenue growing, flat, or declining over time?")

with right:
    st.subheader("Top categories by revenue")
    top_categories = (
        category_filtered.sort_values("revenue", ascending=False).head(10).copy()
    )
    if top_categories.empty:
        st.info("<TBD> — no category rows match the filters.")
    else:
        category_fig = px.bar(
            top_categories,
            x="revenue",
            y="category",
            orientation="h",
            color="avg_review_score",
            color_continuous_scale=[DANGER, WARNING, SUCCESS],
            labels={
                "revenue": "Revenue (BRL)",
                "category": "Category",
                "avg_review_score": "Avg review",
            },
        )
        category_fig.update_layout(yaxis=dict(categoryorder="total ascending"))
        category_fig = apply_theme(category_fig, title="Top 10 categories")
        st.plotly_chart(category_fig, use_container_width=True)
    st.caption("Answers: which categories earn the most, and how well are they reviewed?")

# --- Chart row 2 -----------------------------------------------------------
left, right = st.columns(2)

with left:
    st.subheader("RFM segments")
    if segment_counts.empty:
        st.info("<TBD> — no RFM rows available.")
    else:
        rfm_fig = px.pie(
            segment_counts,
            names="segment",
            values="customer_count",
            hole=0.55,
            color_discrete_sequence=COLOR_SEQUENCE,
        )
        rfm_fig = apply_theme(rfm_fig, title="Customer segments")
        st.plotly_chart(rfm_fig, use_container_width=True)
    st.caption("Answers: how are customers distributed across RFM segments?")

with right:
    st.subheader("Delivery performance over time")
    dual_axis = make_subplots(specs=[[{"secondary_y": True}]])
    if delivery_sorted.empty:
        st.info("<TBD> — no delivery rows match the date range.")
    else:
        late_line = px.line(
            delivery_sorted,
            x="month",
            y="late_rate_pct",
            markers=True,
            color_discrete_sequence=[DANGER],
        )
        days_line = px.line(
            delivery_sorted,
            x="month",
            y="avg_delivery_days",
            markers=True,
            color_discrete_sequence=[PRIMARY],
        )
        for trace in late_line.data:
            trace.name = "Late rate (%)"
            dual_axis.add_trace(trace, secondary_y=False)
        for trace in days_line.data:
            trace.name = "Avg delivery days"
            dual_axis.add_trace(trace, secondary_y=True)
        dual_axis.update_yaxes(title_text="Late rate (%)", secondary_y=False)
        dual_axis.update_yaxes(title_text="Avg delivery days", secondary_y=True)
        dual_axis = apply_theme(dual_axis, title="Late rate vs delivery days")
        st.plotly_chart(dual_axis, use_container_width=True)
    st.caption("Answers: is delivery getting slower, and are late orders rising?")

# --- Full-width table ------------------------------------------------------
st.subheader("Top 20 sellers by revenue")
seller_table = seller_filtered.sort_values("revenue", ascending=False).head(20).copy()
if seller_table.empty:
    st.info("<TBD> — no seller rows match the filters.")
else:
    seller_display = seller_table[
        [
            "seller_id",
            "seller_state",
            "orders",
            "items",
            "revenue",
            "freight",
            "avg_review_score",
            "late_rate_pct",
        ]
    ]
    st.dataframe(
        seller_display,
        use_container_width=True,
        hide_index=True,
        column_config={
            "revenue": st.column_config.NumberColumn("Revenue", format="%.2f"),
            "freight": st.column_config.NumberColumn("Freight", format="%.2f"),
            "avg_review_score": st.column_config.NumberColumn(
                "Avg review", format="%.2f"
            ),
            "late_rate_pct": st.column_config.NumberColumn(
                "Late rate %", format="%.2f"
            ),
        },
    )
st.caption("Answers: which sellers generate the most revenue, and how risky are they?")

# --- Secondary table -------------------------------------------------------
st.subheader("RFM segment summary")
if rfm.empty:
    st.info("<TBD> — no RFM rows available.")
else:
    if rfm_raw:
        segment_summary = (
            rfm.groupby("segment", as_index=False)
            .agg(
                customers=("customer_unique_id", "count"),
                avg_recency_days=("recency_days", "mean"),
                avg_frequency=("frequency", "mean"),
                avg_monetary=("monetary", "mean"),
                total_monetary=("monetary", "sum"),
            )
            .sort_values("customers", ascending=False)
        )
    else:
        segment_summary = rfm.copy()
        segment_summary = segment_summary.rename(
            columns={"customer_count": "customers"}
        )
    st.dataframe(segment_summary, use_container_width=True, hide_index=True)
st.caption("Answers: how large and how valuable is each RFM segment?")

if needs_data:
    with st.expander("Needs data"):
        for item in sorted(set(needs_data)):
            st.write(f"- {item}")

st.caption(
    "Source: Gold views (vw_sales_daily, vw_delivery_performance, "
    "vw_customer_rfm, vw_category_performance, vw_seller_performance) or "
    "CSV exports in dashboards/data/."
)
