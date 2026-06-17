"""
app.py  —  AI-Powered Financial Profile & Asset Allocation Tool
Streamlit dashboard powered by the Groq API (Llama 3.3).
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
    BASE_ALLOCATIONS,
    QUESTIONS,
    compute_risk_score,
    get_risk_label,
    score_to_gauge_color,
)

# ── Page config ───────────────────────────────────────────────────────────────

st.set_page_config(
    page_title="AI Asset Allocator",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Global CSS ────────────────────────────────────────────────────────────────

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
@import url('https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.3/font/bootstrap-icons.min.css');

html, body, [class*="css"] { font-family: 'Inter', sans-serif; }

/* ── Keyframe Animations ── */
@keyframes fadeSlideUp {
    from { opacity: 0; transform: translateY(18px); }
    to   { opacity: 1; transform: translateY(0); }
}
@keyframes barGrow {
    from { transform: scaleX(0); }
    to   { transform: scaleX(1); }
}
@keyframes gradientShift {
    0%   { background-position: 0% 50%; }
    50%  { background-position: 100% 50%; }
    100% { background-position: 0% 50%; }
}
@keyframes pulseBorder {
    0%, 100% { box-shadow: 0 0 0 0 rgba(129,140,248,0.3); }
    50%       { box-shadow: 0 0 0 6px rgba(129,140,248,0); }
}
@keyframes shimmer {
    0%   { background-position: -200% center; }
    100% { background-position: 200% center; }
}
@keyframes countFade {
    from { opacity: 0; transform: scale(0.85); }
    to   { opacity: 1; transform: scale(1); }
}

/* ── Hero ── */
.hero-wrap {
    padding: 1.5rem 0 0.5rem 0;
    animation: fadeSlideUp 0.6s ease both;
}
.hero-title {
    font-size: 2.5rem;
    font-weight: 700;
    background: linear-gradient(270deg, #818CF8, #A78BFA, #38BDF8, #818CF8);
    background-size: 300% 300%;
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
    animation: gradientShift 5s ease infinite;
    line-height: 1.2;
    margin-bottom: 0.4rem;
}
.hero-sub {
    color: #64748B;
    font-size: 1rem;
    max-width: 600px;
}

/* ── Section headers ── */
.sec-header {
    display: flex;
    align-items: center;
    gap: 0.6rem;
    margin: 2rem 0 1rem;
    animation: fadeSlideUp 0.5s ease both;
}
.sec-header .bar { width: 3px; height: 1.1rem; border-radius: 2px;
    background: linear-gradient(180deg, #818CF8, #38BDF8); flex-shrink:0; }
.sec-header .label { font-size: 1rem; font-weight: 600; color: #E2E8F0; }
.sec-header .icon { color: #818CF8; font-size: 1.1rem; }

/* ── Feature cards (landing) ── */
.feature-card {
    background: rgba(129,140,248,0.05);
    border: 1px solid rgba(129,140,248,0.15);
    border-radius: 16px;
    padding: 1.6rem 1.4rem;
    text-align: center;
    animation: fadeSlideUp 0.5s ease both;
    transition: transform 0.2s ease, box-shadow 0.2s ease;
}
.feature-card:hover {
    transform: translateY(-4px);
    box-shadow: 0 12px 32px rgba(129,140,248,0.12);
}
.feature-card .icon-wrap {
    width: 3rem; height: 3rem; border-radius: 12px;
    background: linear-gradient(135deg, rgba(129,140,248,0.2), rgba(56,189,248,0.15));
    display: flex; align-items: center; justify-content: center;
    margin: 0 auto 1rem;
    font-size: 1.3rem; color: #818CF8;
}
.feature-card h4 { color: #E2E8F0; font-size: 0.95rem; font-weight: 600; margin: 0 0 0.4rem; }
.feature-card p  { color: #64748B; font-size: 0.82rem; margin: 0; line-height: 1.55; }

/* ── Risk badge ── */
.risk-badge {
    display: inline-flex; align-items: center; gap: 0.4rem;
    padding: 0.4rem 1rem; border-radius: 999px;
    font-size: 0.9rem; font-weight: 600;
    animation: pulseBorder 2.5s ease infinite;
}

/* ── Profile chips ── */
.chip-row { display: flex; flex-wrap: wrap; gap: 0.4rem; margin-top: 0.8rem; }
.chip {
    display: inline-flex; align-items: center; gap: 0.35rem;
    background: rgba(255,255,255,0.05); border: 1px solid rgba(255,255,255,0.09);
    border-radius: 999px; padding: 0.28rem 0.75rem;
    font-size: 0.8rem; color: #94A3B8;
}
.chip i { color: #818CF8; font-size: 0.75rem; }

/* ── Asset metric cards ── */
.metric-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 0.75rem; margin: 1rem 0; }
.metric-card {
    background: rgba(255,255,255,0.03);
    border: 1px solid rgba(255,255,255,0.07);
    border-radius: 14px; padding: 1.1rem 1rem;
    text-align: center;
    animation: fadeSlideUp 0.5s ease both;
    transition: transform 0.2s ease;
}
.metric-card:hover { transform: translateY(-3px); }
.metric-card .mc-icon { font-size: 1.4rem; margin-bottom: 0.4rem; }
.metric-card .mc-pct {
    font-size: 2rem; font-weight: 700; line-height: 1;
    animation: countFade 0.6s ease both;
}
.metric-card .mc-label { font-size: 0.75rem; color: #64748B; margin-top: 0.25rem; font-weight: 500; text-transform: uppercase; letter-spacing: 0.04em; }

/* ── Allocation bars ── */
.alloc-section { animation: fadeSlideUp 0.6s ease both; }
.alloc-row { margin-bottom: 1.1rem; }
.alloc-label-row { display: flex; justify-content: space-between; margin-bottom: 0.35rem; }
.alloc-name { font-size: 0.88rem; font-weight: 600; display: flex; align-items: center; gap: 0.4rem; }
.alloc-pct  { font-size: 0.88rem; font-weight: 700; }
.bar-bg { background: rgba(255,255,255,0.06); border-radius: 999px; height: 7px; overflow: hidden; }
.bar-fill {
    height: 7px; border-radius: 999px;
    transform-origin: left center;
    animation: barGrow 0.9s cubic-bezier(0.34,1.56,0.64,1) both;
}
.alloc-reason { margin-top: 0.4rem; font-size: 0.79rem; color: #475569; line-height: 1.55; }

/* ── SIP card ── */
.sip-card {
    background: linear-gradient(270deg, rgba(16,185,129,0.08), rgba(56,189,248,0.06), rgba(16,185,129,0.08));
    background-size: 300% 300%;
    animation: gradientShift 6s ease infinite, fadeSlideUp 0.6s ease both;
    border: 1px solid rgba(16,185,129,0.2);
    border-radius: 14px; padding: 1.2rem 1.5rem;
    display: flex; align-items: center; gap: 1.2rem; margin: 1rem 0;
}
.sip-icon-wrap {
    width: 3rem; height: 3rem; border-radius: 12px;
    background: rgba(16,185,129,0.15);
    display: flex; align-items: center; justify-content: center;
    font-size: 1.3rem; color: #10B981; flex-shrink: 0;
}
.sip-label { color: #64748B; font-size: 0.78rem; font-weight: 500; text-transform: uppercase; letter-spacing: 0.05em; }
.sip-amount { color: #10B981; font-size: 1.6rem; font-weight: 700; line-height: 1.15; }
.sip-sub { color: #475569; font-size: 0.78rem; margin-top: 0.15rem; }

/* ── Considerations ── */
.consid-wrap {
    background: rgba(255,255,255,0.02);
    border: 1px solid rgba(255,255,255,0.06);
    border-radius: 14px; overflow: hidden;
    animation: fadeSlideUp 0.5s ease both;
}
.consid-item {
    display: flex; align-items: flex-start; gap: 0.75rem;
    padding: 0.9rem 1.2rem;
    border-bottom: 1px solid rgba(255,255,255,0.04);
    font-size: 0.85rem; color: #CBD5E1; line-height: 1.55;
    transition: background 0.15s ease;
}
.consid-item:last-child { border-bottom: none; }
.consid-item:hover { background: rgba(255,255,255,0.02); }
.consid-item i { color: #10B981; font-size: 1rem; flex-shrink: 0; margin-top: 0.1rem; }

/* ── Fund cards ── */
.fund-card {
    background: rgba(255,255,255,0.02);
    border: 1px solid rgba(255,255,255,0.06);
    border-left: 3px solid #818CF8;
    border-radius: 0 14px 14px 0;
    padding: 1rem 1.2rem; margin-bottom: 0.65rem;
    animation: fadeSlideUp 0.5s ease both;
    transition: border-left-color 0.2s ease, background 0.2s ease;
}
.fund-card:hover { background: rgba(129,140,248,0.04); border-left-color: #A78BFA; }
.fund-card-title { font-size: 0.95rem; font-weight: 600; color: #E2E8F0; display: flex; align-items: center; gap: 0.5rem; }
.fund-badge {
    display: inline-block; background: rgba(129,140,248,0.12); color: #818CF8;
    font-size: 0.7rem; font-weight: 600; padding: 0.12rem 0.5rem;
    border-radius: 999px; text-transform: uppercase; letter-spacing: 0.04em;
}
.fund-rationale { font-size: 0.8rem; color: #475569; margin-top: 0.35rem; line-height: 1.55; }
.fund-pick-row { display: flex; align-items: center; gap: 0.5rem; padding: 0.3rem 0; font-size: 0.8rem; color: #64748B; }
.fund-rank-badge {
    background: rgba(16,185,129,0.12); color: #10B981;
    font-size: 0.7rem; font-weight: 700; padding: 0.1rem 0.4rem; border-radius: 4px; flex-shrink: 0;
}
.fund-picks-wrap { margin-top: 0.6rem; border-top: 1px solid rgba(255,255,255,0.04); padding-top: 0.5rem; }
.fund-picks-label { font-size: 0.72rem; font-weight: 600; color: #475569; text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: 0.3rem; }

/* ── Demo banner ── */
.demo-banner {
    background: rgba(56,189,248,0.06); border: 1px solid rgba(56,189,248,0.15);
    border-radius: 10px; padding: 0.7rem 1rem;
    font-size: 0.83rem; color: #7DD3FC; margin-bottom: 1rem;
    display: flex; align-items: center; gap: 0.6rem;
}

/* ── Disclaimer ── */
.disclaimer {
    background: rgba(255,255,255,0.015); border: 1px solid rgba(255,255,255,0.05);
    border-radius: 10px; padding: 0.9rem 1.2rem;
    font-size: 0.76rem; color: #334155; line-height: 1.65; margin-top: 2rem;
}
.footer-links { text-align: center; margin-top: 1rem; font-size: 0.77rem; color: #334155; }
.footer-links a { color: #818CF8; text-decoration: none; }
.footer-links a:hover { color: #A78BFA; }

[data-testid="stSidebar"] { background: rgba(15,23,42,0.97); }
</style>
""", unsafe_allow_html=True)

