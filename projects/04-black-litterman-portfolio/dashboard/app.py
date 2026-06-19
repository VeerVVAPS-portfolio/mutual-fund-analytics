"""
Streamlit dashboard — Black-Litterman Portfolio (Project 4).

Run: streamlit run dashboard/app.py  (from the project root)
"""

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from black_litterman import ASSET_ORDER, DEFAULT_VIEWS, compute_posterior  # noqa: E402
from optimizer import optimize_portfolio  # noqa: E402
from reverse_optimization import (  # noqa: E402
    RISK_FREE_RATE,
    compute_implied_excess_returns,
    compute_lambda,
    compute_market_weights,
)
from stress_test import SHOCKS, stressed_return, var_95_corrected, var_95_replica  # noqa: E402

st.set_page_config(page_title="Black-Litterman Portfolio | Project 4", layout="wide")

ASSET_LABELS = {
    "GSEC": "G-Sec (10Y)", "NIFTY50": "NIFTY 50", "AUTO": "Auto", "BANK": "Bank",
    "FINSERV": "Fin. Services", "FMCG": "FMCG", "IT": "IT", "OILGAS": "Oil & Gas",
    "PHARMA": "Pharma", "REITS": "REITs", "GOLD": "Gold",
}

# ── CSS — same dark theme as Projects 1 & 2 ────────────────────────────────────

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@400;500;600;700&family=Inter:wght@400;500;600&display=swap');
@import url('https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.3/font/bootstrap-icons.min.css');

html, body, [class*="css"] {
    font-family: 'Inter', sans-serif;
    background-color: #0A0A0E !important;
    color: #E4E4E7 !important;
}
:root {
    --bg: #0A0A0E; --surf: #111116; --surf2: #18181F;
    --bdr: rgba(255,255,255,0.06); --bdr2: rgba(255,255,255,0.12); --rule: rgba(255,255,255,0.05);
    --t1: #F4F4F5; --t2: #A1A1AA; --t3: #71717A; --t4: #52525B;
    --acc: #818CF8; --gold: #E4C76B; --green: #10B981; --amber: #F59E0B; --sky: #38BDF8; --red: #F87171;
}
@keyframes fadeUp { from{opacity:0;transform:translateY(16px)} to{opacity:1;transform:translateY(0)} }

/* Modern Streamlit (1.4x+) renamed its CSS-module classnames from
   "css-xxxxx" to "st-emotion-cache-xxxxx", which silently broke the old
   [class*="css"] trick for the main content panel and header — only the
   explicitly-targeted [data-testid="stSidebar"] still picked up the dark
   theme, leaving the main panel on Streamlit's default white background.
   Target the stable data-testid hooks directly instead. */
[data-testid="stAppViewContainer"], [data-testid="stMain"], [data-testid="stHeader"] {
    background-color: var(--bg) !important;
}
[data-testid="stHeader"] { background-color: transparent !important; }

.block-container { padding-top: 2.5rem !important; max-width: 1150px !important; }
[data-testid="stSidebar"] { background: var(--surf) !important; border-right: 1px solid var(--bdr) !important; }

/* Streamlit's native widget labels (slider/radio captions) render with the
   framework's own light-theme text color and aren't reliably caught by the
   global override above — force them to the readable muted tone. */
[data-testid="stWidgetLabel"] p, .stRadio label p, .stSlider label p {
    color: var(--t2) !important;
}
/* st.caption() renders its container at 60% opacity by default, which
   combined with an already-muted text color drops effective contrast well
   below WCAG AA — these captions carry real explanatory content, not
   decorative chrome, so force full opacity and a legible color. */
[data-testid="stCaptionContainer"] {
    opacity: 1 !important;
}
[data-testid="stCaptionContainer"] p {
    color: var(--t2) !important;
}

.sb-brand { font-family: 'Space Grotesk', sans-serif; font-size: 1rem; font-weight: 700; color: var(--t1); letter-spacing: -0.01em; margin-bottom: 0.15rem; }
.sb-sub { font-size: 0.7rem; color: var(--t4); letter-spacing: 0.04em; text-transform: uppercase; }
.sb-section { font-size: 0.65rem; font-weight: 600; letter-spacing: 0.12em; text-transform: uppercase; color: var(--t4); margin-bottom: 0.5rem; }

