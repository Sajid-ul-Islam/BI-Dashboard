import streamlit as st
import plotly.io as pio
import plotly.graph_objects as go

# Define UI Colors
THEME_COLORS = {
    "primary": "#2563eb",      # Blue
    "secondary": "#10b981",    # Emerald Green
    "accent": "#f43f5e",       # Rose Red
    "warning": "#f59e0b",      # Amber/Yellow
    "info": "#06b6d4"          # Cyan/Teal
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
        background-color: var(--secondary-background-color);
        padding: 6px;
        border-radius: 12px;
        border: 1px solid var(--border-color);
    }}
    
    .stTabs [data-baseweb="tab"] {{
        height: 42px;
        white-space: pre-wrap;
        background-color: transparent;
        border-radius: 8px;
        color: var(--text-color);
        opacity: 0.7;
        font-weight: 500;
        font-size: 14px;
        border: none !important;
        padding: 0 16px;
        transition: all 0.2s ease;
    }}
    
    .stTabs [data-baseweb="tab"]:hover {{
        color: var(--text-color);
        opacity: 1;
        background-color: var(--secondary-background-color);
    }}
    
    .stTabs [aria-selected="true"] {{
        background-color: {THEME_COLORS['primary']} !important;
        color: white !important;
        font-weight: 600;
        box-shadow: 0 4px 12px rgba(37, 99, 235, 0.3);
    }}
    
    /* Clean up the sidebar */
    section[data-testid="stSidebar"] {{
        border-right: 1px solid var(--border-color);
    }}
    
    section[data-testid="stSidebar"] .block-container {{
        padding: 1.5rem !important;
    }}
    
    /* Card wrappers */
    div.metric-card-container {{
        background: var(--secondary-background-color);
        border: 1px solid var(--border-color);
        border-radius: 16px;
        padding: 24px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        margin-bottom: 20px;
        transition: transform 0.2s ease, border-color 0.2s ease;
    }}
    
    div.metric-card-container:hover {{
        transform: translateY(-2px);
        border-color: rgba(37, 99, 235, 0.3);
    }}
    
    /* Style headers */
    h1, h2, h3 {{
        font-weight: 700 !important;
        letter-spacing: -0.02em !important;
    }}
    
    h1 {{
        background: linear-gradient(135deg, var(--text-color) 40%, {THEME_COLORS['primary']} 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-size: 2.2rem !important;
        margin-bottom: 1.5rem !important;
    }}
    
    /* DataFrame styling overrides */
    .stDataFrame div[data-testid="stTable"] {{
        border: 1px solid var(--border-color) !important;
        border-radius: 12px !important;
        overflow: hidden !important;
    }}
    
    /* Text Inputs and Textareas */
    div[data-baseweb="input"] {{
        background-color: var(--secondary-background-color) !important;
        border: 1px solid var(--border-color) !important;
        border-radius: 8px !important;
    }}
    
    /* Style st.chat_message container with glassmorphic cards styles */
    [data-testid="stChatMessage"] {{
        background-color: var(--secondary-background-color) !important;
        border: 1px solid var(--border-color) !important;
        border-radius: 16px !important;
        padding: 16px !important;
        margin-bottom: 14px !important;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1) !important;
    }}
    
    /* Accent user messages */
    [data-testid="stChatMessage"]:-webkit-any([class*="user"], [data-testid*="user"]) {{
        background-color: rgba(37, 99, 235, 0.06) !important;
        border-left: 3px solid {THEME_COLORS['primary']} !important;
    }}
    
    /* Accent assistant messages */
    [data-testid="stChatMessage"]:-webkit-any([class*="assistant"], [data-testid*="assistant"]) {{
        background-color: rgba(16, 185, 129, 0.04) !important;
        border-left: 3px solid {THEME_COLORS['secondary']} !important;
    }}

    /* Style st.status widget details */
    div[data-testid="stStatusWidget"] {{
        background-color: var(--secondary-background-color) !important;
        border: 1px solid var(--border-color) !important;
        border-radius: 12px !important;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1) !important;
    }}
    
    /* Button Hover Micro-animations */
    .stButton > button {{
        border-radius: 8px !important;
        transition: transform 0.15s ease, background-color 0.2s ease, box-shadow 0.2s ease !important;
    }}
    .stButton > button:hover {{
        transform: translateY(-1.5px);
        box-shadow: 0 6px 15px rgba(37, 99, 235, 0.25) !important;
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
            text_color = "var(--text-color)"
            arrow = "•"
            
        trend_html = (
            f'<span style="background: {badge_color}; color: {text_color}; '
            f'padding: 4px 10px; border-radius: 20px; font-size: 13px; font-weight: 600; '
            f'display: inline-flex; align-items: center; gap: 4px; margin-left: auto;">'
            f'{arrow} {trend}</span>'
        )

    card_html = (
        f'<div class="metric-card-container">'
        f'<div style="display: flex; align-items: center; margin-bottom: 10px;">'
        f'<span style="color: var(--text-color); opacity: 0.7; font-size: 14px; font-weight: 500; '
        f'text-transform: uppercase; letter-spacing: 0.05em;">{title}</span>'
        f'{trend_html}</div>'
        f'<div style="font-size: 32px; font-weight: 700; color: var(--text-color); '
        f'letter-spacing: -0.02em;">{value}</div></div>'
    )
    return card_html


def apply_plotly_theme(fig):
    """
    Applies the dashboard's custom dark, sleek theme directly to a Plotly figure object.
    """
    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Outfit, sans-serif", size=12),
        margin=dict(t=40, b=40, l=40, r=20),
        xaxis=dict(
            zeroline=False
        ),
        yaxis=dict(
            zeroline=False
        ),
        legend=dict(
            bgcolor="rgba(0, 0, 0, 0)",
            bordercolor="rgba(0, 0, 0, 0)",
            borderwidth=1,
            font=dict(size=10)
        ),
        hoverlabel=dict(
            font=dict(size=12)
        )
    )
    # If traces exist, adjust lines and colors
    for trace in fig.data:
        # Check trace color settings and apply smooth curves
        if hasattr(trace, "line") and hasattr(trace.line, "shape"):
            trace.line.shape = "spline"
            trace.line.smoothing = 1.3
            
    return fig
