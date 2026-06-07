import streamlit as st
import time
from style_utils import inject_custom_css

# Inject styling
inject_custom_css()

st.header("Dashboard Configuration & Setup")

settings_col1, settings_col2 = st.columns(2)

with settings_col1:
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
    
    if st.button("Save & Apply LLM Settings", width="stretch"):
        st.session_state["override_llm_provider"] = provider
        st.session_state["override_llm_key"] = override_key
        st.success(f"LLM configurations applied! Provider set to: {provider}.")
        time.sleep(0.5)
        st.rerun()

with settings_col2:
    st.write("### 🔌 WooCommerce Connection Status")
    
    # Show active credentials status (from secrets.toml or manual fallback)
    from woocommerce_client import get_woocommerce_secrets
    wc_secrets = get_woocommerce_secrets()
    has_secrets = len(wc_secrets) > 0
    store_url = wc_secrets.get("store_url", "None")
        
    if has_secrets:
        st.success(f"🔗 Connected to WooCommerce store: **{store_url}**")
        st.write("Credentials are loaded dynamically from `.streamlit/secrets.toml` in the background.")
    else:
        st.warning("⚠️ No active WooCommerce credentials found in `.streamlit/secrets.toml`.")
        
    st.markdown(
        """
        **Connection Guide:**
        To sync the dashboard with your live e-commerce data:
        1. Open the file `.streamlit/secrets.toml` in your project folder.
        2. Set your WooCommerce API configurations:
        ```toml
        [woocommerce]
        store_url = "https://your-store.com"
        consumer_key = "ck_your_consumer_key_here"
        consumer_secret = "cs_your_consumer_secret_here"
        ```
        3. Make sure pretty permalinks are enabled on your WordPress site.
        """
    )
