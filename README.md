---
title: BI Dashboard
emoji: 📊
colorFrom: blue
colorTo: indigo
sdk: streamlit
sdk_version: "1.42.0"
app_file: app.py
pinned: false
---

# WooCommerce Business Intelligence & RAG Dashboard

A modern, production-grade Business Intelligence (BI) Dashboard for WooCommerce built in Streamlit. Powered by **Polars** for lightning-fast tabular data processing, **Plotly** for responsive and interactive visualizations, and an integrated **AI RAG (Retrieval-Augmented Generation) system** to query e-commerce statistics using natural language.

---

## Key Features

1. **Double Mode Operations**:
   - **Demo Mode**: Loads pre-generated, realistic 12-month transaction histories, product catalogs, and customer metrics so you can test all features instantly.
   - **Live Sync Mode**: Direct secure queries to the WooCommerce REST API using consumer keys.
2. **Advanced BI KPIs**:
   - Total Revenue, Order counts, AOV, and Repeat customer rates.
   - **Period-over-Period (PoP) comparison engine**: Computes growth/decay indicators (+% or -%) dynamically comparing the selected date range to the equivalent preceding period.
3. **Responsive Visualizations**:
   - Interactive dual-axis charts showing Revenue vs Orders trends over time.
   - Hourly sales velocity curves and weekday sales density bar charts.
   - New vs Returning customer revenue shares.
   - Dynamic inventory catalog listing with quick alerts (low-stock or out-of-stock items).
4. **LLM RAG Chat Copilot**:
   - Seamlessly synthesizes your store's sales trends, top buyers, inventory health, and category revenue into a structured text database.
   - Integrates with **Google Gemini SDK**, **Groq**, and **OpenRouter** to answer questions like: *"Which category has the highest sales?"* or *"What is my repeat customer purchase rate and how do we improve it?"*

---

## File Architecture

- **[app.py](file:///g:/BI%20Dashboard/app.py)**: Main entry point setting up the multi-tab layout, global date filter sidebars, and tab renders.
- **[woocommerce_client.py](file:///g:/BI%20Dashboard/woocommerce_client.py)**: Polars-powered WooCommerce API Client and robust synthetic data generator.
- **[style_utils.py](file:///g:/BI%20Dashboard/style_utils.py)**: Custom CSS styles (Glassmorphism containers, Outfit font, glowing badges) and custom metric card functions.
- **[rag_copilot.py](file:///g:/BI%20Dashboard/rag_copilot.py)**: Retrieves data insights, formats the RAG prompt, and manages LLM API interfaces.
- **[requirements.txt](file:///g:/BI%20Dashboard/requirements.txt)**: List of dependencies.

---

## Quick Start Installation

### 1. Clone & Set Up Directory
Open your terminal in the dashboard root directory (`g:\BI Dashboard`).

### 2. Install Dependencies
Install all package requirements via pip:
```bash
pip install -r requirements.txt
```

### 3. Start the Streamlit Server
Run the local Streamlit application:
```bash
streamlit run app.py
```
This will spin up a local server (typically at `http://localhost:8501`) and automatically launch a window in your web browser.

---

## API & Credentials Integration

You can set up WooCommerce credentials and LLM keys in two ways:

### Method A: Streamlit Secrets (Recommended)
Edit the gitignored secrets file at `.streamlit/secrets.toml`.

```toml
[woocommerce]
store_url = "https://your-store-domain.com"
consumer_key = "ck_your_actual_consumer_key_here"
consumer_secret = "cs_your_actual_consumer_secret_here"

[llm]
gemini_key = "AIzaSy..." # Your Google AI Studio API key
# Or fallbacks:
openrouter_key = "sk-or-v1-..."
groq_key = "gsk_..."
```

### Method B: Dashboard Settings Tab (No File Edits)
Navigate to the **Settings** tab directly inside the running dashboard to securely enter your WooCommerce keys and generative keys. These parameters will be stored in your active browser session.

#### 🔑 Generating WooCommerce API Keys:
1. Log in to your WordPress dashboard.
2. Go to **WooCommerce** -> **Settings** -> **Advanced** -> **REST API**.
3. Click **Add Key**.
4. Set description, select user, and set permissions to **Read** (Read/Write is also supported, but Read-only is recommended for security).
5. Click **Generate API Key**. Copy the **Consumer Key** and **Consumer Secret**.