# ── Constants ─────────────────────────────────────────────────────────────────

ASSET_COLORS = {
    "equity":       "#818CF8",
    "debt":         "#10B981",
    "gold":         "#F59E0B",
    "alternatives": "#38BDF8",
}
ASSET_ICONS = {
    "equity":       "bi-graph-up-arrow",
    "debt":         "bi-shield-check",
    "gold":         "bi-gem",
    "alternatives": "bi-layers",
}
ASSET_GRADIENTS = {
    "equity":       "linear-gradient(90deg,#818CF8,#A78BFA)",
    "debt":         "linear-gradient(90deg,#10B981,#34D399)",
    "gold":         "linear-gradient(90deg,#F59E0B,#FCD34D)",
    "alternatives": "linear-gradient(90deg,#38BDF8,#67E8F9)",
}
RISK_BADGE_COLORS = {
    "Conservative":          ("#10B981", "rgba(16,185,129,0.1)",  "rgba(16,185,129,0.25)"),
    "Moderate Conservative": ("#F59E0B", "rgba(245,158,11,0.1)",  "rgba(245,158,11,0.25)"),
    "Moderate Aggressive":   ("#F97316", "rgba(249,115,22,0.1)",  "rgba(249,115,22,0.25)"),
    "Aggressive":            ("#EF4444", "rgba(239,68,68,0.1)",   "rgba(239,68,68,0.25)"),
}