.ph-wrap { padding: 1rem 0 2.5rem; animation: fadeUp 0.6s ease both; }
.ph-eyebrow { font-size: 0.68rem; font-weight: 600; letter-spacing: 0.14em; text-transform: uppercase; color: var(--acc); margin-bottom: 1rem; }
.ph-title { font-family: 'Space Grotesk', sans-serif; font-size: 3.2rem; font-weight: 700; line-height: 1.0; letter-spacing: -0.03em; color: var(--t1); margin-bottom: 1.2rem; }
.ph-title span { color: var(--acc); }
.ph-stats { display: flex; align-items: center; gap: 2rem; flex-wrap: wrap; padding: 1.2rem 0; border-top: 1px solid var(--rule); border-bottom: 1px solid var(--rule); }
.ph-stat-num { font-family: 'Space Grotesk', sans-serif; font-size: 1.5rem; font-weight: 700; color: var(--t1); line-height: 1; }
.ph-stat-label { font-size: 0.68rem; color: var(--t3); margin-top: 0.2rem; letter-spacing: 0.04em; }
.ph-divider { width: 1px; height: 2rem; background: var(--rule); }

.sec-head { display: flex; align-items: center; gap: 0.6rem; padding: 2rem 0 1rem; border-top: 1px solid var(--rule); animation: fadeUp 0.5s ease both; }
.sec-head-label { font-size: 0.65rem; font-weight: 600; letter-spacing: 0.14em; text-transform: uppercase; color: var(--t4); }
.sec-head-line { flex: 1; height: 1px; background: var(--rule); }

.metric-row { display: flex; gap: 1.2rem; flex-wrap: wrap; margin: 0.5rem 0 1rem; }
.metric-card { flex: 1; min-width: 160px; background: var(--surf2); border: 1px solid var(--bdr); border-radius: 12px; padding: 1.2rem 1.4rem; }
.metric-label { font-size: 0.68rem; color: var(--t3); letter-spacing: 0.06em; text-transform: uppercase; margin-bottom: 0.5rem; }
.metric-val { font-family: 'Space Grotesk', sans-serif; font-size: 1.9rem; font-weight: 700; letter-spacing: -0.02em; }
.metric-sub { font-size: 0.72rem; color: var(--t4); margin-top: 0.3rem; }
</style>
""", unsafe_allow_html=True)

CHART_FONT = "#71717A"
HOVER_FONT = "#F4F4F5"
HOVER_BG = "#18181F"
GRID_COLOR = "#27272A"
TRANSPARENT = "rgba(0,0,0,0)"
PLOTLY_BASE = dict(
    paper_bgcolor=TRANSPARENT,
    plot_bgcolor=TRANSPARENT,
    font=dict(color=CHART_FONT, family="Space Grotesk, Inter, sans-serif", size=12),
    hoverlabel=dict(bgcolor=HOVER_BG, font_size=13, font_color=HOVER_FONT, bordercolor=GRID_COLOR),
)

# ── Data: static historical-data layer, loaded once ────────────────────────────

@st.cache_data
def load_static_data():
    stats = pd.read_csv(PROJECT_ROOT / "data/processed/stats.csv", index_col=0)
    cov_monthly = pd.read_csv(PROJECT_ROOT / "data/processed/covariance_monthly.csv", index_col=0)
    cov_annual = pd.read_csv(PROJECT_ROOT / "data/processed/covariance_annual.csv", index_col=0)
    market_weights = compute_market_weights()
    lam = compute_lambda(stats)
    return stats, cov_monthly, cov_annual, market_weights, lam

stats, cov_monthly, cov_annual, market_weights, lam = load_static_data()

# ── Sidebar — views editor ──────────────────────────────────────────────────────

with st.sidebar:
    st.markdown(
        '<div class="sb-brand">Black-Litterman Portfolio</div>'
        '<div class="sb-sub">₹100 Cr Multi-Asset Mandate</div>',
        unsafe_allow_html=True,
    )
    st.divider()

    st.markdown('<div class="sb-section">Mode</div>', unsafe_allow_html=True)
    mode_label = st.radio(
        "Mode",
        ["Replica (matches the original Excel)", "Corrected (consistent annual units)"],
        label_visibility="collapsed",
    )
    mode = "replica" if mode_label.startswith("Replica") else "corrected"
    if mode == "replica":
        st.caption(
            "Uses the MONTHLY covariance matrix throughout (reverse optimization, "
            "Black-Litterman blending, optimizer) — reproduces the original Excel and "
            "slide deck exactly, including its Sharpe Ratio / VaR unit mismatch."
        )
    else:
        st.caption(
            "Uses the ANNUALIZED covariance matrix consistently throughout, so return, "
            "volatility, Sharpe Ratio, and VaR are all on the same time basis. The "
            "Omega matrix is also diagonalized and confidence-weighted (the original "
            "model's confidence inputs were never actually used)."
        )

    st.divider()

    st.markdown('<div class="sb-section">Investor Views</div>', unsafe_allow_html=True)

    view1_q = st.slider("Bank vs IT spread (%)", 0.0, 10.0, 2.5, 0.5) / 100
    view1_c = st.slider("Confidence (Bank>IT)", 5, 95, 75, 5,
                         help="Only affects results in Corrected mode — the original model never used confidence.") / 100

    view2_q = st.slider("Auto vs FMCG spread (%)", 0.0, 10.0, 3.0, 0.5) / 100
    view2_c = st.slider("Confidence (Auto>FMCG)", 5, 95, 60, 5) / 100

    view3_q = st.slider("G-Sec absolute target (%)", 0.0, 15.0, 7.0, 0.5) / 100
    view3_c = st.slider("Confidence (G-Sec)", 5, 95, 90, 5) / 100

    views = [
        {"name": "Bank > IT", "type": "relative", "asset1": "BANK", "asset2": "IT", "q": view1_q, "confidence": view1_c},
        {"name": "Auto > FMCG", "type": "relative", "asset1": "AUTO", "asset2": "FMCG", "q": view2_q, "confidence": view2_c},
        {"name": "G-Sec = target", "type": "absolute", "asset1": "GSEC", "asset2": None, "q": view3_q, "confidence": view3_c},
    ]

    st.divider()
    with st.expander("Assumptions & limitations"):
        st.markdown(
            """
