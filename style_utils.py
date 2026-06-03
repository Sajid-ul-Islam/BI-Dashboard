import streamlit as st
import plotly.io as pio
import plotly.graph_objects as go

# Define UI Colors
THEME_COLORS = {
    "primary": "#6366f1",      # Indigo
    "secondary": "#10b981",    # Emerald Green
    "accent": "#f43f5e",       # Rose Red
    "warning": "#f59e0b",      # Amber/Yellow
    "info": "#06b6d4",         # Cyan/Teal
    "dark_bg": "#0b0f19",      # Sleek Deep Dark Navy/Slate
    "card_bg": "rgba(20, 24, 38, 0.7)", # Transparent glassmorphic card bg
    "card_border": "rgba(255, 255, 255, 0.06)",
    "text_main": "#f8fafc",     # Off-white
    "text_muted": "#94a3b8"     # Cool Gray
}

def inject_custom_css():
    """
    Injects custom CSS to theme Streamlit elements with a premium, responsive glassmorphic aesthetic.
    """
    css_content = f"""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;500;600;700&display=swap');
    
    /* Apply modern font globally */
    html, body, [class*="css"], .stApp {{
        font-family: 'Outfit', -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
        background-color: {THEME_COLORS['dark_bg']};
        color: {THEME_COLORS['text_main']};
    }}
    
    /* Make app full-width with clean padding */
    .block-container {{
        padding-top: 2rem !important;
        padding-bottom: 2rem !important;
        padding-left: 3rem !important;
        padding-right: 3rem !important;
        max-width: 100% !important;
    }}
    
    /* Style Streamlit Tabs for premium feeling */
    .stTabs [data-baseweb="tab-list"] {{
        gap: 12px;
        background-color: rgba(15, 23, 42, 0.3);
        padding: 6px;
        border-radius: 12px;
        border: 1px solid rgba(255, 255, 255, 0.04);
    }}
    
    .stTabs [data-baseweb="tab"] {{
        height: 42px;
        white-space: pre-wrap;
        background-color: transparent;
        border-radius: 8px;
        color: {THEME_COLORS['text_muted']};
        font-weight: 500;
        font-size: 14px;
        border: none !important;
        padding: 0 16px;
        transition: all 0.2s ease;
    }}
    
    .stTabs [data-baseweb="tab"]:hover {{
        color: {THEME_COLORS['text_main']};
        background-color: rgba(255, 255, 255, 0.03);
    }}
    
    .stTabs [aria-selected="true"] {{
        background-color: {THEME_COLORS['primary']} !important;
        color: white !important;
        font-weight: 600;
        box-shadow: 0 4px 12px rgba(99, 102, 241, 0.3);
    }}
    
    /* Clean up the sidebar */
    section[data-testid="stSidebar"] {{
        background-color: #070a13 !important;
        border-right: 1px solid rgba(255, 255, 255, 0.05);
    }}
    
    section[data-testid="stSidebar"] .block-container {{
        padding: 1.5rem !important;
    }}
    
    /* Card wrappers */
    div.metric-card-container {{
        background: {THEME_COLORS['card_bg']};
        border: 1px solid {THEME_COLORS['card_border']};
        border-radius: 16px;
        padding: 24px;
        box-shadow: 0 10px 30px -15px rgba(0,0,0,0.5);
        backdrop-filter: blur(12px);
        margin-bottom: 20px;
        transition: transform 0.2s ease, border-color 0.2s ease;
    }}
    
    div.metric-card-container:hover {{
        transform: translateY(-2px);
        border-color: rgba(99, 102, 241, 0.3);
    }}
    
    /* Style headers */
    h1, h2, h3 {{
        font-weight: 700 !important;
        letter-spacing: -0.02em !important;
    }}
    
    h1 {{
        background: linear-gradient(135deg, #ffffff 40%, {THEME_COLORS['primary']} 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-size: 2.2rem !important;
        margin-bottom: 1.5rem !important;
    }}
    
    /* DataFrame styling overrides */
    .stDataFrame div[data-testid="stTable"] {{
        border: 1px solid {THEME_COLORS['card_border']} !important;
        border-radius: 12px !important;
        overflow: hidden !important;
    }}
    
    /* Text Inputs and Textareas */
    div[data-baseweb="input"] {{
        background-color: rgba(15, 23, 42, 0.5) !important;
        border: 1px solid rgba(255, 255, 255, 0.08) !important;
        border-radius: 8px !important;
    }}
    
    /* Glowing chat bubbles for RAG system */
    .chat-bubble-user {{
        background-color: rgba(99, 102, 241, 0.15);
        border-left: 4px solid {THEME_COLORS['primary']};
        padding: 12px 16px;
        border-radius: 12px;
        margin-bottom: 12px;
        font-size: 14px;
        color: {THEME_COLORS['text_main']};
    }}
    
    .chat-bubble-ai {{
        background-color: rgba(255, 255, 255, 0.03);
        border-left: 4px solid {THEME_COLORS['secondary']};
        padding: 12px 16px;
        border-radius: 12px;
        margin-bottom: 12px;
        font-size: 14px;
        color: {THEME_COLORS['text_main']};
        line-height: 1.6;
    }}
    
    </style>
    """
    st.markdown(css_content, unsafe_allow_html=True)