TRANSPARENT = "rgba(0,0,0,0)"
CHART_FONT  = "#94A3B8"
HOVER_FONT  = "#1F2937"
PLOTLY_BASE = dict(
    paper_bgcolor=TRANSPARENT, plot_bgcolor=TRANSPARENT,
    font=dict(color=CHART_FONT, family="Inter, sans-serif", size=12),
    hoverlabel=dict(bgcolor="#1E293B", font_size=12, font_color="#E2E8F0", bordercolor="#334155"),
)

# ── Helpers ───────────────────────────────────────────────────────────────────

def sec_header(icon_cls: str, title: str, delay: str = "0s"):
    st.markdown(
        f'<div class="sec-header" style="animation-delay:{delay}">'
        f'  <div class="bar"></div>'
        f'  <i class="bi {icon_cls} icon"></i>'
        f'  <span class="label">{title}</span>'
        f'</div>',
        unsafe_allow_html=True,
    )

def risk_badge_html(label: str) -> str:
    color, bg, border = RISK_BADGE_COLORS.get(label, ("#818CF8", "rgba(129,140,248,0.1)", "rgba(129,140,248,0.25)"))
    return (
        f'<span class="risk-badge" style="color:{color};background:{bg};border:1px solid {border}">'
        f'<i class="bi bi-activity"></i>{label}</span>'
    )

