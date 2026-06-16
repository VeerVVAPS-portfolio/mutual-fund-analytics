"""
Streamlit dashboard — Mutual Fund Analytics Automation (Project 1).

Run: streamlit run dashboard/app.py  (from the project root)
"""

import sys
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from scoring import apply_eligibility_filter, compute_composite_score  # noqa: E402

st.set_page_config(page_title="Fund Rankings", layout="wide")

# ── Shared style constants ────────────────────────────────────────────────────

FONT_COLOR = "#1F2937"        # near-black, readable on any light background
GRID_COLOR = "#E5E7EB"        # subtle grid lines
ACCENT_GREEN = "#059669"      # top-3 bars and highlights
ACCENT_PURPLE = "#6366F1"     # other funds
TOP3_BG = "#D1FAE5"           # light green row highlight
TOP3_FG = "#065F46"           # dark green text on light green — WCAG AA
TRANSPARENT = "rgba(0,0,0,0)" # seamless chart background

PLOTLY_BASE = dict(
    paper_bgcolor=TRANSPARENT,
    plot_bgcolor=TRANSPARENT,
    font=dict(color=FONT_COLOR, family="Inter, sans-serif", size=12),
    margin=dict(l=10, r=10, t=10, b=10),
    hoverlabel=dict(bgcolor="white", font_size=13, font_color=FONT_COLOR),
)

# ── Data ─────────────────────────────────────────────────────────────────────

@st.cache_data
def load_eligible_funds() -> pd.DataFrame:
    schemes = pd.read_csv(PROJECT_ROOT / "data/processed/schemes.csv")
    metrics = pd.read_csv(PROJECT_ROOT / "data/processed/metrics.csv").drop(
        columns=["scheme_name", "category"]
    )
    return apply_eligibility_filter(schemes.merge(metrics, on="scheme_code"))

eligible = load_eligible_funds()

# ── Investor profiles ─────────────────────────────────────────────────────────

PROFILES = {
    "Balanced (Default)": {
        "weights": {"sharpe": 1 / 3, "alpha": 1 / 3, "consistency": 1 / 3},
        "desc": "Equal weight across all three metrics — a sensible starting point for most investors.",
    },
    "Safety First": {
        "weights": {"sharpe": 0.20, "alpha": 0.10, "consistency": 0.70},
        "desc": (
            "Prioritises **Consistency** — funds that repeatedly beat peers "
            "across multiple 3-year windows. Suits conservative investors who value "
            "steady, predictable performance over raw returns."
        ),
    },
    "Return Seeker": {
        "weights": {"sharpe": 0.20, "alpha": 0.70, "consistency": 0.10},
        "desc": (
            "Prioritises **Jensen's Alpha** — the extra return a manager earns beyond "
            "what the fund's market risk alone would predict. "
            "Suits growth-focused investors comfortable with variance."
        ),
    },
    "Risk-Adjusted": {
        "weights": {"sharpe": 0.70, "alpha": 0.20, "consistency": 0.10},
        "desc": (
            "Prioritises **Sharpe Ratio** — return earned per unit of volatility. "
            "Suits investors who want the smoothest ride for the return they receive."
        ),
    },
    "Custom": {
        "weights": None,
        "desc": "Set your own weights using the sliders below.",
    },
}

SHARPE_HELP = (
    "Return earned per unit of risk (volatility) taken. "
    "A Sharpe of 1.0 means you earn 1% excess return for every 1% of volatility — "
    "higher is better. Computed over the trailing 3 years vs a 7% risk-free rate (India G-Sec)."
)
ALPHA_HELP = (
    "The manager's 'skill score'. It measures how much extra return the fund earned "
    "beyond what its market sensitivity (Beta) alone predicts via CAPM. "
    "Positive = manager added value; negative = lagged behind even accounting for risk."
)
CONSISTENCY_HELP = (
    "Percentage of rolling 3-year windows where this fund beat its category average. "
    "60% means the fund outperformed peers in 6 out of every 10 three-year periods — "
    "more reliable than a single snapshot return."
)

# ── Sidebar ───────────────────────────────────────────────────────────────────

