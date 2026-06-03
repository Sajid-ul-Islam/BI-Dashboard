import streamlit as st
import time
from style_utils import inject_custom_css
from woocommerce_client import WooCommerceClient

# Inject styling
inject_custom_css()

st.header("Dashboard Configuration & Setup")

settings_col1, settings_col2 = st.columns(2)

@st.dialog("WooCommerce Connection Test")
def run_connection_test(url, ck, cs):
    st.write(f"Initiating handshake with WooCommerce REST API at `{url}`...")
    with st.spinner("Contacting API endpoints..."):
        client = WooCommerceClient(url, ck, cs)
        success, message = client.test_connection()
        
    if success:
        st.success(f"🎉 **Handshake Succeeded**\n\n{message}")
        st.info("You can safely apply these connection settings to run the dashboard in Live mode.")
    else:
        st.error(f"❌ **Handshake Failed**\n\n{message}")
        st.warning("Please check your store URL (ensure HTTPS), consumer credentials, and WordPress REST API permissions.")
        
    if st.button("Dismiss Result", use_container_width=True):
        st.rerun()

with settings_col1:
    st.write("### 🔌 WooCommerce Credentials Override")
    st.info("You can enter your credentials here to override configurations in `.streamlit/secrets.toml` dynamically.")
    
    override_url = st.text_input("WooCommerce Store URL", value=st.session_state["wc_override_url"] or "https://", placeholder="https://example.com")
    override_ck = st.text_input("Consumer Key (ck_...)", value=st.session_state["wc_override_ck"], type="password", placeholder="ck_12345...")
    override_cs = st.text_input("Consumer Secret (cs_...)", value=st.session_state["wc_override_cs"], type="password", placeholder="cs_12345...")
    
    test_col1, test_col2 = st.columns(2)
    with test_col1:
        if st.button("Test API Connection", use_container_width=True):
            if not override_url.startswith("http"):
                st.error("Invalid Store URL format.")
            elif not override_ck.startswith("ck_") or not override_cs.startswith("cs_"):
                st.error("Invalid Consumer Key/Secret credential formats.")
            else:
                run_connection_test(override_url, override_ck, override_cs)
                
    with test_col2:
        if st.button("Save & Apply Connection", use_container_width=True):
            st.session_state["wc_override_url"] = override_url
            st.session_state["wc_override_ck"] = override_ck
            st.session_state["wc_override_cs"] = override_cs
            st.session_state["use_demo"] = False
            st.cache_data.clear()
            st.success("Credentials saved to session! Reloading dashboard data...")
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
