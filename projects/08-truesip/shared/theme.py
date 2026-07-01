"""
shared/theme.py — dark theme CSS injector for TrueSIP.

Matches the established dark design system from Projects 1/2/4/6:
  Background:  #0A0A0E
  Surface:     #13131A
  Card:        #1A1A24
  Accent:      #818CF8 (indigo)
  Text:        #F1F5F9 (primary), #94A3B8 (muted)
  Success:     #10B981
  Warning:     #F59E0B
  Danger:      #EF4444
  Fonts:       Space Grotesk (headings), Inter (body)
  Icons:       Bootstrap Icons via CDN

Usage (must be called ONCE near the top of dashboard/app.py, after
st.set_page_config):
    from shared.theme import inject_theme
    inject_theme()
"""

import streamlit as st

# Google Fonts: Space Grotesk (300–700) + Inter (400, 500, 600).
_FONT_IMPORT = (
    "https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@300;400;500;600;700"
    "&family=Inter:wght@400;500;600&display=swap"
)

# Bootstrap Icons CDN (v1.11.3 — pinned for stability).
_BOOTSTRAP_ICONS_CDN = (
    "https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.3/font/bootstrap-icons.min.css"
)

_CSS = """
/* ── TrueSIP dark theme ────────────────────────────────────────────────────── */

/* Fonts */
@import url('{font_import}');

/* Design tokens */
:root {{
  --bg:          #0A0A0E;
  --surface:     #13131A;
  --card:        #1A1A24;
  --border:      #2A2A38;
  --accent:      #818CF8;
  --accent-dark: #6366F1;
  --accent-glow: rgba(129, 140, 248, 0.15);
  --text:        #F1F5F9;
  --text-muted:  #94A3B8;
  --success:     #10B981;
  --warning:     #F59E0B;
  --danger:      #EF4444;
}}

/* Base */
html, body, [class*="css"] {{
  background-color: var(--bg) !important;
  color: var(--text) !important;
  font-family: 'Inter', sans-serif !important;
}}

/* Headings use Space Grotesk */
h1, h2, h3, h4, h5, h6,
.stMarkdown h1, .stMarkdown h2,
.stMarkdown h3, .stMarkdown h4 {{
  font-family: 'Space Grotesk', sans-serif !important;
  color: var(--text) !important;
  letter-spacing: -0.02em;
}}

/* Main container */
.main .block-container {{
  background-color: var(--bg) !important;
  padding-top: 2rem;
  max-width: 860px;
}}

/* Cards (st.container with border) — elevation + hover-lift */
div[data-testid="stVerticalBlock"] > div[data-testid="stVerticalBlock"] {{
  background: var(--card);
  border-radius: 12px;
  border: 1px solid var(--border);
  padding: 1.5rem;
  margin-bottom: 1rem;
  box-shadow: 0 1px 3px rgba(0,0,0,.4), 0 1px 2px rgba(0,0,0,.6);
  transition: transform 150ms ease, box-shadow 150ms ease, border-color 150ms ease;
}}
div[data-testid="stVerticalBlock"] > div[data-testid="stVerticalBlock"]:hover {{
  transform: translateY(-2px);
  box-shadow: 0 8px 32px rgba(129,140,248,0.12), 0 0 0 1px var(--accent-glow);
  border-color: rgba(129,140,248,0.3) !important;
}}

/* Sidebar */
[data-testid="stSidebar"] {{
  background-color: var(--surface) !important;
  border-right: 1px solid var(--border);
}}

/* Inputs */
input, textarea, select,
[data-baseweb="input"] input,
[data-baseweb="textarea"] textarea,
[data-baseweb="select"] div {{
  background-color: var(--surface) !important;
  color: var(--text) !important;
  border-color: var(--border) !important;
  border-radius: 8px !important;
}}
input:focus, textarea:focus {{
  border-color: var(--accent) !important;
  box-shadow: 0 0 0 2px var(--accent-glow) !important;
}}

/* Primary buttons */
.stButton > button[kind="primary"],
.stButton > button {{
  background: var(--accent-dark) !important;
  color: #fff !important;
  border: none !important;
  border-radius: 8px !important;
  font-family: 'Inter', sans-serif !important;
  font-weight: 500 !important;
  padding: 0.6rem 1.4rem !important;
  white-space: nowrap !important;
  transition: background 150ms ease, transform 100ms ease;
}}
.stButton > button:hover {{
  background: var(--accent) !important;
  transform: translateY(-1px);
}}
.stButton > button:active {{
  transform: translateY(0);
}}
/* Focus-visible ring for keyboard accessibility */
.stButton > button:focus-visible {{
  outline: 2px solid var(--accent) !important;
  outline-offset: 2px !important;
}}

/* Secondary / back buttons */
.stButton > button[kind="secondary"] {{
  background: transparent !important;
  color: var(--text-muted) !important;
  border: 1px solid var(--border) !important;
}}
.stButton > button[kind="secondary"]:hover {{
  color: var(--text) !important;
  border-color: var(--accent) !important;
  background: transparent !important;
}}

/* Select boxes */
[data-baseweb="select"] {{
  background-color: var(--surface) !important;
}}
[data-baseweb="select"] > div {{
  background-color: var(--surface) !important;
  border-color: var(--border) !important;
  border-radius: 8px !important;
}}

/* Sliders */
[data-testid="stSlider"] > div > div > div > div {{
  background: var(--accent) !important;
}}

/* Progress bars */
[data-testid="stProgress"] > div > div {{
  background: var(--accent) !important;
}}

/* Metric labels — elevation system */
[data-testid="stMetric"] {{
  background: var(--card);
  border: 1px solid var(--border);
  border-radius: 10px;
  padding: 0.8rem 1rem;
  box-shadow: 0 1px 3px rgba(0,0,0,.4), 0 1px 2px rgba(0,0,0,.6);
  transition: transform 150ms ease, box-shadow 150ms ease, border-color 150ms ease;
}}
[data-testid="stMetric"]:hover {{
  transform: translateY(-2px);
  box-shadow: 0 8px 24px rgba(0,0,0,.5), 0 0 0 1px var(--accent-glow);
  border-color: var(--accent) !important;
}}
[data-testid="stMetricLabel"] {{
  color: var(--text-muted) !important;
  font-size: 0.8rem !important;
}}
[data-testid="stMetricValue"] {{
  color: var(--text) !important;
  font-family: 'Space Grotesk', sans-serif !important;
}}
[data-testid="stMetricDelta"] svg {{
  display: none;
}}

/* Info / warning / error callouts */
[data-testid="stInfo"] {{
  background: rgba(99, 102, 241, 0.12) !important;
  border-left: 3px solid var(--accent) !important;
  color: var(--text) !important;
  border-radius: 0 8px 8px 0;
}}
[data-testid="stWarning"] {{
  background: rgba(245, 158, 11, 0.12) !important;
  border-left: 3px solid var(--warning) !important;
  border-radius: 0 8px 8px 0;
}}
[data-testid="stError"] {{
  background: rgba(239, 68, 68, 0.12) !important;
  border-left: 3px solid var(--danger) !important;
  border-radius: 0 8px 8px 0;
}}
[data-testid="stSuccess"] {{
  background: rgba(16, 185, 129, 0.12) !important;
  border-left: 3px solid var(--success) !important;
  border-radius: 0 8px 8px 0;
}}

/* Expanders — elevation */
[data-testid="stExpander"] {{
  background: var(--card) !important;
  border: 1px solid var(--border) !important;
  border-radius: 10px !important;
  box-shadow: 0 1px 3px rgba(0,0,0,.4), 0 1px 2px rgba(0,0,0,.6);
}}
[data-testid="stExpander"] summary {{
  color: var(--text-muted) !important;
  font-weight: 500;
}}
[data-testid="stExpander"] summary:hover {{
  color: var(--text) !important;
}}

/* DataFrames / tables */
[data-testid="stDataFrame"] {{
  border: 1px solid var(--border) !important;
  border-radius: 8px !important;
  overflow: hidden;
}}
thead tr th {{
  background: var(--surface) !important;
  color: var(--text-muted) !important;
  font-size: 0.8rem !important;
  text-transform: uppercase;
  letter-spacing: 0.05em;
}}
tbody tr:nth-child(even) td {{
  background: rgba(255,255,255,0.02) !important;
}}

/* Hide Streamlit native multipage nav (wizard uses session_state steps) */
[data-testid="stSidebarNavItems"],
[data-testid="collapsedControl"],
header[data-testid="stHeader"] {{
  display: none !important;
}}

/* Step indicator (custom class used in app.py) */
.truesip-step-bar {{
  display: flex;
  gap: 0.5rem;
  margin-bottom: 2rem;
  align-items: center;
}}
.truesip-step {{
  flex: 1;
  height: 3px;
  border-radius: 99px;
  background: var(--border);
  transition: background 300ms ease;
}}
.truesip-step.active {{
  background: var(--accent);
}}
.truesip-step.done {{
  background: var(--success);
}}

/* Utility helpers */
.text-muted {{ color: var(--text-muted) !important; }}
.text-accent {{ color: var(--accent) !important; }}
.text-success {{ color: var(--success) !important; }}
.text-warning {{ color: var(--warning) !important; }}
.text-danger  {{ color: var(--danger) !important; }}

/* Step bar — numbered label pill */
.truesip-step-label {{
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 4px;
}}
.truesip-step-num {{
  width: 24px;
  height: 24px;
  border-radius: 50%;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  font-size: 0.72rem;
  font-weight: 600;
  font-family: 'Space Grotesk', sans-serif;
  background: var(--border);
  color: var(--text-muted);
  transition: background 300ms ease, color 300ms ease;
}}
.truesip-step-num.active {{
  background: var(--accent);
  color: #fff;
}}
.truesip-step-num.done {{
  background: var(--success);
  color: #fff;
}}
.truesip-step-seg-label {{
  font-size: 0.65rem;
  color: var(--text-muted);
  font-family: 'Inter', sans-serif;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  white-space: nowrap;
}}
.truesip-step-seg-label.active {{
  color: var(--accent);
  font-weight: 600;
}}
.truesip-step-seg-label.done {{
  color: var(--success);
}}

/* Total SIP hero card */
.truesip-sip-hero {{
  background: linear-gradient(135deg, var(--card) 0%, rgba(99,102,241,0.12) 100%);
  border: 1px solid rgba(129,140,248,0.35);
  border-radius: 16px;
  padding: 1.75rem 2rem;
  margin-bottom: 1.5rem;
  box-shadow: 0 4px 24px rgba(129,140,248,0.12);
}}
.truesip-sip-hero-label {{
  font-family: 'Inter', sans-serif;
  font-size: 0.85rem;
  color: var(--text-muted);
  text-transform: uppercase;
  letter-spacing: 0.08em;
  margin-bottom: 0.25rem;
}}
.truesip-sip-hero-amount {{
  font-family: 'Space Grotesk', sans-serif;
  font-size: 2.6rem;
  font-weight: 700;
  color: var(--accent);
  line-height: 1.1;
  letter-spacing: -0.02em;
}}
.truesip-sip-hero-sub {{
  font-family: 'Inter', sans-serif;
  font-size: 0.85rem;
  color: var(--text-muted);
  margin-top: 0.35rem;
}}

/* Disclaimer callout — restyled smaller, consistent */
.truesip-disclaimer {{
  background: rgba(245,158,11,0.08);
  border-left: 3px solid rgba(245,158,11,0.5);
  border-radius: 0 8px 8px 0;
  padding: 0.55rem 0.9rem;
  font-size: 0.78rem;
  color: var(--text-muted);
  margin: 0.75rem 0;
  line-height: 1.5;
}}
.truesip-disclaimer strong {{ color: var(--text); }}

/* Bootstrap Icon check-mark helper (replaces emoji ✓) */
.truesip-check {{
  color: var(--success);
  font-size: 1rem;
}}

/* Volatility caveat tag on goal cards */
.truesip-vol-caveat {{
  display: inline-block;
  background: rgba(245,158,11,0.15);
  color: var(--warning);
  border: 1px solid rgba(245,158,11,0.3);
  border-radius: 6px;
  padding: 0.15rem 0.5rem;
  font-size: 0.75rem;
  margin-top: 0.25rem;
}}

/* Shimmer skeleton — scoped to the LLM explanation placeholder only */
@keyframes truesip-shimmer {{
  0%   {{ background-position: -200% 0; }}
  100% {{ background-position:  200% 0; }}
}}
.truesip-skeleton-line {{
  height: 14px;
  border-radius: 4px;
  background: linear-gradient(90deg,
    var(--border) 25%, var(--surface) 50%, var(--border) 75%);
  background-size: 200% 100%;
  animation: truesip-shimmer 1.5s infinite;
  margin: 10px 0;
}}
.truesip-skeleton-line.w-80 {{ width: 80%; }}
.truesip-skeleton-line.w-60 {{ width: 60%; }}
.truesip-skeleton-line.w-70 {{ width: 70%; }}
.truesip-skeleton-card {{ padding: 1rem 0; }}
"""


def inject_theme() -> None:
    """
    Inject the TrueSIP dark theme CSS + Bootstrap Icons into the current page.

    Must be called once per page render, immediately after st.set_page_config().
    Idempotent — safe to call multiple times (Streamlit deduplicates identical
    markdown injections within a session).
    """
    # Bootstrap Icons stylesheet
    st.markdown(
        f'<link rel="stylesheet" href="{_BOOTSTRAP_ICONS_CDN}">',
        unsafe_allow_html=True,
    )
    # Theme CSS
    css = _CSS.format(font_import=_FONT_IMPORT)
    st.markdown(f"<style>{css}</style>", unsafe_allow_html=True)
