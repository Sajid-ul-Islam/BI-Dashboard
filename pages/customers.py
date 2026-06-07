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
customers_df = st.session_state["customers_df"]

st.header("Customer Insights & CLV Analytics")

cc1, cc2, cc3 = st.columns(3)
with cc1:
    st.metric("Total Customer Database", f"{customers_df.height:,}")
with cc2:
    customer_ltv = customers_df.filter(pl.col("orders_count") > 0)
    avg_ltv = customer_ltv["total_spent"].mean() if customer_ltv.height > 0 else 0.0
    st.metric("Average Customer LTV", f"${avg_ltv:,.2f}")
with cc3:
    max_ltv = customers_df["total_spent"].max() if customers_df.height > 0 else 0.0
    st.metric("Highest Customer Lifetime Value", f"${max_ltv:,.2f}")

cust_col1, cust_col2 = st.columns([1, 1])

with cust_col1:
    st.subheader("Customer Lifetime Value (LTV) Distribution")
    if not customers_df.is_empty():
        active_custs = customers_df.filter(pl.col("orders_count") > 0).to_pandas()
        if not active_custs.empty:
            fig_hist = px.histogram(
                active_custs,
                x="total_spent",
                nbins=20,
                labels={"total_spent": "LTV / Total Spent ($)", "count": "Customers Count"},
                color_discrete_sequence=[THEME_COLORS["primary"]]
            )
            apply_plotly_theme(fig_hist)
            fig_hist.update_layout(yaxis_title="Count of Customers")
            st.plotly_chart(fig_hist, use_container_width=True)
        else:
            st.info("No active customer spending data found.")
    else:
        st.info("No customer data loaded.")

with cust_col2:
    st.subheader("New vs. Returning Customer Revenue Split")
    if not orders_df.is_empty():
        cust_counts = customers_df.select("email", "orders_count")
        
        orders_with_counts = orders_df.join(
            cust_counts, 
            left_on="customer_email", 
            right_on="email", 
            how="left"
        ).with_columns([
            pl.col("orders_count").fill_null(1).alias("orders_count")
        ])
        
        orders_cohort = orders_with_counts.with_columns([
            pl.when(pl.col("orders_count") > 1)
            .then(pl.lit("Returning"))
            .otherwise(pl.lit("New"))
            .alias("Cohort")
        ])
        
        cohort_rev = orders_cohort.group_by("Cohort").agg(pl.col("total").sum().alias("Revenue"))
        
        fig_cohort = px.pie(
            cohort_rev.to_pandas(),
            values="Revenue",
            names="Cohort",
            color="Cohort",
            color_discrete_map={"New": THEME_COLORS["accent"], "Returning": THEME_COLORS["primary"]},
            hole=0.5
        )
        apply_plotly_theme(fig_cohort)
        st.plotly_chart(fig_cohort, use_container_width=True)
    else:
        st.info("No sales data available.")

# Top Customers Table
st.subheader("Top Customers Leaderboard")
if not customers_df.is_empty():
    top_custs = (
        customers_df.sort("total_spent", descending=True)
        .with_columns(
            (pl.col("first_name") + " " + pl.col("last_name")).alias("Name")
        )
        .select("customer_id", "Name", "email", "orders_count", "total_spent")
        .head(10)
    )
    
    st.dataframe(
        top_custs.to_pandas(),
        column_config={
            "customer_id": st.column_config.NumberColumn("Customer ID", format="%d"),
            "Name": "Name",
            "email": "Email",
            "orders_count": st.column_config.NumberColumn("Total Orders", format="%d"),
            "total_spent": st.column_config.NumberColumn("Lifetime Value", format="$%.2f")
        },
        use_container_width=True,
        hide_index=True
    )
else:
    st.info("No customers records.")
