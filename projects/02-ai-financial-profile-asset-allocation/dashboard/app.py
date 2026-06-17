"""
app.py  —  AI-Powered Financial Profile & Asset Allocation Tool
Streamlit dashboard powered by the Grok API (xAI).
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

import plotly.graph_objects as go
import streamlit as st

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from allocation_engine import get_allocation
from fund_recommender import build_fund_recommendations
from risk_profiler import (
    QUESTIONS,
    compute_risk_score,
    get_risk_label,
    score_to_gauge_color,
)

# ── Page config ───────────────────────────────────────────────────────────────

st.set_page_config(
    page_title="AI Asset Allocation",
    page_icon="💹",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Plotly theme (mirrors Project 1) ─────────────────────────────────────────

CHART_FONT  = "#E2E8F0"
HOVER_FONT  = "#1F2937"
GRID_COLOR  = "#4B5563"
ACCENT_GREEN  = "#10B981"
ACCENT_PURPLE = "#818CF8"
TRANSPARENT   = "rgba(0,0,0,0)"

ASSET_COLORS = {
    "equity":       "#818CF8",   # purple
    "debt":         "#10B981",   # green
    "gold":         "#F59E0B",   # amber
    "alternatives": "#F97316",   # orange
}

PLOTLY_BASE = dict(
    paper_bgcolor=TRANSPARENT,
    plot_bgcolor=TRANSPARENT,
    font=dict(color=CHART_FONT, family="Inter, sans-serif", size=13),
    hoverlabel=dict(bgcolor="white", font_size=13, font_color=HOVER_FONT),
)

# ── API key resolution ────────────────────────────────────────────────────────

def resolve_api_key() -> str | None:
    # 1. Streamlit Cloud secrets
    try:
        key = st.secrets.get("XAI_API_KEY")
        if key:
            return key
    except Exception:
        pass
    # 2. Local .env
    try:
        from dotenv import load_dotenv
        load_dotenv(PROJECT_ROOT / ".env")
    except ImportError:
        pass
    return os.environ.get("XAI_API_KEY") or None


# ── Sidebar ───────────────────────────────────────────────────────────────────

with st.sidebar:
    st.title("💹 AI Asset Allocator")
    st.caption("Powered by Grok · Built for Indian investors")
    st.divider()

    # API key input (only shown if not already resolved)
    api_key = resolve_api_key()
    if not api_key:
        api_key = st.text_input(
            "Grok API Key",
            type="password",
            placeholder="xai-...",
            help="Free at [console.x.ai](https://console.x.ai). Leave blank to see a demo.",
        ) or None

    st.divider()
    st.subheader("Your Profile")

    age      = st.selectbox(QUESTIONS["age"]["label"],      QUESTIONS["age"]["options"],      help=QUESTIONS["age"]["help"])
    horizon  = st.selectbox(QUESTIONS["horizon"]["label"],  QUESTIONS["horizon"]["options"],  help=QUESTIONS["horizon"]["help"])
    goal     = st.selectbox(QUESTIONS["goal"]["label"],     QUESTIONS["goal"]["options"],     help=QUESTIONS["goal"]["help"])
    reaction = st.selectbox(QUESTIONS["reaction"]["label"], QUESTIONS["reaction"]["options"], help=QUESTIONS["reaction"]["help"])
    debt     = st.selectbox(QUESTIONS["debt"]["label"],     QUESTIONS["debt"]["options"],     help=QUESTIONS["debt"]["help"])

    st.divider()
    monthly_income_raw = st.number_input(
        "Monthly investable income (₹)",
        min_value=0,
        max_value=10_000_000,
        value=20_000,
        step=1_000,
        help="Amount you can set aside for investments each month.",
    )
    monthly_income = int(monthly_income_raw) if monthly_income_raw > 0 else None

    st.divider()
    generate = st.button("Generate My Allocation →", use_container_width=True, type="primary")


# ── Main content ──────────────────────────────────────────────────────────────

st.title("AI-Powered Asset Allocation")
st.caption("Enter your profile on the left and click **Generate** to receive a personalised allocation.")

if not generate:
    # Landing state — show a brief explainer
    col1, col2, col3 = st.columns(3)
    with col1:
        st.info("**Step 1 — Profile**\nAnswer 5 questions in the sidebar to build your investor profile.")
    with col2:
        st.info("**Step 2 — AI Analysis**\nGrok analyses your profile using CAPM-based risk scoring and generates a personalised allocation.")
    with col3:
        st.info("**Step 3 — Allocation**\nReceive a breakdown across Equity, Debt, Gold, and Alternatives — with reasoning for each.")

    with st.expander("How is my risk score calculated?"):
        st.markdown("""
