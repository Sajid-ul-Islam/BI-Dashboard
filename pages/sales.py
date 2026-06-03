import streamlit as st
import polars as pl
import plotly.express as px
from style_utils import inject_custom_css, apply_plotly_theme, THEME_COLORS

# Inject styling
inject_custom_css()

if "orders_df" not in st.session_state:
    st.warning("⚠️ Data connection lost. Please reload the dashboard.")
    st.stop()

orders_df = st.session_state["orders_df"]

st.header("Sales & Operations Analysis")

# Performance metric split
sc1, sc2, sc3, sc4 = st.columns(4)
with sc1:
    total_gross = orders_df.filter(pl.col("status").is_in(["completed", "processing"]))["total"].sum()
    st.metric("Gross Sales Revenue", f"${total_gross:,.2f}")
with sc2:
    total_dis = orders_df.filter(pl.col("status").is_in(["completed", "processing"]))["discount_total"].sum()
    st.metric("Discounts Given", f"${total_dis:,.2f}")
with sc3:
    total_ship = orders_df.filter(pl.col("status").is_in(["completed", "processing"]))["shipping_total"].sum()
    st.metric("Shipping Fees Collected", f"${total_ship:,.2f}")
with sc4:
    total_tax = orders_df.filter(pl.col("status").is_in(["completed", "processing"]))["total_tax"].sum()
    st.metric("Tax Collected", f"${total_tax:,.2f}")
    
s_col1, s_col2 = st.columns(2)

with s_col1:
    st.subheader("Sales Performance by Day of Week")
    if not orders_df.is_empty():
        # Extract day of week
        orders_dow = (
            orders_df.filter(pl.col("status").is_in(["completed", "processing"]))
            .with_columns(
                pl.col("datetime_created").dt.weekday().alias("weekday")
            )
        )
        
        # Map weekday indices to names
        weekday_names = {1: "Mon", 2: "Tue", 3: "Wed", 4: "Thu", 5: "Fri", 6: "Sat", 7: "Sun"}
        
        dow_grouped = (
            orders_dow.group_by("weekday")
            .agg(
                pl.col("total").sum().alias("Revenue"),
                pl.len().alias("Orders")
            )
            .sort("weekday")
        )
        
        # Map weekdays
        dow_pandas = dow_grouped.to_pandas()
        dow_pandas["Day"] = dow_pandas["weekday"].map(weekday_names)
        
        fig_dow = px.bar(
            dow_pandas,
            x="Day",
            y="Revenue",
            color="Revenue",
            text_auto=".2s",
            color_continuous_scale="Viridis",
            labels={"Revenue": "Revenue ($)"}
        )
        apply_plotly_theme(fig_dow)
        fig_dow.update_layout(coloraxis_showscale=False)
        st.plotly_chart(fig_dow, use_container_width=True)
    else:
        st.info("No sales data available.")
        
with s_col2:
    st.subheader("Hourly Sales Velocity")
    if not orders_df.is_empty():
        orders_hour = (
            orders_df.filter(pl.col("status").is_in(["completed", "processing"]))
            .with_columns(
                pl.col("datetime_created").dt.hour().alias("hour")
            )
        )
        
        hour_grouped = (
            orders_hour.group_by("hour")
            .agg(pl.col("total").sum().alias("Revenue"))
            .sort("hour")
        )
        
        fig_hour = px.line(
            hour_grouped.to_pandas(),
            x="hour",
            y="Revenue",
            markers=True,
            labels={"hour": "Hour of Day (24h)", "Revenue": "Sales Revenue ($)"}
        )
        apply_plotly_theme(fig_hour)
        fig_hour.update_traces(line_color=THEME_COLORS["info"], fill="tozeroy", fillcolor="rgba(6, 182, 212, 0.05)")
        fig_hour.update_layout(xaxis=dict(tickmode="linear", tick0=0, dtick=2))
        st.plotly_chart(fig_hour, use_container_width=True)
    else:
        st.info("No sales data available.")
