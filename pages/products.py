import streamlit as st
import polars as pl
import plotly.express as px
from style_utils import inject_custom_css, apply_plotly_theme, THEME_COLORS

# Inject styling
inject_custom_css()

if "orders_df" not in st.session_state:
    st.warning("⚠️ Data connection lost. Please reload the dashboard.")
    st.stop()

products_df = st.session_state["products_df"]

st.header("Product Performance & Catalog Sync")

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
        fig_prod.update_layout(yaxis={'categoryorder':'total ascending'}, coloraxis_showscale=False)
        apply_plotly_theme(fig_prod)
        st.plotly_chart(fig_prod, use_container_width=True)
    else:
        st.info("No product sales data available.")
        
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
    else:
        st.info("No category data available.")

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
    
st.dataframe(
    inv_df.to_pandas(),
    column_config={
        "product_id": st.column_config.NumberColumn("Product ID", format="%d"),
        "name": "Product Name",
        "category": "Category",
        "price": st.column_config.NumberColumn("Active Price", format="$%.2f"),
        "stock_quantity": st.column_config.NumberColumn("Stock Quantity", format="%d"),
        "stock_status": st.column_config.TextColumn("Stock Status"),
        "total_sales": st.column_config.NumberColumn("Lifetime Units Sold", format="%d")
    },
    use_container_width=True,
    hide_index=True
)
