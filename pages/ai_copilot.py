import streamlit as st
import polars as pl
import time
from style_utils import inject_custom_css
from rag_copilot import build_store_context, get_llm_client, query_llm

# Inject styling
inject_custom_css()

if "orders_df" not in st.session_state:
    st.warning("⚠️ Data connection lost. Please reload the dashboard.")
    st.stop()

orders_df = st.session_state["orders_df"]
products_df = st.session_state["products_df"]
customers_df = st.session_state["customers_df"]
store_name = st.session_state["store_name"]

st.header("🤖 AI Business Intelligence Copilot (RAG)")
st.write(
    "Ask direct questions about your store's sales trends, high-performing categories, inventory risk, or repeat purchases. "
    "The RAG engine compiles your store metrics and customer details as ground-truth context for the LLM."
)

# Identify LLM Client Configuration
provider_name, client_key = get_llm_client()

if provider_name:
    st.success(f"🤖 Connected to LLM Copilot via **{provider_name} API**.")
else:
    st.warning("⚠️ **LLM Keys Missing**: No active API Key found. You can enter an override key in the **Settings** page to enable AI chat.")

# Show context summary in toggle accordion
store_context = build_store_context(orders_df, products_df, customers_df, store_name)
with st.expander("🔍 View AI RAG Context Data (Ground Truth)"):
    st.text(store_context)

st.write("---")

# Render Chat History
for chat in st.session_state["chat_history"]:
    with st.chat_message(chat["role"]):
        st.markdown(chat["content"])

# Suggestion Chips
st.write("💡 *Quick Queries:*")
s_col_1, s_col_2, s_col_3 = st.columns(3)

clicked_question = ""
with s_col_1:
    if st.button("Summarize sales trend & key KPIs", width="stretch"):
        clicked_question = "Summarize sales trend & key KPIs"
with s_col_2:
    if st.button("Identify inventory risk & low stock", width="stretch"):
        clicked_question = "Identify inventory risk & low stock"
with s_col_3:
    if st.button("How can we improve repeat customer rate?", width="stretch"):
        clicked_question = "How can we improve repeat customer rate based on our customer data?"

# Chat Input
user_input = st.chat_input("Ask the store data advisor anything...")

active_prompt = ""
if user_input:
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
    
    # Execute RAG & query LLM inside status container
    with st.status("Analyzing metrics and preparing response...") as status:
        status.write("Checking LLM credentials...")
        time.sleep(0.3)
        status.write("Formatting store context data package...")
        time.sleep(0.3)
        status.write("Sending query payload to generative AI model...")
        
        ai_response = query_llm(active_prompt, system_instruction)
        
        status.update(label="Analysis complete!", state="complete", expanded=False)
        
    # Append AI response to State
    st.session_state["chat_history"].append({"role": "assistant", "content": ai_response})
    st.rerun()

# Clear Chat History Button
if st.session_state["chat_history"]:
    st.write("")
    if st.button("🗑️ Clear Conversation History"):
        st.session_state["chat_history"] = []
        st.rerun()