def render_kpi_card(title: str, value: str, trend: str = "", trend_direction: str = "up") -> str:
    """
    Renders a premium HTML metric card with glassmorphism styling and custom trend indicators.
    Returns the HTML code to be rendered via st.markdown(html, unsafe_allow_html=True)
    """
    trend_html = ""
    if trend:
        if trend_direction == "up":
            badge_color = "rgba(16, 185, 129, 0.12)"
            text_color = THEME_COLORS["secondary"]
            arrow = "▲"
        elif trend_direction == "down":
            badge_color = "rgba(244, 63, 94, 0.12)"
            text_color = THEME_COLORS["accent"]
            arrow = "▼"
        else:
            badge_color = "rgba(148, 163, 184, 0.12)"
            text_color = THEME_COLORS["text_muted"]
            arrow = "•"
            
        trend_html = f"""
        <span style="
            background: {badge_color};
            color: {text_color};
            padding: 4px 10px;
            border-radius: 20px;
            font-size: 13px;
            font-weight: 600;
            display: inline-flex;
            align-items: center;
            gap: 4px;
            margin-left: auto;
        ">
            {arrow} {trend}
        </span>
        """

    card_html = f"""
    <div class="metric-card-container">
        <div style="display: flex; align-items: center; margin-bottom: 10px;">
            <span style="color: {THEME_COLORS['text_muted']}; font-size: 14px; font-weight: 500; text-transform: uppercase; letter-spacing: 0.05em;">{title}</span>
            {trend_html}
        </div>
        <div style="font-size: 32px; font-weight: 700; color: {THEME_COLORS['text_main']}; letter-spacing: -0.02em;">{value}</div>
    </div>
    """
    return card_html


def apply_plotly_theme(fig):
    """
    Applies the dashboard's custom dark, sleek theme directly to a Plotly figure object.
    """
    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Outfit, sans-serif", color=THEME_COLORS["text_main"], size=12),
        margin=dict(t=40, b=40, l=40, r=20),
        xaxis=dict(
            gridcolor="rgba(255, 255, 255, 0.05)",
            zeroline=False,
            color=THEME_COLORS["text_muted"]
        ),
        yaxis=dict(
            gridcolor="rgba(255, 255, 255, 0.05)",
            zeroline=False,
            color=THEME_COLORS["text_muted"]
        ),
        legend=dict(
            bgcolor="rgba(10, 15, 30, 0.6)",
            bordercolor="rgba(255, 255, 255, 0.05)",
            borderwidth=1,
            font=dict(size=10, color=THEME_COLORS["text_main"])
        ),
        hoverlabel=dict(
            bgcolor="#1e293b",
            bordercolor="rgba(255, 255, 255, 0.1)",
            font=dict(color=THEME_COLORS["text_main"], size=12)
        )
    )
    # If traces exist, adjust lines and colors
    for trace in fig.data:
        # Check trace color settings and apply smooth curves
        if hasattr(trace, "line") and hasattr(trace.line, "shape"):
            trace.line.shape = "spline"
            trace.line.smoothing = 1.3
            
    return fig
