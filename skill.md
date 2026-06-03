# WooCommerce BI Chat Copilot: Skill Definition

This document details the data aggregation, calculations, and retrieval skills utilized by the **WooCommerce BI Chat Copilot Agent** to deliver store insights.

---

## 1. Context Synthesis Skill (`build_store_context`)

This skill aggregates raw Polars DataFrames into a dense, clean text-based RAG database for LLM insertion. It limits token overhead while preserving descriptive stats.

### Data Inputs:
- `orders_df` (Polars DataFrame)
- `products_df` (Polars DataFrame)
- `customers_df` (Polars DataFrame)
- `store_name` (String)

### Output Format:
Returns a structured string detailing:
1. **Analysis Timeframe**: Minimum and maximum order dates.
2. **Sales Performance**: Total sales revenue, orders count, AOV, discounts, shipping, tax, and status frequency counts.
3. **Customer LTV Leaderboard**: Top 5 registered buyers by total spend.
4. **Cohort Statistics**: Repeat purchaser percentage (number of customers with > 1 order).
5. **Inventory Sync Alerts**: Products with stock $\le 10$ and top 5 products by lifetime sales.
6. **Category share**: Total units sold by product category grouping.

---

## 2. Period-over-Period (PoP) Comparison Skill

This skill calculates growth and decay dynamics comparing active date ranges to previous periods.

### Mathematical Formulas:
1. **Active Period Duration ($d$)**:
   $$d = D_{end} - D_{start}$$
2. **Prior Period Range**:
   $$D_{prior\_start} = D_{start} - d - 1\text{ day}$$
   $$D_{prior\_end} = D_{start} - 1\text{ day}$$
3. **Growth Rate ($G$)**:
   $$G = \frac{V_{active} - V_{prior}}{V_{prior}} \times 100$$
   *If $V_{prior} = 0$, $G$ defaults to $0.0$.*

### Applied Metrics:
- **Revenue Growth**: Net sales growth comparison.
- **Order Count Growth**: Growth in order velocity.
- **AOV Growth**: Change in transaction basket sizes.

---

## 3. Cohort Segmentation Skill

This skill identifies the ratio of first-time shoppers vs. brand-loyal repeat customers.

### Calculation Steps:
1. Filters out guest orders (`customer_id = 0`).
2. Performs a Polars group-by on `customer_email`, counting total orders per email.
3. Classifies customers:
   - **New Cohort**: Customers with exactly 1 order in the database.
   - **Returning Cohort**: Customers with $\ge 2$ orders in the database.
4. Calculates Repeat Purchase Rate:
   $$\text{Repeat Rate} = \frac{\text{Returning Customers}}{\text{Total Registered Customers}} \times 100$$

---

## 4. Inventory Performance & Health Alerting Skill

Monitors physical inventory levels to prevent stock-outs and identify high-velocity products.

### Alarm Conditions:
- **Out of Stock**: Products with `stock_status = "outofstock"` or `stock_quantity = 0`.
- **Low Stock Risk**: Managed inventory items with $1 \le \text{stock\_quantity} \le 10$.
- **High Velocity Products**: Products sorted descending by `total_sales` (lifetime units sold).
