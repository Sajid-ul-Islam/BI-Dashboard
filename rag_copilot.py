import streamlit as st
import polars as pl
from openai import OpenAI
from google import genai
from typing import Dict, List, Any, Optional
from typing import Tuple, Optional, Any


def build_store_context(orders_df: pl.DataFrame, products_df: pl.DataFrame, customers_df: pl.DataFrame, store_name: str) -> str:
    """
    Summarizes store data from Polars DataFrames into a concise text block for LLM RAG context.
    """
    if orders_df.is_empty():
        return "No sales or order history is currently loaded."

    # 1. Date Range
    min_date = orders_df["date"].min()
    max_date = orders_df["date"].max()
    date_range_str = f"From {min_date} to {max_date}" if min_date and max_date else "N/A"

    # 2. General Sales Performance (completed/processing only)
    completed_orders = orders_df.filter(pl.col("status").is_in(["completed", "processing"]))
    total_sales = completed_orders["total"].sum()
    total_orders = completed_orders.height
    aov = total_sales / total_orders if total_orders > 0 else 0.0
    
    total_discounts = completed_orders["discount_total"].sum()
    total_shipping = completed_orders["shipping_total"].sum()
    total_tax = completed_orders["total_tax"].sum()

    # 3. Order Status Counts
    status_counts = orders_df.group_by("status").agg(pl.len().alias("count")).to_dicts()
    status_str = ", ".join([f"{item['status']}: {item['count']}" for item in status_counts])

    # 4. Customer Metrics
    active_customers = orders_df.filter(pl.col("customer_id") != 0)
    customer_orders_count = active_customers.group_by("customer_email").agg(pl.len().alias("order_count"))
    total_registered_custs = customer_orders_count.height
    repeat_custs = customer_orders_count.filter(pl.col("order_count") > 1).height
    repeat_rate = (repeat_custs / total_registered_custs * 100) if total_registered_custs > 0 else 0.0

    # Top Customers by spending (registered ones)
    top_customers_df = (
        orders_df.filter(pl.col("customer_id") != 0)
        .group_by("customer_name", "customer_email")
        .agg(pl.col("total").sum().alias("total_spent"))
        .sort("total_spent", descending=True)
        .head(5)
    )
    top_cust_list = [f"- {r['customer_name']} ({r['customer_email']}): ${r['total_spent']:.2f}" for r in top_customers_df.to_dicts()]
    top_cust_str = "\n".join(top_cust_list) if top_cust_list else "None"

    # 5. Product Metrics
    # Top Products by sales count
    top_selling_prods = products_df.sort("total_sales", descending=True).head(5)
    top_prod_list = [f"- {r['name']} (Cat: {r['category']}): {r['total_sales']} units sold, Price: ${r['price']:.2f}" for r in top_selling_prods.to_dicts()]
    top_prod_str = "\n".join(top_prod_list) if top_prod_list else "None"

    # Low Stock Items (stock <= 10)
    low_stock_df = products_df.filter(
        (pl.col("stock_quantity") <= 10) & (pl.col("stock_status") != "outofstock")
    ).sort("stock_quantity").head(5)
    low_stock_list = [f"- {r['name']}: {r['stock_quantity']} units left" for r in low_stock_df.to_dicts()]
    low_stock_str = "\n".join(low_stock_list) if low_stock_list else "All products healthy stock level."

    # Revenue by category
    # Join orders and products requires line_items expansion. We can approximate category share via products sales
    # or just list categories and total products.
    category_summary = (
        products_df.group_by("category")
        .agg(
            pl.col("total_sales").sum().alias("units_sold"),
            pl.len().alias("product_count")
        )
        .sort("units_sold", descending=True)
    )
    cat_list = [f"- {r['category']}: {r['units_sold']} units across {r['product_count']} products" for r in category_summary.to_dicts()]
    cat_str = "\n".join(cat_list) if cat_list else "None"

    context = f"""WooCommerce Store Name: {store_name}
Analysis Timeframe: {date_range_str}

1. OVERALL SALES PERFORMANCE:
- Net Sales (excluding refunded/cancelled): ${total_sales:,.2f}
- Completed/Processing Orders: {total_orders:,}
- Average Order Value (AOV): ${aov:,.2f}
- Discount Code Reductions: ${total_discounts:,.2f}
- Shipping Collected: ${total_shipping:,.2f}
- Taxes Collected: ${total_tax:,.2f}
- All Order Status Breakdown: {status_str}

2. CUSTOMER METRICS:
- Total Active Registered Customers: {total_registered_custs}
- Repeat Customer Purchase Rate: {repeat_rate:.2f}% (customers placing > 1 order)
- Top 5 Registered Customers by Lifetime Value (LTV):
{top_cust_str}

3. INVENTORY & CATEGORY HEALTH:
- Top 5 Products by Sales:
{top_prod_str}
- Inventory Stock Alerts (Low Stock):
{low_stock_str}
- Category Performance (Total units sold):
{cat_str}
"""
    return context