def resolve_api_key() -> str | None:
    try:
        key = st.secrets.get("GROQ_API_KEY")
        if key:
            return key
    except Exception:
        pass
    try:
        from dotenv import load_dotenv
        load_dotenv(PROJECT_ROOT / ".env")
    except ImportError:
        pass
    return os.environ.get("GROQ_API_KEY") or None

# ── Sidebar ───────────────────────────────────────────────────────────────────

with st.sidebar:
    st.markdown(
        '<div style="font-size:1.1rem;font-weight:700;color:#E2E8F0;margin-bottom:0.15rem">'
        '<i class="bi bi-bar-chart-fill" style="color:#818CF8"></i> AI Asset Allocator</div>'
        '<div style="font-size:0.78rem;color:#475569">Powered by Groq · Llama 3.3 · Indian Markets</div>',
        unsafe_allow_html=True,
    )
    st.divider()

    api_key = resolve_api_key()
    if not api_key:
        api_key = st.text_input(
            "Groq API Key",
            type="password",
            placeholder="gsk-...",
            help="Free at [console.groq.com](https://console.groq.com). Leave blank for demo.",
        ) or None

    st.divider()
    st.markdown('<div style="font-size:0.82rem;font-weight:600;color:#94A3B8;text-transform:uppercase;letter-spacing:0.06em;margin-bottom:0.5rem">Investor Profile</div>', unsafe_allow_html=True)

    age      = st.selectbox(QUESTIONS["age"]["label"],      QUESTIONS["age"]["options"],      help=QUESTIONS["age"]["help"])
    horizon  = st.selectbox(QUESTIONS["horizon"]["label"],  QUESTIONS["horizon"]["options"],  help=QUESTIONS["horizon"]["help"])
    goal     = st.selectbox(QUESTIONS["goal"]["label"],     QUESTIONS["goal"]["options"],     help=QUESTIONS["goal"]["help"])
    reaction = st.selectbox(QUESTIONS["reaction"]["label"], QUESTIONS["reaction"]["options"], help=QUESTIONS["reaction"]["help"])
    debt     = st.selectbox(QUESTIONS["debt"]["label"],     QUESTIONS["debt"]["options"],     help=QUESTIONS["debt"]["help"])

    st.divider()
    monthly_income_raw = st.number_input(
        "Monthly investable income (₹)",
        min_value=0, max_value=10_000_000, value=20_000, step=1_000,
        help="Amount you can set aside for investments each month.",
    )
    monthly_income = int(monthly_income_raw) if monthly_income_raw > 0 else None

    st.divider()
    generate = st.button("Generate My Allocation →", use_container_width=True, type="primary")