Your risk score (0–100) is computed from five factors:

| Factor | Max Points | Why it matters |
|---|---|---|
| Age | 25 | Younger investors can ride out volatility |
| Investment horizon | 30 | Time is the biggest risk-reducer in markets |
| Primary goal | 20 | Wealth creation tolerates more risk than income |
| Reaction to market drop | 15 | Emotional discipline matters as much as math |
| Debt obligations | 10 | High debt reduces risk-taking capacity |

Scores map to four profiles: **Conservative** (0–30) · **Moderate Conservative** (31–55) · **Moderate Aggressive** (56–70) · **Aggressive** (71–100)
        """)
    st.stop()


# ── Compute risk score ────────────────────────────────────────────────────────

risk_score = compute_risk_score(age, horizon, goal, reaction, debt)
risk_label = get_risk_label(risk_score)
gauge_color = score_to_gauge_color(risk_score)

# ── Call Grok (or demo) ───────────────────────────────────────────────────────

with st.spinner("Generating your personalised allocation…"):
    result = get_allocation(
        age=age,
        horizon=horizon,
        goal=goal,
        reaction=reaction,
        debt=debt,
        risk_score=risk_score,
        risk_label=risk_label,
        monthly_income=monthly_income,
        api_key=api_key,
    )

is_demo = result.get("_demo", False)
has_error = "_error" in result

# ── Demo / error banners ──────────────────────────────────────────────────────

if has_error:
    st.warning(
        f"Grok API returned an error — showing demo allocation instead.\n\n`{result['_error']}`",
        icon="⚠️",
    )
elif is_demo:
    st.info(
        "**Demo mode** — showing a sample allocation for your risk profile. "
        "Enter a Grok API key in the sidebar to generate your personalised allocation.",
        icon="ℹ️",
    )

# ── Section 1: Profile summary ────────────────────────────────────────────────

st.subheader("Your Investor Profile")

gauge_fig = go.Figure(go.Indicator(
    mode="gauge+number",
    value=risk_score,
    title={"text": "Risk Score", "font": {"color": CHART_FONT, "size": 14}},
    number={"font": {"color": gauge_color, "size": 36}},
    gauge={
        "axis": {"range": [0, 100], "tickcolor": CHART_FONT},
        "bar": {"color": gauge_color},
        "steps": [
            {"range": [0,  30], "color": "rgba(16,185,129,0.15)"},
            {"range": [31, 55], "color": "rgba(245,158,11,0.15)"},
            {"range": [56, 70], "color": "rgba(249,115,22,0.15)"},
            {"range": [71,100], "color": "rgba(239,68,68,0.15)"},
        ],
        "threshold": {"line": {"color": gauge_color, "width": 3}, "value": risk_score},
        "bgcolor": TRANSPARENT,
        "bordercolor": GRID_COLOR,
    },
))
gauge_fig.update_layout(**PLOTLY_BASE, height=260, margin=dict(t=40, b=0, l=20, r=20))

pcol1, pcol2 = st.columns([1, 2])

with pcol1:
    st.plotly_chart(gauge_fig, use_container_width=True)

with pcol2:
    st.markdown(f"### {risk_label}")
    st.markdown(f"Risk score: **{risk_score}/100**")
    if monthly_income:
        st.markdown(f"Monthly investable income: **₹{monthly_income:,}**")
    st.markdown("---")
    st.markdown(f"**Age:** {age} &nbsp;|&nbsp; **Horizon:** {horizon}")
    st.markdown(f"**Goal:** {goal} &nbsp;|&nbsp; **Debt:** {debt}")

# ── Section 2: Allocation ─────────────────────────────────────────────────────

st.divider()
st.subheader("Recommended Asset Allocation")

allocation = result.get("allocation", {})
reasoning  = result.get("reasoning", {})

# Donut chart
labels  = [k.capitalize() for k in allocation.keys()]
values  = list(allocation.values())
colors  = [ASSET_COLORS.get(k, "#94A3B8") for k in allocation.keys()]

donut_fig = go.Figure(go.Pie(
    labels=labels,
    values=values,
    hole=0.55,
    marker=dict(colors=colors, line=dict(color="#1E293B", width=2)),
    textinfo="label+percent",
    textfont=dict(color=CHART_FONT, size=13),
    hovertemplate="<b>%{label}</b><br>%{value}%<extra></extra>",
))
donut_fig.update_layout(
    **PLOTLY_BASE,
    height=340,
    showlegend=False,
    margin=dict(t=20, b=20, l=0, r=0),
    annotations=[dict(
        text=f"{allocation.get('equity', 0)}%<br>Equity",
        x=0.5, y=0.5,
        font=dict(size=18, color=ASSET_COLORS["equity"]),
        showarrow=False,
    )],
)

dcol1, dcol2 = st.columns([1, 1])

with dcol1:
    st.plotly_chart(donut_fig, use_container_width=True)

with dcol2:
    for asset, pct in allocation.items():
        color = ASSET_COLORS.get(asset, "#94A3B8")
        reason = reasoning.get(asset, "")
        with st.container():
            st.markdown(
                f"<span style='color:{color}; font-size:1.1em; font-weight:700'>"
                f"{'█' * max(1, pct // 5)} {asset.capitalize()} — {pct}%"
                f"</span>",
                unsafe_allow_html=True,
            )
            if reason:
                st.caption(reason)
            st.markdown("")

# SIP suggestion
sip = result.get("monthly_sip_suggestion")
if sip:
    st.success(f"💰 Suggested monthly SIP: **₹{sip:,}** ({sip/monthly_income*100:.0f}% of your investable income)" if monthly_income else f"💰 Suggested monthly SIP: **₹{sip:,}**")

# ── Section 3: Key considerations ────────────────────────────────────────────

considerations = result.get("key_considerations", [])
if considerations:
    st.divider()
    st.subheader("Key Considerations")
    for item in considerations:
        st.markdown(f"✔ {item}")

# ── Section 4: Fund category recommendations ─────────────────────────────────

equity_pct = allocation.get("equity", 0)
fund_recs   = build_fund_recommendations(equity_pct, risk_label, goal)

if fund_recs:
    st.divider()
    st.subheader("Recommended Fund Categories")
    st.caption("Based on your equity allocation. Top-ranked funds sourced from the Mutual Fund Analytics project.")

    for rec in fund_recs:
        with st.expander(f"**{rec['category']}** — {rec['suggested_weight']}"):
            st.markdown(rec["rationale"])

            top_funds = rec.get("top_funds", [])
            if top_funds:
                st.markdown("**Top-ranked funds (from Project 1 scoring):**")
                for fund in top_funds:
                    name  = fund.get("scheme_name", "—")
                    rank  = fund.get("category_rank", "—")
                    score = fund.get("composite_score", None)
                    score_str = f"{score:.2f}" if score is not None else "—"
                    st.markdown(f"- **#{rank}** {name} &nbsp; *(composite score: {score_str})*")
            else:
                st.caption("Run the Mutual Fund Analytics pipeline to see top fund picks here.")

# ── Footer ────────────────────────────────────────────────────────────────────

st.divider()
st.caption(
    "⚠️ **Disclaimer:** This tool is for educational and portfolio demonstration purposes only. "
    "It does not constitute financial advice. Please consult a SEBI-registered investment advisor "
    "before making investment decisions. Mutual fund investments are subject to market risk."
)
st.caption("Built by Veer Pratap Singh · [GitHub](https://github.com/VeerVVAPS-portfolio) · [LinkedIn](https://linkedin.com/in/veer-pratap-singh-681a5530b)")