def get_llm_client() -> Tuple[Optional[str], Optional[Any]]:
    """
    Identifies the active LLM key and initializes the corresponding client.
    Returns: (provider_name, client_object or api_key_string)
    """
    # Check session override key first
    if "override_llm_key" in st.session_state and st.session_state["override_llm_key"].strip():
        key = st.session_state["override_llm_key"].strip()
        provider = st.session_state.get("override_llm_provider", "Gemini")
        return provider, key

    # Check Streamlit secrets
    try:
        if "llm" in st.secrets:
            secrets = st.secrets["llm"]
            
            # Gemini Native SDK Check
            gemini_key = secrets.get("gemini_key", "")
            if gemini_key and gemini_key != "your_gemini_api_key_here":
                return "Gemini", gemini_key
                
            # OpenRouter Check
            or_key = secrets.get("openrouter_key", "")
            if or_key and or_key != "sk-or-v1-your_openrouter_key_here":
                return "OpenRouter", or_key
                
            # Groq Check
            groq_key = secrets.get("groq_key", "")
            if groq_key and groq_key != "gsk_your_groq_key_here":
                return "Groq", groq_key
    except Exception:
        pass
        
    return None, None


def query_llm(prompt: str, system_instruction: str) -> str:
    """
    Queries the active LLM provider with system instructions and user prompt.
    """
    provider, key = get_llm_client()
    
    if not provider or not key:
        return ("⚠️ **AI Assistant Mode is Offline**\n\n"
                "Please configure a valid API Key in the **Settings** or `.streamlit/secrets.toml` file to activate the AI BI Copilot RAG system.\n\n"
                "Once configured, you will be able to query your store's sales and customer database using natural language.")

    try:
        if provider == "Gemini":
            genai.configure(api_key=key)
            model = genai.GenerativeModel(
                model_name="gemini-1.5-flash",
                system_instruction=system_instruction
            )
            response = model.generate_content(prompt)
            return response.text
            
        elif provider == "OpenRouter":
            client = OpenAI(api_key=key, base_url="https://openrouter.ai/api/v1")
            response = client.chat.completions.create(
                model="google/gemini-2.5-flash", # Highly robust models for RAG
                messages=[
                    {"role": "system", "content": system_instruction},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=1000
            )
            return response.choices[0].message.content
            
        elif provider == "Groq":
            client = OpenAI(api_key=key, base_url="https://api.groq.com/openai/v1")
            response = client.chat.completions.create(
                model="llama-3.1-70b-versatile",
                messages=[
                    {"role": "system", "content": system_instruction},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=1000
            )
            return response.choices[0].message.content
            
    except Exception as e:
        return f"❌ **Error executing AI Query ({provider})**: {str(e)}\n\nPlease check your API key, internet connection, or quota limits."

    return "Unsupported LLM Provider configured."