# ── Hero ──────────────────────────────────────────────────────────────────────

st.markdown(
    '<div class="hero-wrap">'
    '<div class="hero-title">AI-Powered Asset Allocation</div>'
    '<div class="hero-sub">Answer 5 questions. Receive a personalised portfolio built by AI — '
    'with clear reasoning for every decision.</div>'
    '</div>',
    unsafe_allow_html=True,
)

# ── Landing ───────────────────────────────────────────────────────────────────

if not generate:
    c1, c2, c3 = st.columns(3)
    landing_cards = [
        ("bi-clipboard-data",   "Build Your Profile",   "Answer 5 quick questions about your age, goals, horizon, and risk comfort."),
        ("bi-cpu",              "AI Risk Analysis",     "Your answers are scored using a CAPM-based model and processed by Llama 3.3."),
        ("bi-pie-chart-fill",   "Your Allocation",      "Get a personalised split across Equity, Debt, Gold, and Alternatives with full reasoning."),
    ]
    for col, (icon, title, desc) in zip([c1, c2, c3], landing_cards):
        with col:
            st.markdown(
                f'<div class="feature-card">'
                f'  <div class="icon-wrap"><i class="bi {icon}"></i></div>'
                f'  <h4>{title}</h4>'
                f'  <p>{desc}</p>'
                f'</div>',
                unsafe_allow_html=True,
            )

    st.markdown("<br>", unsafe_allow_html=True)
    with st.expander("How is my risk score calculated?"):
        st.markdown("""
Your risk score (0–100) is computed from five weighted factors:

| Factor | Max Points | Why it matters |
|---|---|---|
| Age | 25 | Younger investors can ride out market cycles |
| Investment horizon | 30 | Time is the single biggest risk-reducer |
| Primary goal | 20 | Wealth creation tolerates more volatility than income |
| Reaction to a 20% drop | 15 | Emotional discipline matters as much as math |
| Debt obligations | 10 | High debt reduces capacity for risk |

**Risk profiles:** Conservative (0–30) · Moderate Conservative (31–55) · Moderate Aggressive (56–70) · Aggressive (71–100)
        """)
    st.stop()

# ── Compute ───────────────────────────────────────────────────────────────────

risk_score  = compute_risk_score(age, horizon, goal, reaction, debt)
risk_label  = get_risk_label(risk_score)
gauge_color = score_to_gauge_color(risk_score)

with st.spinner("Analysing your profile…"):
    result = get_allocation(
        age=age, horizon=horizon, goal=goal, reaction=reaction, debt=debt,
        risk_score=risk_score, risk_label=risk_label,
        monthly_income=monthly_income, api_key=api_key,
    )

is_demo   = result.get("_demo", False)
has_error = "_error" in result

if has_error:
    st.warning(f"API error — showing demo allocation.\n\n`{result['_error']}`", icon="⚠️")
elif is_demo:
    st.markdown(
        '<div class="demo-banner">'
        '<i class="bi bi-info-circle"></i>'
        '<span><strong>Demo mode</strong> — enter your Groq API key in the sidebar for a live personalised allocation.</span>'
        '</div>',
        unsafe_allow_html=True,
    )

allocation = result.get("allocation", {})
reasoning  = result.get("reasoning", {})

