import streamlit as st
import polars as pl
import plotly.express as px
import plotly.graph_objects as go
import datetime
import time

# Import custom modules
from woocommerce_client import load_woocommerce_data, WooCommerceClient
from style_utils import inject_custom_css, render_kpi_card, apply_plotly_theme, THEME_COLORS
from rag_copilot import build_store_context, get_llm_client, query_llm

# Page Configuration
st.set_page_config(
    page_title="WooCommerce BI Dashboard",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Inject modern UI styling
inject_custom_css()

# Session State Initialization
if "use_demo" not in st.session_state:
    st.session_state["use_demo"] = True
if "chat_history" not in st.session_state:
    st.session_state["chat_history"] = []
if "override_llm_key" not in st.session_state:
    st.session_state["override_llm_key"] = ""
if "override_llm_provider" not in st.session_state:
    st.session_state["override_llm_provider"] = "Gemini"
if "wc_override_url" not in st.session_state:
    st.session_state["wc_override_url"] = ""
if "wc_override_ck" not in st.session_state:
    st.session_state["wc_override_ck"] = ""
if "wc_override_cs" not in st.session_state:
    st.session_state["wc_override_cs"] = ""

# Sidebar Settings
st.sidebar.markdown(
    f"""
    <div style="display: flex; align-items: center; gap: 12px; margin-bottom: 25px;">
        <span style="font-size: 32px;">📈</span>
        <span style="font-size: 20px; font-weight: 700; background: linear-gradient(135deg, #ffffff, {THEME_COLORS['primary']}); -webkit-background-clip: text; -webkit-text-fill-color: transparent;">WooCommerce BI</span>
    </div>
    """,
    unsafe_allow_html=True
)

st.sidebar.subheader("Connection Mode")

# Determine default connection state
has_secrets = False
try:
    if "woocommerce" in st.secrets:
        wc_secrets = st.secrets["woocommerce"]
        if (wc_secrets.get("store_url") != "https://your-store.com" and 
            wc_secrets.get("consumer_key") != "ck_your_consumer_key_here"):
            has_secrets = True
except Exception:
    pass

# Choose connection mode
mode_options = ["Demo Mode (Mock Data)", "Live Store (secrets.toml)"]
if st.session_state["wc_override_url"] and st.session_state["wc_override_ck"]:
    mode_options.append("Live Store (Manual Setup)")

selected_mode = st.sidebar.radio(
    "Data Source",
    options=mode_options,
    index=0 if st.session_state["use_demo"] else (1 if has_secrets else 0)
)

st.session_state["use_demo"] = (selected_mode == "Demo Mode (Mock Data)")

# Global Date Filters
st.sidebar.subheader("Date Filter")
date_filter_option = st.sidebar.selectbox(
    "Timeframe",
    options=["Last 30 Days", "Last 90 Days", "Year to Date", "All Time", "Custom Range"]
)

# Date calculations
today = datetime.date.today()
if date_filter_option == "Last 30 Days":
    start_date = today - datetime.timedelta(days=30)
    end_date = today
elif date_filter_option == "Last 90 Days":
    start_date = today - datetime.timedelta(days=90)
    end_date = today
elif date_filter_option == "Year to Date":
    start_date = datetime.date(today.year, 1, 1)
    end_date = today
elif date_filter_option == "All Time":
    start_date = today - datetime.timedelta(days=365) # Mock covers 1 year
    end_date = today
else: # Custom Range
    start_date = st.sidebar.date_input("Start Date", today - datetime.timedelta(days=60))
    end_date = st.sidebar.date_input("End Date", today)

date_range = (start_date, end_date)

# Refresh Button
if st.sidebar.button("↻ Force Sync / Refresh", use_container_width=True):
    st.cache_data.clear()
    st.toast("Cache cleared, refetching fresh data...")
    time.sleep(0.5)
    st.rerun()

# ----------------- DATA LOADING -----------------
with st.spinner("Fetching and processing store data..."):
    # If using manual credentials overrides
    if selected_mode == "Live Store (Manual Setup)":
        try:
            client = WooCommerceClient(
                st.session_state["wc_override_url"],
                st.session_state["wc_override_ck"],
                st.session_state["wc_override_cs"]
            )
            orders_df = client.get_orders(date_range)
            products_df = client.get_products()
            customers_df = client.get_customers()
            data_dict = {
                "orders": orders_df,
                "products": products_df,
                "customers": customers_df,
                "is_demo": False,
                "store_name": st.session_state["wc_override_url"].replace("https://", "").replace("http://", "").split("/")[0]
            }
        except Exception as e:
            st.sidebar.error(f"Manual connection failed: {e}")
            st.session_state["use_demo"] = True
            data_dict = load_woocommerce_data(date_range, use_demo=True)
    else:
        # Load from secrets or mock
        data_dict = load_woocommerce_data(date_range, use_demo=st.session_state["use_demo"])

orders_df = data_dict["orders"]
products_df = data_dict["products"]
customers_df = data_dict["customers"]
store_name = data_dict["store_name"]
is_demo = data_dict["is_demo"]

# Sidebar Connection Status Badge
status_color = "linear-gradient(135deg, #10b981, #059669)" if not is_demo else "linear-gradient(135deg, #f59e0b, #d97706)"
status_text = "Connected (Live)" if not is_demo else "Demo Mode Active"
st.sidebar.markdown(
    f"""
    <div style="
        background: {status_color};
        color: white;
        text-align: center;
        padding: 8px 12px;
        border-radius: 8px;
        font-weight: 600;
        font-size: 13px;
        margin-top: 15px;
        box-shadow: 0 4px 10px rgba(0,0,0,0.15);
    ">
        {status_text}
    </div>
    <div style="font-size: 12px; text-align: center; color: #94a3b8; margin-top: 6px;">
        {store_name}
    </div>
    """,
    unsafe_allow_html=True
)

# Header Section
st.title("Business Intelligence Control Center")

# Helper function to calculate KPIs with Period over Period analysis
def calculate_kpis(orders: pl.DataFrame, start: datetime.date, end: datetime.date) -> dict:
    if orders.is_empty():
        return {
            "sales": 0.0, "orders": 0, "aov": 0.0, "refunds": 0.0,
            "sales_change": 0.0, "orders_change": 0.0, "aov_change": 0.0
        }
        
    # Active Period filter
    active_orders = orders.filter((pl.col("date") >= start) & (pl.col("date") <= end))
    # Completed/Processing status only for revenue
    valid_active = active_orders.filter(pl.col("status").is_in(["completed", "processing"]))
    
    # Calculate Period length
    delta = end - start
    prior_start = start - delta - datetime.timedelta(days=1)
    prior_end = start - datetime.timedelta(days=1)
    
    # Prior Period filter
    prior_orders = orders.filter((pl.col("date") >= prior_start) & (pl.col("date") <= prior_end))
    valid_prior = prior_orders.filter(pl.col("status").is_in(["completed", "processing"]))
    
    # Revenue
    sales_active = valid_active["total"].sum()
    sales_prior = valid_prior["total"].sum()
    sales_change = ((sales_active - sales_prior) / sales_prior * 100) if sales_prior > 0 else 0.0
    
    # Order count
    orders_active = valid_active.height
    orders_prior = valid_prior.height
    orders_change = ((orders_active - orders_prior) / orders_prior * 100) if orders_prior > 0 else 0.0
    
    # Average Order Value (AOV)
    aov_active = sales_active / orders_active if orders_active > 0 else 0.0
    aov_prior = sales_prior / orders_prior if orders_prior > 0 else 0.0
    aov_change = ((aov_active - aov_prior) / aov_prior * 100) if aov_prior > 0 else 0.0
    
    # Refund Rate (using refund status or sums)
    refunded_active = active_orders.filter(pl.col("status") == "refunded")["total"].sum()
    refund_rate = (refunded_active / (sales_active + refunded_active) * 100) if (sales_active + refunded_active) > 0 else 0.0

    return {
        "sales": sales_active,
        "orders": orders_active,
        "aov": aov_active,
        "refund_rate": refund_rate,
        "sales_change": sales_change,
        "orders_change": orders_change,
        "aov_change": aov_change
    }

kpis = calculate_kpis(orders_df, start_date, end_date)

# Tabs Navigation
tab_overview, tab_sales, tab_customers, tab_products, tab_ai, tab_settings = st.tabs([
    "📊 Overview", 
    "📈 Sales Analysis", 
    "👥 Customer Insights", 
    "📦 Product Performance", 
    "🤖 AI BI Copilot (RAG)", 
    "⚙️ Settings"
])

# ----------------------------------------------------
# TAB 1: OVERVIEW
# ----------------------------------------------------
with tab_overview:
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
                "Orders Placed", 
                f"{kpis['orders']:,}", 
                f"{kpis['orders_change']:+.1f}% vs prior period", 
                "up" if kpis['orders_change'] >= 0 else "down"
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
        # Calculate Repeat Customer Rate
        valid_orders = orders_df.filter(pl.col("status").is_in(["completed", "processing"]) & (pl.col("customer_id") != 0))
        if valid_orders.height > 0:
            c_counts = valid_orders.group_by("customer_email").agg(pl.len().alias("count"))
            repeat_custs = c_counts.filter(pl.col("count") > 1).height
            total_custs = c_counts.height
            repeat_rate = (repeat_custs / total_custs * 100) if total_custs > 0 else 0.0
        else:
            repeat_rate = 0.0
            
        st.markdown(
            render_kpi_card(
                "Repeat Purchase Rate", 
                f"{repeat_rate:.1f}%", 
                "Registered Users", 
                "neutral"
            ), 
            unsafe_allow_html=True
        )

    st.write("")

    # Visual Graphs Row
    g_col1, g_col2 = st.columns([2, 1])
    
    with g_col1:
        st.subheader("Revenue & Orders Trend")
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
            
            # Create interactive dual-axis chart or line chart
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
        st.subheader("Order Status Breakdown")
        if not orders_df.is_empty():
            status_df = orders_df.group_by("status").agg(pl.len().alias("count"))
            
            # Map status colors
            colors_map = {
                "completed": THEME_COLORS["secondary"],
                "processing": THEME_COLORS["primary"],
                "refunded": THEME_COLORS["accent"],
                "cancelled": THEME_COLORS["text_muted"]
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
        
        # Style dataframe cells
        recent_pandas = recent_df.to_pandas()
        recent_pandas["total"] = recent_pandas["total"].apply(lambda val: f"${val:.2f}")
        recent_pandas.columns = ["Order ID", "Timestamp", "Customer", "Amount", "Status", "Items", "Products purchased"]
        st.dataframe(recent_pandas, use_container_width=True, hide_index=True)
    else:
        st.info("No recent orders.")

# ----------------------------------------------------
# TAB 2: SALES & OPERATIONS
# ----------------------------------------------------
with tab_sales:
    st.subheader("Sales Breakdown & Performance Matrix")
    
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

# ----------------------------------------------------
# TAB 3: CUSTOMER INSIGHTS
# ----------------------------------------------------
with tab_customers:
    st.subheader("Customer Metrics & CLV Analytics")
    
    cc1, cc2, cc3 = st.columns(3)
    with cc1:
        # Total registered customers
        st.metric("Total Customer Database", f"{customers_df.height:,}")
    with cc2:
        # Average LTV of customers with orders
        customer_ltv = customers_df.filter(pl.col("orders_count") > 0)
        avg_ltv = customer_ltv["total_spent"].mean() if customer_ltv.height > 0 else 0.0
        st.metric("Average Customer LTV", f"${avg_ltv:,.2f}")
    with cc3:
        # Max customer spend
        max_ltv = customers_df["total_spent"].max() if customers_df.height > 0 else 0.0
        st.metric("Highest Customer Lifetime Value", f"${max_ltv:,.2f}")

    cust_col1, cust_col2 = st.columns([1, 1])
    
    with cust_col1:
        st.subheader("Customer Lifetime Value (LTV) Distribution")
        if not customers_df.is_empty():
            # Filter to active customers only
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
            # Group orders by customer. If they have only 1 order overall they are New, else Returning.
            # (In a real scenario, we calculate this dynamically per order based on history, 
            # here we can approximate by joining the orders with customer database counts)
            cust_counts = customers_df.select("email", "orders_count")
            
            orders_with_counts = orders_df.join(
                cust_counts, 
                left_on="customer_email", 
                right_on="email", 
                how="left"
            ).with_columns([
                # Fill null counts with 1 (guests or customers not in DB)
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

    # Top Customers Table
    st.subheader("Top Customers Leaderboard")
    if not customers_df.is_empty():
        top_custs = (
            customers_df.sort("total_spent", descending=True)
            .select("customer_id", "first_name", "last_name", "email", "orders_count", "total_spent")
            .head(10)
        )
        top_custs_pd = top_custs.to_pandas()
        top_custs_pd["Name"] = top_custs_pd["first_name"] + " " + top_custs_pd["last_name"]
        top_custs_pd = top_custs_pd[["customer_id", "Name", "email", "orders_count", "total_spent"]]
        top_custs_pd["total_spent"] = top_custs_pd["total_spent"].apply(lambda v: f"${v:,.2f}")
        top_custs_pd.columns = ["Customer ID", "Name", "Email", "Total Orders", "Lifetime Value"]
        st.dataframe(top_custs_pd, use_container_width=True, hide_index=True)
    else:
        st.info("No customers records.")

# ----------------------------------------------------
# TAB 4: PRODUCT PERFORMANCE
# ----------------------------------------------------
with tab_products:
    st.subheader("Product & Inventory Health Analysis")
    
    # Metrics
    pc1, pc2, pc3 = st.columns(3)
    with pc1:
        st.metric("Total Catalog Items", f"{products_df.height:,}")
    with pc2:
        out_of_stock = products_df.filter(pl.col("stock_status") == "outofstock").height
        st.metric("Out of Stock Products", f"{out_of_stock}")
    with pc3:
        low_stock = products_df.filter((pl.col("stock_quantity") <= 10) & (pl.col("stock_quantity") > 0)).height
        st.metric("Low Stock Items (<=10)", f"{low_stock}")

    p_col1, p_col2 = st.columns(2)
    
    with p_col1:
        st.subheader("Top 8 Products by Units Sold")
        if not products_df.is_empty():
            top_sales = products_df.sort("total_sales", descending=True).head(8).to_pandas()
            
            fig_prod = px.bar(
                top_sales,
                x="total_sales",
                y="name",
                orientation="h",
                color="total_sales",
                color_continuous_scale="Purples",
                labels={"total_sales": "Units Sold", "name": "Product Name"}
            )
            # Order bars descending
            fig_prod.update_layout(yaxis={'categoryorder':'total ascending'}, coloraxis_showscale=False)
            apply_plotly_theme(fig_prod)
            st.plotly_chart(fig_prod, use_container_width=True)
            
    with p_col2:
        st.subheader("Product Categories Revenue Distribution")
        if not products_df.is_empty():
            cat_sales = (
                products_df.with_columns(
                    (pl.col("price") * pl.col("total_sales")).alias("category_rev")
                )
                .group_by("category")
                .agg(pl.col("category_rev").sum().alias("Revenue"))
            )
            
            fig_cat = px.pie(
                cat_sales.to_pandas(),
                values="Revenue",
                names="category",
                hole=0.5,
                color_discrete_sequence=px.colors.qualitative.Pastel
            )
            apply_plotly_theme(fig_cat)
            st.plotly_chart(fig_cat, use_container_width=True)

    # Catalog & Inventory List
    st.subheader("Product Catalog & Inventory Sync")
    
    inv_filter = st.radio(
        "Filter Inventory Status",
        options=["All Products", "Low Stock & Out of Stock", "Out of Stock Only"],
        horizontal=True
    )
    
    inv_df = products_df.select("product_id", "name", "category", "price", "stock_quantity", "stock_status", "total_sales")
    
    if inv_filter == "Low Stock & Out of Stock":
        inv_df = inv_df.filter((pl.col("stock_quantity") <= 10) | (pl.col("stock_status") == "outofstock"))
    elif inv_filter == "Out of Stock Only":
        inv_df = inv_df.filter(pl.col("stock_status") == "outofstock")
        
    inv_pd = inv_df.to_pandas()
    inv_pd["price"] = inv_pd["price"].apply(lambda v: f"${v:,.2f}")
    inv_pd.columns = ["Product ID", "Product Name", "Category", "Active Price", "Stock Quantity", "Stock Status", "Lifetime Units Sold"]
    
    st.dataframe(inv_pd, use_container_width=True, hide_index=True)

# ----------------------------------------------------
# TAB 5: AI BI COPILOT (RAG)
# ----------------------------------------------------
with tab_ai:
    st.subheader("Conversational AI Copilot (Retrieval-Augmented)")
    st.write(
        "Ask direct questions about your store's sales trends, high-performing categories, inventory risk, or repeat purchases. "
        "The RAG engine feeds your live/demo statistics as context directly to the LLM to get highly personalized insights."
    )

    # Identify LLM Client Configuration
    provider_name, client_key = get_llm_client()
    
    if provider_name:
        st.success(f"🤖 Connected to LLM Copilot via **{provider_name} API**.")
    else:
        st.warning("⚠️ **LLM Keys Missing**: No active API Key found in `secrets.toml` or connection settings. You can enter an override key in the **Settings** tab to enable AI chat.")

    # Show context summary in toggle accordion
    store_context = build_store_context(orders_df, products_df, customers_df, store_name)
    with st.expander("🔍 View AI RAG Context Data (Ground Truth)"):
        st.text(store_context)

    st.write("---")

    # Render Chat History
    chat_container = st.container()
    with chat_container:
        for chat in st.session_state["chat_history"]:
            if chat["role"] == "user":
                st.markdown(f'<div class="chat-bubble-user"><b>You:</b><br>{chat["content"]}</div>', unsafe_allow_html=True)
            else:
                st.markdown(f'<div class="chat-bubble-ai"><b>AI BI Copilot:</b><br>{chat["content"]}</div>', unsafe_allow_html=True)

    # Suggestion Chips
    st.write("💡 *Quick Queries:*")
    s_col_1, s_col_2, s_col_3 = st.columns(3)
    
    clicked_question = ""
    with s_col_1:
        if st.button("Summarize sales trend & key KPIs", use_container_width=True):
            clicked_question = "Summarize sales trend & key KPIs"
    with s_col_2:
        if st.button("Identify inventory risk & low stock", use_container_width=True):
            clicked_question = "Identify inventory risk & low stock"
    with s_col_3:
        if st.button("How can we improve repeat customer rate?", use_container_width=True):
            clicked_question = "How can we improve repeat customer rate based on our customer data?"

    # Chat Input form
    with st.form("chat_form", clear_on_submit=True):
        user_input = st.text_input("Ask the store data advisor anything...", placeholder="e.g. Which product category generates the highest revenue?")
        submit_chat = st.form_submit_button("Send Query 🚀")

    # Execute Chat
    active_prompt = ""
    if submit_chat and user_input.strip():
        active_prompt = user_input.strip()
    elif clicked_question:
        active_prompt = clicked_question

    if active_prompt:
        # Append User Message to State
        st.session_state["chat_history"].append({"role": "user", "content": active_prompt})
        
        # Build prompt & system instruction
        system_instruction = (
            f"You are a high-level E-commerce Business Intelligence AI Consultant for a WooCommerce store called '{store_name}'.\n"
            "Below is the summary of the store's performance data. Use this data as the Ground Truth / Context to answer any user queries.\n"
            "If the user asks questions that cannot be answered with this data, reply politely stating you are a WooCommerce BI copilot and don't have access to that information.\n\n"
            "STORE CONTEXT DATA:\n"
            "-------------------\n"
            f"{store_context}\n"
            "-------------------\n\n"
            "Keep your answers professional, concise, and structured. Provide actionable suggestions to improve the business where relevant."
        )
        
        with st.spinner("Analyzing metrics and preparing response..."):
            ai_response = query_llm(active_prompt, system_instruction)
            
        # Append AI response to State
        st.session_state["chat_history"].append({"role": "assistant", "content": ai_response})
        st.rerun()

    # Clear Chat History Button
    if st.session_state["chat_history"]:
        if st.button("🗑️ Clear Conversation History"):
            st.session_state["chat_history"] = []
            st.rerun()

# ----------------------------------------------------
# TAB 6: SETTINGS
# ----------------------------------------------------
with tab_settings:
    st.subheader("Dashboard Integrations & Setup")
    
    settings_col1, settings_col2 = st.columns(2)
    
    with settings_col1:
        st.write("### 🔌 WooCommerce Credentials Override")
        st.info("You can enter your credentials here to override placeholders in `secrets.toml` without modifying the files.")
        
        override_url = st.text_input("WooCommerce Store URL", value=st.session_state["wc_override_url"] or "https://", placeholder="https://example.com")
        override_ck = st.text_input("Consumer Key (ck_...)", value=st.session_state["wc_override_ck"], type="password", placeholder="ck_12345...")
        override_cs = st.text_input("Consumer Secret (cs_...)", value=st.session_state["wc_override_cs"], type="password", placeholder="cs_12345...")
        
        test_col1, test_col2 = st.columns(2)
        with test_col1:
            if st.button("Test API Connection", use_container_width=True):
                if not override_url.startswith("http"):
                    st.error("Invalid Store URL format.")
                elif not override_ck.startswith("ck_") or not override_cs.startswith("cs_"):
                    st.error("Invalid Key/Secret credentials format.")
                else:
                    with st.spinner("Testing API..."):
                        test_client = WooCommerceClient(override_url, override_ck, override_cs)
                        success, message = test_client.test_connection()
                        if success:
                            st.success(message)
                        else:
                            st.error(message)
        with test_col2:
            if st.button("Save & Apply Connection", use_container_width=True):
                st.session_state["wc_override_url"] = override_url
                st.session_state["wc_override_ck"] = override_ck
                st.session_state["wc_override_cs"] = override_cs
                st.session_state["use_demo"] = False
                st.cache_data.clear()
                st.success("Credentials saved to session! Refreshing dashboard...")
                time.sleep(1)
                st.rerun()
                
        if st.session_state["wc_override_url"]:
            if st.button("Clear Credentials Overrides", use_container_width=True):
                st.session_state["wc_override_url"] = ""
                st.session_state["wc_override_ck"] = ""
                st.session_state["wc_override_cs"] = ""
                st.session_state["use_demo"] = True
                st.cache_data.clear()
                st.success("Manual overrides cleared. Reverting to default...")
                time.sleep(1)
                st.rerun()

    with settings_col2:
        st.write("### 🤖 Generative AI (LLM) Settings")
        st.info("Set an API key override to enable the RAG copilot directly from the dashboard UI.")
        
        provider = st.selectbox(
            "AI Provider",
            options=["Gemini", "Groq", "OpenRouter"],
            index=["Gemini", "Groq", "OpenRouter"].index(st.session_state["override_llm_provider"])
        )
        
        key_placeholder = "Enter your API Key..."
        if provider == "Gemini":
            key_placeholder = "Enter Gemini API Key (e.g. AIzaSy...)"
        elif provider == "Groq":
            key_placeholder = "Enter Groq Key (e.g. gsk_...)"
        elif provider == "OpenRouter":
            key_placeholder = "Enter OpenRouter Key (e.g. sk-or-v1-...)"
            
        override_key = st.text_input("API Key Override", value=st.session_state["override_llm_key"], type="password", placeholder=key_placeholder)
        
        if st.button("Save & Apply LLM Settings", use_container_width=True):
            st.session_state["override_llm_provider"] = provider
            st.session_state["override_llm_key"] = override_key
            st.success(f"LLM configurations applied! Provider set to: {provider}.")
            time.sleep(0.5)
            st.rerun()
            
        st.write("")
        st.markdown(
            """
            **Setup Guide:**
            1. **WooCommerce**: Go to your WordPress Dashboard -> *WooCommerce* -> *Settings* -> *Advanced* -> *REST API* -> *Add Key*. Make sure permissions are set to **Read** or **Read/Write**.
            2. **LLM**: Get a free API Key from [Google AI Studio](https://aistudio.google.com/) for Gemini, or register on [Groq Console](https://console.groq.com/) / [OpenRouter](https://openrouter.ai/).
            """
        )
