import streamlit as st
import polars as pl
import plotly.graph_objects as go
import plotly.express as px
import datetime
from style_utils import inject_custom_css, render_kpi_card, apply_plotly_theme, THEME_COLORS

# Inject styling
inject_custom_css()

if "orders_df" not in st.session_state:
    st.warning("⚠️ Data connection lost. Please reload the dashboard.")
    st.stop()

orders_df = st.session_state["orders_df"]
products_df = st.session_state["products_df"]
customers_df = st.session_state["customers_df"]
store_name = st.session_state["store_name"]
is_demo = st.session_state["is_demo"]
kpis = st.session_state["kpis"]

# Format date range for dynamic titles
active_dates = st.session_state.get("active_date_range")
date_subtitle = ""
if active_dates and len(active_dates) == 2:
    start_str = active_dates[0].strftime("%b %d, %Y")
    end_str = active_dates[1].strftime("%b %d, %Y")
    date_subtitle = f"({start_str})" if start_str == end_str else f"({start_str} - {end_str})"

st.header("Overview Dashboard")

# Metric cards row
m_col1, m_col2, m_col3, m_col4 = st.columns(4)

with m_col1:
    st.markdown(
        render_kpi_card(
            "Total Revenue", 
            f"${kpis['sales']:,.2f}", 
            f"{kpis['sales_change']:+.1f}% vs prior period", 
            "up" if kpis['sales_change'] >= 0 else "down"
        ), 
        unsafe_allow_html=True
    )
with m_col2:
    st.markdown(
        render_kpi_card(
            "Orders Shipped", 
            f"{kpis.get('shipped', 0):,}", 
            f"{kpis.get('shipped_change', 0.0):+.1f}% vs prior period", 
            "up" if kpis.get('shipped_change', 0.0) >= 0 else "down"
        ), 
        unsafe_allow_html=True
    )
with m_col3:
    st.markdown(
        render_kpi_card(
            "Average Order Value", 
            f"${kpis['aov']:,.2f}", 
            f"{kpis['aov_change']:+.1f}% vs prior period", 
            "up" if kpis['aov_change'] >= 0 else "down"
        ), 
        unsafe_allow_html=True
    )
with m_col4:
    st.markdown(
        render_kpi_card(
            "Total Items Sold", 
            f"{kpis['items_sold']:,.0f}", 
            f"{kpis['items_sold_change']:+.1f}% vs prior period", 
            "up" if kpis['items_sold_change'] >= 0 else "down"
        ), 
        unsafe_allow_html=True
    )

st.write("")

# Visual Graphs Row
g_col1, g_col2 = st.columns([2, 1])

with g_col1:
    st.subheader(f"Revenue & Orders Trend {date_subtitle}")
    if not orders_df.is_empty():
        # Aggregate sales by date
        daily_stats = (
            orders_df.filter(pl.col("status").is_in(["completed", "processing"]))
            .group_by("date")
            .agg(
                pl.col("total").sum().alias("Revenue"),
                pl.len().alias("Orders")
            )
            .sort("date")
        )
        
        # Create interactive dual-axis chart
        fig_trend = go.Figure()
        # Revenue Area
        fig_trend.add_trace(go.Scatter(
            x=daily_stats["date"].to_list(),
            y=daily_stats["Revenue"].to_list(),
            name="Revenue ($)",
            fill='tozeroy',
            line=dict(color=THEME_COLORS["primary"], width=2.5),
            fillcolor='rgba(99, 102, 241, 0.1)'
        ))
        # Orders Line (secondary y-axis)
        fig_trend.add_trace(go.Scatter(
            x=daily_stats["date"].to_list(),
            y=daily_stats["Orders"].to_list(),
            name="Orders Count",
            line=dict(color=THEME_COLORS["secondary"], width=2, dash='dot'),
            yaxis="y2"
        ))
        
        fig_trend.update_layout(
            yaxis=dict(title="Revenue ($)"),
            yaxis2=dict(
                title="Orders",
                overlaying="y",
                side="right",
                gridcolor="rgba(0,0,0,0)"
            ),
            legend=dict(x=0.01, y=0.99, orientation="h")
        )
        apply_plotly_theme(fig_trend)
        st.plotly_chart(fig_trend, use_container_width=True)
    else:
        st.info("No sales data available for the selected timeframe.")

with g_col2:
    st.subheader(f"Order Status Breakdown {date_subtitle}")
    if not orders_df.is_empty():
        status_df = orders_df.group_by("status").agg(pl.len().alias("count"))
        
        # Map status colors
        colors_map = {
            "completed": THEME_COLORS["secondary"],
            "processing": THEME_COLORS["primary"],
            "refunded": THEME_COLORS["accent"],
            "cancelled": "#94a3b8"
        }
        colors = [colors_map.get(s, THEME_COLORS["info"]) for s in status_df["status"].to_list()]
        
        fig_pie = px.pie(
            status_df.to_pandas(), 
            values="count", 
            names="status",
            hole=0.6,
            color_discrete_sequence=colors
        )
        fig_pie.update_traces(textposition='inside', textinfo='percent+label')
        apply_plotly_theme(fig_pie)
        st.plotly_chart(fig_pie, use_container_width=True)
    else:
        st.info("No status data available.")

# Recent Orders Table
st.subheader("Recent Activity Stream")
if not orders_df.is_empty():
    recent_df = (
        orders_df.sort("date_created", descending=True)
        .select("order_id", "date_created", "customer_name", "total", "status", "items_count", "item_names")
        .head(8)
    )
    
    # Modern Column Configured DataFrame
    st.dataframe(
        recent_df.to_pandas(),
        column_config={
            "order_id": st.column_config.NumberColumn("Order ID", format="%d"),
            "date_created": st.column_config.TextColumn("Timestamp"),
            "customer_name": "Customer",
            "total": st.column_config.NumberColumn("Amount", format="$%.2f"),
            "status": st.column_config.TextColumn("Status"),
            "items_count": st.column_config.NumberColumn("Items"),
            "item_names": "Items Summary"
        },
        use_container_width=True,
        hide_index=True
    )