# ── Section 1: Investor Profile ───────────────────────────────────────────────

sec_header("bi-person-badge", "Investor Profile")

gauge_fig = go.Figure(go.Indicator(
    mode="gauge+number",
    value=risk_score,
    number={"font": {"color": gauge_color, "size": 44}, "suffix": ""},
    title={"text": "RISK SCORE / 100", "font": {"color": "#475569", "size": 11}},
    gauge={
        "axis": {"range": [0, 100], "tickcolor": "#334155", "tickwidth": 1,
                 "tickvals": [0, 30, 55, 70, 100], "ticktext": ["0", "30", "55", "70", "100"]},
        "bar": {"color": gauge_color, "thickness": 0.22},
        "steps": [
            {"range": [0,  30], "color": "rgba(16,185,129,0.08)"},
            {"range": [31, 55], "color": "rgba(245,158,11,0.08)"},
            {"range": [56, 70], "color": "rgba(249,115,22,0.08)"},
            {"range": [71,100], "color": "rgba(239,68,68,0.08)"},
        ],
        "threshold": {"line": {"color": gauge_color, "width": 2}, "value": risk_score},
        "bgcolor": TRANSPARENT, "borderwidth": 0,
    },
))
gauge_fig.update_layout(**PLOTLY_BASE, height=220, margin=dict(t=30, b=0, l=10, r=10))

pcol1, pcol2 = st.columns([1, 2])
with pcol1:
    st.plotly_chart(gauge_fig, use_container_width=True)
with pcol2:
    st.markdown(risk_badge_html(risk_label), unsafe_allow_html=True)
    profile_chips = [
        ("bi-calendar3",           age),
        ("bi-clock",               horizon),
        ("bi-bullseye",            goal),
        ("bi-credit-card",         debt),
    ]
    if monthly_income:
        profile_chips.append(("bi-currency-rupee", f"₹{monthly_income:,} / mo"))
    chips_html = "".join(
        f'<span class="chip"><i class="bi {ic}"></i>{txt}</span>'
        for ic, txt in profile_chips
    )
    st.markdown(f'<div class="chip-row">{chips_html}</div>', unsafe_allow_html=True)

# ── Section 2: Asset Allocation ───────────────────────────────────────────────

sec_header("bi-pie-chart-fill", "Recommended Asset Allocation")

# 4 metric cards
metric_html = '<div class="metric-grid">'
for i, (asset, pct) in enumerate(allocation.items()):
    color = ASSET_COLORS.get(asset, "#94A3B8")
    icon  = ASSET_ICONS.get(asset, "bi-circle")
    delay = f"{0.1 * i:.1f}s"
    metric_html += (
        f'<div class="metric-card" style="animation-delay:{delay};border-top:2px solid {color}22">'
        f'  <div class="mc-icon"><i class="bi {icon}" style="color:{color}"></i></div>'
        f'  <div class="mc-pct" style="color:{color};animation-delay:{delay}">{pct}%</div>'
        f'  <div class="mc-label">{asset.capitalize()}</div>'
        f'</div>'
    )
metric_html += '</div>'
st.markdown(metric_html, unsafe_allow_html=True)

# Donut + bars layout
dcol1, dcol2 = st.columns([1, 1])

with dcol1:
    donut_fig = go.Figure(go.Pie(
        labels=[k.capitalize() for k in allocation],
        values=list(allocation.values()),
        hole=0.62,
        marker=dict(
            colors=[ASSET_COLORS.get(k, "#94A3B8") for k in allocation],
            line=dict(color="#0F172A", width=3),
        ),
        textinfo="label+percent",
        textfont=dict(size=11),
        hovertemplate="<b>%{label}</b><br>%{value}%<extra></extra>",
        pull=[0.04] * len(allocation),
        direction="clockwise",
        sort=False,
    ))
    donut_fig.update_layout(
        **PLOTLY_BASE,
        height=300,
        showlegend=False,
        margin=dict(t=10, b=10, l=0, r=0),
        annotations=[dict(
            text=f'<b style="font-size:20px">{allocation.get("equity", 0)}%</b><br>'
                 f'<span style="font-size:11px;color:#64748B">Equity</span>',
            x=0.5, y=0.5, showarrow=False,
            font=dict(color=ASSET_COLORS["equity"], size=20),
        )],
    )
    st.plotly_chart(donut_fig, use_container_width=True)