**Equal-split equity weights** — the 70.1% equity market-cap bucket is split
equally across 8 sub-indices, not by individual sector market cap.

**Estimated market caps** — analyst estimates, not live AUM data.

**25% weight cap** — inferred from the original Solver output (G-Sec and
Gold both land exactly on 25%), not stated explicitly in the workbook.

**Covariance window mismatch** — per-asset return/vol use the full
2015–2025 history, but the covariance matrix is computed only from
2019-08 onward (REITs' first listed month) — inherited from the original
model, not redesigned.

**The core bug** — the original Excel never built a separate annualized
covariance matrix. It used the monthly one throughout, while combining it
with annualized returns and the annual risk-free rate. That's the root
cause of the Sharpe Ratio / VaR figures looking unusually good. Toggle
"Corrected" mode above to see the consistent-units version.
            """
        )

# ── Live recompute ──────────────────────────────────────────────────────────────

cov = cov_monthly if mode == "replica" else cov_annual
pi_excess = compute_implied_excess_returns(cov, market_weights, lam)
posterior = compute_posterior(cov, pi_excess, views, rf=RISK_FREE_RATE, mode=mode)

opt = optimize_portfolio(
    posterior.loc[ASSET_ORDER].values,
    cov.loc[ASSET_ORDER, ASSET_ORDER].values,
    rf=RISK_FREE_RATE,
)
weights = pd.Series(opt["weights"])[ASSET_ORDER]

s_return = stressed_return(opt["weights"])
if mode == "replica":
    var95 = var_95_replica(opt["return"], opt["volatility"])
else:
    var95 = var_95_corrected(opt["return"], opt["volatility"])

# ── Page header ──────────────────────────────────────────────────────────────────

st.markdown(
    '<div class="ph-wrap">'
    '  <div class="ph-eyebrow">Project 4 · Quant Portfolio Construction</div>'
    '  <div class="ph-title">Black-Litterman<br><span>Portfolio.</span></div>'
    '  <div class="ph-stats">'
    f'    <div><div class="ph-stat-num">{len(ASSET_ORDER)}</div><div class="ph-stat-label">Asset classes</div></div>'
    '    <div class="ph-divider"></div>'
    f'    <div><div class="ph-stat-num">{len(views)}</div><div class="ph-stat-label">Investor views</div></div>'
    '    <div class="ph-divider"></div>'
    f'    <div><div class="ph-stat-num">{lam:.2f}</div><div class="ph-stat-label">Risk aversion (λ)</div></div>'
    '    <div class="ph-divider"></div>'
    f'    <div><div class="ph-stat-num">₹100 Cr</div><div class="ph-stat-label">Mandate size</div></div>'
    '  </div>'
    '</div>',
    unsafe_allow_html=True,
)

# ── Metric cards ──────────────────────────────────────────────────────────────────

st.markdown(
    '<div class="sec-head"><div class="sec-head-label">Portfolio Outputs</div><div class="sec-head-line"></div></div>',
    unsafe_allow_html=True,
)

st.markdown(
    '<div class="metric-row">'
    f'<div class="metric-card"><div class="metric-label">Portfolio Return</div><div class="metric-val" style="color:var(--green)">{opt["return"]:.2%}</div></div>'
    f'<div class="metric-card"><div class="metric-label">Portfolio Volatility</div><div class="metric-val" style="color:var(--sky)">{opt["volatility"]:.2%}</div><div class="metric-sub">{"Monthly cov — not annualized" if mode=="replica" else "Annualized"}</div></div>'
    f'<div class="metric-card"><div class="metric-label">Sharpe Ratio</div><div class="metric-val" style="color:var(--acc)">{opt["sharpe"]:.2f}</div></div>'
    f'<div class="metric-card"><div class="metric-label">Stressed Return (-20% equity)</div><div class="metric-val" style="color:var(--red)">{s_return:.2%}</div></div>'
    f'<div class="metric-card"><div class="metric-label">95% Monthly VaR</div><div class="metric-val" style="color:var(--amber)">{var95:.2%}</div></div>'
    '</div>',
    unsafe_allow_html=True,
)
if mode == "replica":
    st.caption(
        "These figures reproduce the original Excel/slide-deck exactly, including the Sharpe Ratio "
        "comparing an annualized return against a monthly (not annualized) volatility — switch to "
        "Corrected mode in the sidebar to see internally-consistent figures."
    )

# ── Posterior returns + allocation ──────────────────────────────────────────────

st.markdown(
    '<div class="sec-head"><div class="sec-head-label">Posterior Expected Returns</div><div class="sec-head-line"></div></div>',
    unsafe_allow_html=True,
)

col1, col2 = st.columns(2)

with col1:
    labels = [ASSET_LABELS[a] for a in ASSET_ORDER]
    fig = go.Figure(go.Bar(
        x=labels, y=posterior.loc[ASSET_ORDER].values,
        marker_color="#818CF8",
        hovertemplate="%{x}: %{y:.2%}<extra></extra>",
    ))
    fig.update_layout(**PLOTLY_BASE, title="Black-Litterman Posterior Returns", yaxis_tickformat=".0%",
                       xaxis=dict(gridcolor=GRID_COLOR), yaxis=dict(gridcolor=GRID_COLOR), height=380)
    st.plotly_chart(fig, use_container_width=True)

with col2:
    nonzero = weights[weights > 0.001]
    # Slices below 3% are too thin for an inside label without overlapping
    # their neighbors — suppress the label there and rely on hover + the
    # legend (which lists every slice regardless of size) instead.
    slice_labels = [f"{v:.1%}" if v >= 0.03 else "" for v in nonzero.values]
    fig2 = go.Figure(go.Pie(
        labels=[ASSET_LABELS[a] for a in nonzero.index], values=nonzero.values,
        hole=0.55,
        marker=dict(colors=["#818CF8", "#E4C76B", "#10B981", "#38BDF8", "#F59E0B", "#F87171", "#A78BFA", "#34D399"]),
        text=slice_labels, textinfo="text", textposition="inside",
        hovertemplate="%{label}: %{value:.2%}<extra></extra>",
    ))
    fig2.update_layout(**PLOTLY_BASE, title="Optimal Allocation", height=380, showlegend=True)
    st.plotly_chart(fig2, use_container_width=True)

# ── Stress test detail ──────────────────────────────────────────────────────────

st.markdown(
    '<div class="sec-head"><div class="sec-head-label">Stress Scenario</div><div class="sec-head-line"></div></div>',
    unsafe_allow_html=True,
)

stress_df = pd.DataFrame({
    "Asset": [ASSET_LABELS[a] for a in ASSET_ORDER],
    "Weight": weights.loc[ASSET_ORDER].values,
    "Shock": SHOCKS.loc[ASSET_ORDER].values,
    "Contribution": (weights.loc[ASSET_ORDER] * SHOCKS.loc[ASSET_ORDER]).values,
}).set_index("Asset")

st.dataframe(
    stress_df.style.format({"Weight": "{:.2%}", "Shock": "{:.0%}", "Contribution": "{:.2%}"}),
    use_container_width=True,
)
