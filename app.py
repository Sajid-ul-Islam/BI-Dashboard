import streamlit as st
import polars as pl
import datetime
import time
from typing import Tuple, Dict, Any

# Import custom modules
from woocommerce_client import load_woocommerce_data, WooCommerceClient, get_woocommerce_secrets
from style_utils import inject_custom_css, THEME_COLORS

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

# Modern Sidebar Logo (Streamlit 1.33.0+)
st.logo("assets/logo.svg", icon_image="assets/logo.svg")

# Sidebar Branding Header
st.sidebar.markdown(
    f"""
    <div style="display: flex; align-items: center; gap: 12px; margin-bottom: 25px; margin-top: -30px;">
        <span style="font-size: 20px; font-weight: 700; background: linear-gradient(135deg, var(--text-color), {THEME_COLORS['primary']}); -webkit-background-clip: text; -webkit-text-fill-color: transparent;">WooCommerce BI</span>
    </div>
    """,
    unsafe_allow_html=True
)

st.sidebar.subheader("Connection Mode")

# Determine default connection state
wc_secrets = get_woocommerce_secrets()
has_secrets = len(wc_secrets) > 0

# Choose connection mode
if has_secrets:
    mode_options = ["Live Store (secrets.toml)", "Demo Mode (Mock Data)"]
else:
    mode_options = ["Demo Mode (Mock Data)"]

selected_mode = st.sidebar.radio(
    "Data Source",
    options=mode_options,
    index=0,
    key="connection_mode_radio"
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
if st.sidebar.button("↻ Force Sync / Refresh", width="stretch"):
    st.cache_data.clear()
    if "last_loading_params" in st.session_state:
        del st.session_state["last_loading_params"]
    st.toast("Cache cleared, reloading fresh data...")
    time.sleep(0.5)
    st.rerun()

# Helper function to calculate KPIs with Period over Period analysis
def calculate_kpis(orders: pl.DataFrame, start: datetime.date, end: datetime.date) -> dict:
    if orders.is_empty():
        return {
            "sales": 0.0, "orders": 0, "aov": 0.0, "refund_rate": 0.0,
            "sales_change": 0.0, "orders_change": 0.0, "aov_change": 0.0,
            "items_sold": 0, "items_sold_change": 0.0
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
    
    # Refund Rate
    refunded_active = active_orders.filter(pl.col("status") == "refunded")["total"].sum()
    refund_rate = (refunded_active / (sales_active + refunded_active) * 100) if (sales_active + refunded_active) > 0 else 0.0

    # Total Items Sold
    items_active = valid_active["items_count"].sum()
    items_prior = valid_prior["items_count"].sum()
    items_change = ((items_active - items_prior) / items_prior * 100) if items_prior > 0 else 0.0

    return {
        "sales": sales_active,
        "orders": orders_active,
        "aov": aov_active,
        "refund_rate": refund_rate,
        "sales_change": sales_change,
        "orders_change": orders_change,
        "aov_change": aov_change,
        "items_sold": items_active,
        "items_sold_change": items_change
    }

# ----------------- DATA LOADING -----------------
# Optimized loading check to prevent redundant re-fetching during sidebar transitions
current_params = (selected_mode, date_range)
if "last_loading_params" not in st.session_state or st.session_state["last_loading_params"] != current_params or "orders_df" not in st.session_state:
    with st.spinner("Fetching and processing store data..."):
        # Load from secrets or mock
        data_dict = load_woocommerce_data(date_range, use_demo=st.session_state["use_demo"])
        
        st.session_state["orders_df"] = data_dict["orders"]
        st.session_state["products_df"] = data_dict["products"]
        st.session_state["customers_df"] = data_dict["customers"]
        st.session_state["store_name"] = data_dict["store_name"]
        st.session_state["is_demo"] = data_dict["is_demo"]
        st.session_state["last_loading_params"] = current_params
        
        # Calculate and cache KPIs
        st.session_state["kpis"] = calculate_kpis(data_dict["orders"], start_date, end_date)

orders_df = st.session_state["orders_df"]
store_name = st.session_state["store_name"]
is_demo = st.session_state["is_demo"]

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
    <div style="font-size: 11px; text-align: center; color: var(--text-color); opacity: 0.7; margin-top: 6px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;">
        {store_name}
    </div>
    """,
    unsafe_allow_html=True
)

if "api_error" in st.session_state and st.session_state["api_error"]:
    st.sidebar.error(st.session_state["api_error"])

# Define pages structure (Streamlit 1.35.0+)
pages = {
    "Dashboard": [
        st.Page("pages/overview.py", title="Overview", icon="📊"),
        st.Page("pages/sales.py", title="Sales Analysis", icon="📈"),
        st.Page("pages/customers.py", title="Customer Insights", icon="👥"),
        st.Page("pages/products.py", title="Product Performance", icon="📦"),
    ],
    "AI Assistant": [
        st.Page("pages/ai_copilot.py", title="AI Copilot", icon="🤖"),
    ],
    "Settings": [
        st.Page("pages/settings.py", title="Settings", icon="⚙️"),
    ],
}

pg = st.navigation(pages)
pg.run()