with dcol2:
    bars_html = '<div class="alloc-section">'
    for i, (asset, pct) in enumerate(allocation.items()):
        color   = ASSET_COLORS.get(asset, "#94A3B8")
        icon    = ASSET_ICONS.get(asset, "bi-circle")
        grad    = ASSET_GRADIENTS.get(asset, f"linear-gradient(90deg,{color},{color})")
        reason  = reasoning.get(asset, "")
        delay   = f"{0.15 + 0.12 * i:.2f}s"
        bars_html += (
            f'<div class="alloc-row">'
            f'  <div class="alloc-label-row">'
            f'    <span class="alloc-name" style="color:{color}">'
            f'      <i class="bi {icon}"></i>{asset.capitalize()}'
            f'    </span>'
            f'    <span class="alloc-pct" style="color:{color}">{pct}%</span>'
            f'  </div>'
            f'  <div class="bar-bg">'
            f'    <div class="bar-fill" style="width:{pct}%;background:{grad};animation-delay:{delay}"></div>'
            f'  </div>'
            f'  <div class="alloc-reason">{reason}</div>'
            f'</div>'
        )
    bars_html += '</div>'
    st.markdown(bars_html, unsafe_allow_html=True)

# ── Comparison chart ─────────────────────────────────────────────────────────

sec_header("bi-bar-chart-steps", "How Your Profile Compares")

assets  = list(allocation.keys())
labels  = ["Conservative", "Mod. Conservative", "Mod. Aggressive", "Aggressive", "Your Profile"]
profile_keys = ["Conservative", "Moderate Conservative", "Moderate Aggressive", "Aggressive"]

your_alloc = [allocation.get(a, 0) for a in assets]
profile_allocs = {k: [BASE_ALLOCATIONS[k].get(a, 0) for a in assets] for k in profile_keys}

comp_fig = go.Figure()
for asset in assets:
    color  = ASSET_COLORS.get(asset, "#94A3B8")
    values = [BASE_ALLOCATIONS[pk].get(asset, 0) for pk in profile_keys] + [allocation.get(asset, 0)]
    comp_fig.add_trace(go.Bar(
        name=asset.capitalize(),
        y=labels,
        x=values,
        orientation="h",
        marker=dict(
            color=[color] * 4 + [color],
            opacity=[0.45] * 4 + [1.0],
            line=dict(width=0),
        ),
        hovertemplate=f"<b>{asset.capitalize()}</b>: %{{x}}%<extra></extra>",
        text=[f"{v}%" for v in values],
        textposition="inside",
        textfont=dict(size=10, color="white"),
        insidetextanchor="middle",
    ))

comp_fig.update_layout(
    **PLOTLY_BASE,
    barmode="stack",
    height=280,
    margin=dict(t=10, b=10, l=10, r=10),
    showlegend=True,
    legend=dict(
        orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1,
        font=dict(size=11), bgcolor=TRANSPARENT, itemsizing="constant",
    ),
    yaxis=dict(
        tickfont=dict(size=11),
        categoryorder="array",
        categoryarray=list(reversed(labels)),
    ),
    xaxis=dict(range=[0, 105], ticksuffix="%", gridcolor="#1E293B", tickfont=dict(size=10)),
    shapes=[dict(
        type="line", x0=0, x1=1, y0=0.5, y1=0.5,
        xref="paper", yref="paper",
        line=dict(color="#818CF8", width=1.5, dash="dot"),
    )],
)
st.plotly_chart(comp_fig, use_container_width=True)
st.caption("Dimmed bars = standard benchmark profiles · Solid bar = your personalised allocation · Dotted line separates benchmarks from your profile")