with st.sidebar:
    st.header("Category")
    short_name = lambda c: c.replace("Equity Scheme - ", "").replace(" Fund", "")
    categories = sorted(eligible["category"].unique())
    category = st.selectbox(
        "Fund category",
        categories,
        format_func=short_name,
        label_visibility="collapsed",
    )

    st.divider()

    st.header("Investor Style")
    profile_name = st.selectbox(
        "Profile",
        list(PROFILES.keys()),
        label_visibility="collapsed",
    )
    profile = PROFILES[profile_name]
    st.caption(profile["desc"])

    if profile["weights"] is None:
        st.markdown("**Adjust weights** — auto-normalised to 100%")
        sharpe_w     = st.slider("Sharpe Ratio",    0.0, 1.0, 1/3, 0.05, help=SHARPE_HELP)
        alpha_w      = st.slider("Jensen's Alpha",  0.0, 1.0, 1/3, 0.05, help=ALPHA_HELP)
        consistency_w = st.slider("Consistency",    0.0, 1.0, 1/3, 0.05, help=CONSISTENCY_HELP)
        total = sharpe_w + alpha_w + consistency_w
        if total == 0:
            st.error("At least one weight must be greater than 0.")
            st.stop()
        weights = {
            "sharpe": sharpe_w / total,
            "alpha": alpha_w / total,
            "consistency": consistency_w / total,
        }
    else:
        weights = profile["weights"]

    st.caption(
        f"Effective weights — "
        f"Sharpe **{weights['sharpe']:.0%}** · "
        f"Alpha **{weights['alpha']:.0%}** · "
        f"Consistency **{weights['consistency']:.0%}**"
    )

    st.divider()

    with st.expander("What do these metrics mean?"):
        st.markdown(
            """
**Sharpe Ratio**
Return per unit of volatility. Higher is better. Above 1.0 is considered strong.

---
**Jensen's Alpha**
Manager skill score. Extra return beyond what market risk alone predicts.
Positive = manager adds value.

---
**Consistency**
% of rolling 3-year windows where the fund beat its category average.
More reliable than a single snapshot return.

---
**Beta**
Fund movement relative to NIFTY 50. Beta 1.2 = 20% more volatile than the index.

---
**5Y Return (CAGR)**
Compounded annual growth over 5 years — the annualised return from a lump-sum 5 years ago.
            """
        )

# ── Scoring ───────────────────────────────────────────────────────────────────

scored      = compute_composite_score(eligible, weights)
category_df = scored[scored["category"] == category].sort_values("category_rank")
top         = category_df.iloc[0]
cat_label   = short_name(category)

# ── Page header ───────────────────────────────────────────────────────────────

st.title(f"Mutual Fund Rankings — {cat_label}")
st.caption(
    f"{len(eligible)} funds eligible across {eligible['category'].nunique()} categories "
    f"(AUM ≥ ₹1,000 Cr · 5-year track record)   |   "
    f"**{len(category_df)} eligible** in {cat_label}"
)

st.divider()

# ── Top pick ──────────────────────────────────────────────────────────────────

st.subheader("Top Pick")

# Truncate long fund names cleanly
def short_fund_name(name: str, max_len: int = 32) -> str:
    name = name.replace("Equity Scheme - ", "").replace("(Direct Plan)", "").strip()
    return name if len(name) <= max_len else name[:max_len].rstrip() + "..."

top_display = short_fund_name(top["scheme_name"])

# Card layout: name + AMC on the left, three key stats on the right
left, mid, r1, r2, r3 = st.columns([3, 2, 1.5, 1.5, 1.5])

with left:
    st.markdown(f"**{top_display}**")
    st.caption(top["scheme_name"])          # full name in small text below

with mid:
    st.markdown(f"**AMC**")
    st.write(top["amc"])

with r1:
    st.metric("5Y Return", f"{top['return_5y']:.1%}")

with r2:
    st.metric("Sharpe", f"{top['sharpe']:.2f}", help=SHARPE_HELP)

with r3:
    st.metric("Consistency", f"{top['consistency']:.0%}", help=CONSISTENCY_HELP)

st.divider()

# ── Ranked table ──────────────────────────────────────────────────────────────

st.subheader("All Eligible Funds")

display_cols = {
    "category_rank": "Rank",
    "scheme_name":   "Fund",
    "amc":           "AMC",
    "total_aum_cr":  "AUM (Cr)",
    "return_5y":     "5Y Return",
    "beta":          "Beta",
    "sharpe":        "Sharpe",
    "alpha":         "Alpha",
    "consistency":   "Consistency",
    "composite_score": "Score",
}
table = category_df[list(display_cols.keys())].rename(columns=display_cols)


def highlight_top3(row):
    if row["Rank"] <= 3:
        style = f"background-color: {TOP3_BG}; color: {TOP3_FG}; font-weight: 600"
    else:
        style = f"color: {FONT_COLOR}"
    return [style] * len(row)


styled = (
    table.style
    .format({
        "AUM (Cr)":  "{:,.0f}",
        "5Y Return": "{:.1%}",
        "Beta":      "{:.2f}",
        "Sharpe":    "{:.2f}",
        "Alpha":     "{:.1%}",
        "Consistency": "{:.1%}",
        "Score":     "{:.1%}",
    })
    .apply(highlight_top3, axis=1)
)

