# WooCommerce BI Chat Copilot: Agent Definition

This document outlines the architecture, capabilities, and system configuration for the **WooCommerce BI Chat Copilot Agent** integrated within the Business Intelligence Control Center.

---

## 1. Agent Overview

The **WooCommerce BI Chat Copilot** is a specialized Retrieval-Augmented Generation (RAG) assistant designed to help e-commerce managers, store owners, and analysts query their WooCommerce database using natural language. It functions as an E-commerce Business Intelligence AI Consultant.

### Agent Persona & Identity
- **Name**: WooCommerce BI Chat Copilot
- **Role**: AI Store Data Advisor & E-commerce Consultant
- **Tone**: Professional, analytical, concise, and growth-oriented.
- **Boundaries**: Strictly focuses on WooCommerce operations (orders, sales velocity, product catalogs, customer values). It does not answer questions outside this scope.

---

## 2. Agent Architecture

The agent is designed as a RAG pipeline utilizing **Polars** as a high-speed tabular processing engine to compile data structures, which are formatted into a compressed text-based RAG database (ground truth) and passed to the LLM.

```mermaid
graph TD
    User([User Prompt]) --> ChatUI[Streamlit Chat Page]
    ChatUI --> RAG_Compiler[rag_copilot.py: build_store_context]
    
    %% Polars Data Fetching
    OrdersDB[(Polars Orders DF)] --> RAG_Compiler
    ProductsDB[(Polars Products DF)] --> RAG_Compiler
    CustomersDB[(Polars Customers DF)] --> RAG_Compiler
    
    RAG_Compiler --> PromptBuilder[Construct System + Context + Prompt]
    PromptBuilder --> LLM_Client{LLM Routing}
    
    %% LLM Providers
    LLM_Client -->|Gemini SDK| GeminiAPI[Google Gemini 1.5/2.5 Flash]
    LLM_Client -->|Groq Client| GroqAPI[Llama 3.1 70B]
    LLM_Client -->|OpenRouter| OpenRouterAPI[Gemini 2.5 Flash]
    
    %% Response Cycle
    GeminiAPI --> ResponseHandler[Response Text]
    GroqAPI --> ResponseHandler
    OpenRouterAPI --> ResponseHandler
    
    ResponseHandler --> UI_Display[st.chat_message]
    UI_Display --> User
```

---

## 3. Core System Instructions

The LLM is prompted with the following system instruction matrix to guarantee reliability, truthfulness, and business relevance:

```text
You are a high-level E-commerce Business Intelligence AI Consultant for a WooCommerce store.
Below is the summary of the store's performance data. Use this data as the Ground Truth / Context to answer any user queries.
If the user asks questions that cannot be answered with this data, reply politely stating you are a WooCommerce BI copilot and don't have access to that information.

STORE CONTEXT DATA:
-------------------
{store_context}
-------------------

Rules:
1. Grounding: Do not invent or extrapolate statistics not directly present in the context.
2. Structure: Break down complex comparative answers using bullet points or tables.
3. Recommendations: Propose 1-2 actionable business actions if requested or when metrics show clear risk (e.g. low stock, high refunds).
4. Tone: Analytical, helpful, and direct. Avoid boilerplate fluff.
```

---

## 4. LLM Routing & Fallbacks

The agent dynamically evaluates available credentials to maintain service availability:

1. **Gemini API (Native)**: Selected by default if `gemini_key` is supplied. It uses the native Google GenAI SDK for low-latency, structured reasoning.
2. **OpenRouter API**: Chosen if `openrouter_key` is configured. Connects to `google/gemini-2.5-flash` or custom models.
3. **Groq API**: Chosen if `groq_key` is configured. Connects to `llama-3.1-70b-versatile` for high-speed open-source inferences.
4. **Offline Mode**: If no key is set, the agent responds with a helpful connection instruction modal to prompt the user to input keys in settings.