# ── SIP Card ─────────────────────────────────────────────────────────────────

sip = result.get("monthly_sip_suggestion")
if sip:
    pct_str = f" ({sip / monthly_income * 100:.0f}% of your income)" if monthly_income else ""
    st.markdown(
        f'<div class="sip-card">'
        f'  <div class="sip-icon-wrap"><i class="bi bi-currency-rupee"></i></div>'
        f'  <div>'
        f'    <div class="sip-label">Suggested Monthly SIP</div>'
        f'    <div class="sip-amount">₹{sip:,}</div>'
        f'    <div class="sip-sub">Invest consistently · Increase 10% annually{pct_str}</div>'
        f'  </div>'
        f'</div>',
        unsafe_allow_html=True,
    )

# ── Key Considerations ────────────────────────────────────────────────────────

considerations = result.get("key_considerations", [])
if considerations:
    sec_header("bi-lightbulb", "Key Considerations")
    items_html = "".join(
        f'<div class="consid-item"><i class="bi bi-check-circle-fill"></i><span>{item}</span></div>'
        for item in considerations
    )
    st.markdown(f'<div class="consid-wrap">{items_html}</div>', unsafe_allow_html=True)

# ── Fund Category Recommendations ─────────────────────────────────────────────

equity_pct = allocation.get("equity", 0)
fund_recs  = build_fund_recommendations(equity_pct, risk_label, goal)

if fund_recs:
    sec_header("bi-building", "Recommended Fund Categories")
    st.caption("Based on your equity allocation · Top-ranked funds from the Mutual Fund Analytics project")

    for rec in fund_recs:
        top_funds = rec.get("top_funds", [])
        picks_html = ""
        if top_funds:
            picks_html = '<div class="fund-picks-wrap"><div class="fund-picks-label">Top-ranked funds</div>'
            for fund in top_funds:
                name      = fund.get("scheme_name", "—")
                rank      = fund.get("category_rank", "—")
                score     = fund.get("composite_score", None)
                score_str = f"{score:.2f}" if score is not None else "—"
                picks_html += (
                    f'<div class="fund-pick-row">'
                    f'  <span class="fund-rank-badge">#{rank}</span>'
                    f'  <span style="flex:1">{name}</span>'
                    f'  <span style="color:#334155;font-size:0.72rem">score {score_str}</span>'
                    f'</div>'
                )
            picks_html += '</div>'
        else:
            picks_html = '<div style="margin-top:0.5rem;font-size:0.76rem;color:#334155">Run the Mutual Fund Analytics pipeline to populate fund picks.</div>'

        st.markdown(
            f'<div class="fund-card">'
            f'  <div class="fund-card-title">'
            f'    <i class="bi bi-collection" style="color:#818CF8;font-size:0.9rem"></i>'
            f'    {rec["category"]}'
            f'    <span class="fund-badge">{rec["suggested_weight"]}</span>'
            f'  </div>'
            f'  <div class="fund-rationale">{rec["rationale"]}</div>'
            f'  {picks_html}'
            f'</div>',
            unsafe_allow_html=True,
        )

# ── Footer ────────────────────────────────────────────────────────────────────

st.markdown(
    '<div class="disclaimer">'
    '<strong>Disclaimer:</strong> This tool is for educational and portfolio demonstration purposes only. '
    'It does not constitute financial advice. Please consult a SEBI-registered investment advisor before '
    'making investment decisions. Mutual fund investments are subject to market risk. '
    'Read all scheme-related documents carefully before investing.'
    '</div>'
    '<div class="footer-links">'
    'Built by <strong>Veer Pratap Singh</strong> &nbsp;·&nbsp; '
    '<a href="https://github.com/VeerVVAPS-portfolio">GitHub</a> &nbsp;·&nbsp; '
    '<a href="https://linkedin.com/in/veer-pratap-singh-681a5530b">LinkedIn</a>'
    '</div>',
    unsafe_allow_html=True,
)