st.dataframe(styled, use_container_width=True, hide_index=True)

st.divider()

# ── Horizontal bar chart ──────────────────────────────────────────────────────

st.subheader("Composite Score — All Funds")

chart_df = category_df.copy()
chart_df["label"] = (
    "#" + chart_df["category_rank"].astype(str)
    + "  " + chart_df["scheme_name"]
              .str.replace(r"Equity Scheme\s*-\s*", "", regex=True)
              .str.replace(" Fund", "")
              .str.strip()
              .str[:38]
)
chart_df["score_pct"] = (chart_df["composite_score"] * 100).round(1).astype(str) + "%"
chart_df_sorted = chart_df.sort_values("composite_score")

bar_colors = [ACCENT_GREEN if r <= 3 else ACCENT_PURPLE
              for r in chart_df_sorted["category_rank"]]

bar_fig = go.Figure(go.Bar(
    x=chart_df_sorted["composite_score"],
    y=chart_df_sorted["label"],
    orientation="h",
    text=chart_df_sorted["score_pct"],
    textposition="outside",
    cliponaxis=False,
    marker_color=bar_colors,
    marker_line_width=0,
    hovertemplate="<b>%{y}</b><br>Score: %{x:.1%}<extra></extra>",
))

bar_fig.update_layout(
    **PLOTLY_BASE,
    margin=dict(l=10, r=60, t=10, b=40),
    height=max(320, len(chart_df) * 38),
    xaxis=dict(
        tickformat=".0%",
        range=[0, 1.18],
        showgrid=True,
        gridcolor=GRID_COLOR,
        zeroline=False,
        tickfont=dict(color=FONT_COLOR, size=11),
        title=dict(text="Composite Score (percentile rank vs category peers)",
                   font=dict(color=FONT_COLOR, size=11)),
    ),
    yaxis=dict(
        autorange=True,
        tickfont=dict(color=FONT_COLOR, size=11),
        showgrid=False,
    ),
)

# Legend annotation
bar_fig.add_annotation(
    x=1.15, y=0.02, xref="paper", yref="paper",
    text=(
        f"<span style='color:{ACCENT_GREEN}'>&#9632;</span> Top 3  "
        f"<span style='color:{ACCENT_PURPLE}'>&#9632;</span> Others"
    ),
    showarrow=False,
    font=dict(size=11, color=FONT_COLOR),
    align="right",
    xanchor="right",
)

st.plotly_chart(bar_fig, use_container_width=True)

st.divider()

# ── Radar chart (top 3) ───────────────────────────────────────────────────────

st.subheader("Top 3 — Head-to-Head Comparison")
st.caption(
    "Each axis shows the fund's percentile rank within the category. "
    "Outer edge = 100th percentile (best in category)."
)

top3 = category_df[category_df["category_rank"] <= 3].copy()
radar_metrics = ["sharpe_pct", "alpha_pct", "consistency_pct"]
radar_labels  = ["Sharpe", "Alpha", "Consistency"]
radar_colors  = [ACCENT_GREEN, ACCENT_PURPLE, "#F59E0B"]

radar_fig = go.Figure()
for i, (_, row) in enumerate(top3.iterrows()):
    vals = [row[m] for m in radar_metrics] + [row[radar_metrics[0]]]
    short = short_fund_name(row["scheme_name"], max_len=28)
    radar_fig.add_trace(go.Scatterpolar(
        r=vals,
        theta=radar_labels + [radar_labels[0]],
        fill="toself",
        name=f"#{int(row['category_rank'])}  {short}",
        line=dict(color=radar_colors[i], width=2),
        fillcolor=radar_colors[i],
        opacity=0.18,
    ))

radar_fig.update_layout(
    **PLOTLY_BASE,
    margin=dict(l=40, r=40, t=20, b=60),
    height=400,
    polar=dict(
        bgcolor=TRANSPARENT,
        radialaxis=dict(
            visible=True,
            range=[0, 1],
            tickformat=".0%",
            tickfont=dict(size=10, color=FONT_COLOR),
            gridcolor=GRID_COLOR,
            linecolor=GRID_COLOR,
        ),
        angularaxis=dict(
            tickfont=dict(size=13, color=FONT_COLOR),
            linecolor=GRID_COLOR,
            gridcolor=GRID_COLOR,
        ),
    ),
    showlegend=True,
    legend=dict(
        orientation="h",
        yanchor="bottom", y=-0.28,
        xanchor="center", x=0.5,
        font=dict(color=FONT_COLOR, size=11),
    ),
)

st.plotly_chart(radar_fig, use_container_width=True)
