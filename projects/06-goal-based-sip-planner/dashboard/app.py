"""
app.py — Goal-Based SIP Planner
Wizard: add/edit goals -> income & expenses -> results (affordability, breakdown, fund picks).
"""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from cashflow_projection import project_cashflow
from formatting import format_inr_compact
from fund_recommender import recommend_for_goal
from funding_sequencer import build_staggered_plan
from advisory import build_advisory_note
from goal_calculator import solve_goal
from protection import (
    recommended_life_cover, recommended_health_cover, recommended_emergency_fund,
    compute_foir, HEALTH_COVER_BY_TIER,
)
from report_pdf import build_pdf_report

# ── Page config ────────────────────────────────────────────────────────────

st.set_page_config(
    page_title="Goal-Based SIP Planner",
    page_icon="🎯",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ── CSS (shared dark theme, matches Projects 1/2/4) ───────────────────────

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
    --acc: #818CF8; --green: #10B981; --amber: #F59E0B; --red: #EF4444; --sky: #38BDF8;
}
@keyframes fadeUp { from{opacity:0;transform:translateY(16px)} to{opacity:1;transform:translateY(0)} }
@keyframes scalePop { from{opacity:0;transform:scale(0.92)} to{opacity:1;transform:scale(1)} }

[data-testid="stAppViewContainer"], [data-testid="stMain"], [data-testid="stHeader"] {
    background-color: var(--bg) !important;
}
[data-testid="stHeader"] { background-color: transparent !important; }
[data-testid="stWidgetLabel"] p, .stRadio label p, .stSlider label p { color: var(--t2) !important; }
[data-testid="stCaptionContainer"] { opacity: 1 !important; }
[data-testid="stCaptionContainer"] p { color: var(--t2) !important; }
.block-container { padding-top: 2.5rem !important; }
[data-testid="stSidebar"] { background: var(--surf) !important; border-right: 1px solid var(--bdr) !important; }

.landing-wrap { max-width: 680px; margin: 3rem auto 0; text-align: center; animation: fadeUp 0.7s ease both; }
.landing-eyebrow { font-size: 0.68rem; font-weight: 600; letter-spacing: 0.14em; text-transform: uppercase; color: var(--acc); margin-bottom: 1.2rem; }
.landing-title { font-family: 'Space Grotesk', sans-serif; font-size: 3.2rem; font-weight: 700; line-height: 1.05; letter-spacing: -0.03em; color: var(--t1); margin-bottom: 1rem; }
.landing-title span { color: var(--acc); }
.landing-sub { font-size: 1rem; color: var(--t3); max-width: 480px; margin: 0 auto 2.5rem; line-height: 1.7; }

.goal-card { background: var(--surf); border: 1px solid var(--bdr); border-radius: 10px; padding: 1.2rem 1.4rem; margin-bottom: 0.8rem; animation: fadeUp 0.4s ease both; }
.goal-card-title { font-family: 'Space Grotesk', sans-serif; font-size: 1.1rem; font-weight: 700; color: var(--t1); display: flex; align-items: center; gap: 0.4rem; }
.goal-card-sub { font-size: 0.78rem; color: var(--t3); margin-top: 0.25rem; }
.priority-badge {
    display: inline-flex; align-items: center; padding: 0.1rem 0.5rem; border-radius: 999px;
    font-size: 0.6rem; font-weight: 700; text-transform: uppercase; letter-spacing: 0.04em;
}

.sip-hero { text-align: center; padding: 1.5rem 0; border-top: 1px solid var(--rule); border-bottom: 1px solid var(--rule); margin: 1rem 0; }
.sip-hero-label { font-size: 0.65rem; font-weight: 600; text-transform: uppercase; letter-spacing: 0.12em; color: var(--t4); margin-bottom: 0.5rem; }
.sip-hero-amount { font-family: 'Space Grotesk', sans-serif; font-size: 2.8rem; font-weight: 700; color: var(--green); letter-spacing: -0.02em; animation: scalePop 0.4s ease both; }

.metric-card { background: var(--surf); border: 1px solid var(--bdr); border-radius: 10px; padding: 1rem 0.6rem; text-align: center; }
.mc-num { font-family: 'Space Grotesk', sans-serif; font-size: 1.35rem; font-weight: 700; color: var(--t1); white-space: nowrap; }
.mc-label { font-size: 0.62rem; color: var(--t4); margin-top: 0.3rem; text-transform: uppercase; letter-spacing: 0.05em; }

.warn-banner { display: flex; align-items: center; gap: 0.6rem; border: 1px solid rgba(239,68,68,0.2); border-left: 2px solid var(--red); border-radius: 0 6px 6px 0; padding: 0.6rem 1rem; font-size: 0.8rem; color: #FCA5A5; margin-bottom: 0.6rem; background: rgba(239,68,68,0.04); }
.ok-banner { display: flex; align-items: center; gap: 0.6rem; border: 1px solid rgba(16,185,129,0.2); border-left: 2px solid var(--green); border-radius: 0 6px 6px 0; padding: 0.6rem 1rem; font-size: 0.8rem; color: #6EE7B7; margin-bottom: 0.6rem; background: rgba(16,185,129,0.04); }
.caution-banner { display: flex; align-items: center; gap: 0.6rem; border: 1px solid rgba(245,158,11,0.2); border-left: 2px solid var(--amber); border-radius: 0 6px 6px 0; padding: 0.6rem 1rem; font-size: 0.8rem; color: #FCD34D; margin-bottom: 0.6rem; background: rgba(245,158,11,0.04); }

.fund-pick { display: flex; align-items: center; gap: 0.4rem; padding: 0.22rem 0; font-size: 0.76rem; color: var(--t3); }
.fund-rank { background: rgba(16,185,129,0.08); color: var(--green); font-size: 0.64rem; font-weight: 700; padding: 0.06rem 0.35rem; border-radius: 3px; flex-shrink:0; }

.advisor-note { background: var(--surf); border: 1px solid var(--bdr); border-left: 3px solid var(--acc); border-radius: 0 10px 10px 0; padding: 1.3rem 1.5rem; margin-bottom: 1.2rem; }
.advisor-label { font-size: 0.65rem; font-weight: 600; text-transform: uppercase; letter-spacing: 0.12em; color: var(--acc); margin-bottom: 0.6rem; display: flex; align-items: center; gap: 0.4rem; }
.advisor-headline { font-family: 'Space Grotesk', sans-serif; font-size: 1.15rem; font-weight: 700; color: var(--t1); margin-bottom: 0.7rem; line-height: 1.4; }
.advisor-para { font-size: 0.86rem; color: var(--t2); line-height: 1.7; margin-bottom: 0.7rem; }
.advisor-para:last-child { margin-bottom: 0; }
.advisor-risk { font-size: 0.8rem; color: #FCD34D; line-height: 1.7; margin-top: 0.8rem; padding-top: 0.8rem; border-top: 1px solid var(--rule); display: flex; gap: 0.5rem; }

.disclaimer { border-top: 1px solid var(--rule); padding-top: 1rem; font-size: 0.72rem; color: var(--t4); line-height: 1.7; margin-top: 1.5rem; }
.footer { text-align: center; margin-top: 1rem; font-size: 0.72rem; color: var(--t4); }
.footer a { color: var(--acc); text-decoration: none; }
</style>
""", unsafe_allow_html=True)

# ── Constants ──────────────────────────────────────────────────────────────

CATEGORY_DEFAULTS = {
    "Education":  {"inflation": 0.07, "return": 0.12, "step_up": 0.0},
    "Marriage":   {"inflation": 0.07, "return": 0.12, "step_up": 0.0},
    "Home":       {"inflation": 0.08, "return": 0.12, "step_up": 0.10},
    "Car":        {"inflation": 0.05, "return": 0.10, "step_up": 0.0},
    "Retirement": {"inflation": 0.06, "return": 0.12, "step_up": 0.05},
    "Other":      {"inflation": 0.06, "return": 0.10, "step_up": 0.0},
}
PRIORITY_OPTIONS = ["Must-have", "Good-to-have", "Dream goal"]
PRIORITY_ORDER = {p: i for i, p in enumerate(PRIORITY_OPTIONS)}
PRIORITY_STYLES = {
    "Must-have":     ("#FCA5A5", "rgba(239,68,68,0.1)",  "rgba(239,68,68,0.3)"),
    "Good-to-have":  ("#FCD34D", "rgba(245,158,11,0.1)", "rgba(245,158,11,0.3)"),
    "Dream goal":    ("#A1A1AA", "rgba(161,161,170,0.1)","rgba(161,161,170,0.25)"),
}

RETURN_HELP = (
    "Expected annual return your SIP investments will earn. Equity mutual funds have "
    "historically returned ~10-12% CAGR long-term in India; debt funds ~6-8%. A higher "
    "assumption lowers the required SIP but assumes more market risk."
)
STEPUP_HELP = (
    "Optional: increases your monthly SIP by this % every year (e.g. in line with a salary "
    "hike) instead of investing a flat amount throughout the goal's horizon. Leave at 0% for a flat SIP."
)

def inflation_help(category: str) -> str:
    default = CATEGORY_DEFAULTS[category]["inflation"]
    return (
        f"Typical {category} cost inflation in India runs around {default*100:.0f}%/yr. "
        "This default is pre-filled but fully editable — adjust if your specific goal trends differently."
    )

PLOTLY_BASE = dict(
    paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
    font=dict(color="#71717A", family="Inter, sans-serif", size=12),
    hoverlabel=dict(bgcolor="#18181F", font_size=12, font_color="#F4F4F5", bordercolor="#27272A"),
)

# ── Session state ────────────────────────────────────────────────────────

if "step" not in st.session_state:
    st.session_state.step = 0
if "goals" not in st.session_state:
    st.session_state.goals = []  # list of input dicts
if "editing_index" not in st.session_state:
    st.session_state.editing_index = None
if "draft" not in st.session_state:
    st.session_state.draft = None
if "form_session" not in st.session_state:
    st.session_state.form_session = 0
if "income_inputs" not in st.session_state:
    st.session_state.income_inputs = {}
if "loans" not in st.session_state:
    st.session_state.loans = []
if "loan_editing_index" not in st.session_state:
    st.session_state.loan_editing_index = None
if "loan_draft" not in st.session_state:
    st.session_state.loan_draft = None
if "loan_form_session" not in st.session_state:
    st.session_state.loan_form_session = 0
if "protection_inputs" not in st.session_state:
    st.session_state.protection_inputs = {}

# ── Sidebar ────────────────────────────────────────────────────────────────

with st.sidebar:
    st.markdown(
        '<div style="font-family:\'Space Grotesk\',sans-serif;font-size:1rem;font-weight:700;color:#F4F4F5">Goal-Based SIP Planner</div>'
        '<div style="font-size:0.65rem;color:#52525B;text-transform:uppercase;letter-spacing:0.08em">Solve, don\'t guess</div>',
        unsafe_allow_html=True,
    )
    st.divider()
    if st.session_state.step > 0:
        if st.button("Start Over", use_container_width=True):
            st.session_state.step = 0
            st.session_state.goals = []
            st.session_state.editing_index = None
            st.session_state.draft = None
            st.session_state.income_inputs = {}
            st.session_state.loans = []
            st.session_state.loan_editing_index = None
            st.session_state.loan_draft = None
            st.session_state.protection_inputs = {}
            st.session_state.form_session += 1
            st.session_state.loan_form_session += 1
            st.rerun()

# ── Helpers ──────────────────────────────────────────────────────────────

def centered(ratio=2.2):
    _, c, _ = st.columns([1, ratio, 1])
    return c


def compute_results():
    """Run solve_goal for every goal in session state, return enriched list."""
    results = []
    for g in st.session_state.goals:
        r = solve_goal(
            present_value=g["amount"],
            inflation_rate=g["inflation"],
            years=g["years"],
            annual_return=g["return"],
            target_is_future_value=g["amount_is_future_value"],
            step_up_pct=g["step_up"],
        )
        results.append({**g, "result": r})
    return results


def sorted_by_priority(items: list[dict]) -> list[dict]:
    return sorted(items, key=lambda g: PRIORITY_ORDER.get(g.get("priority", "Dream goal"), 99))


def apply_inr_yaxis(fig, values: list[float], num_ticks: int = 5):
    """Label y-axis ticks in Indian lakh/crore notation instead of Plotly's default SI suffixes."""
    vmin, vmax = min(values), max(values)
    if vmax == vmin:
        vmax = vmin + 1
    ticks = [vmin + (vmax - vmin) * i / (num_ticks - 1) for i in range(num_ticks)]
    fig.update_yaxes(tickmode="array", tickvals=ticks, ticktext=[format_inr_compact(t) for t in ticks])


# ── Screens ────────────────────────────────────────────────────────────────

def render_landing():
    with centered():
        st.markdown(
            '<div class="landing-wrap">'
            '  <div class="landing-eyebrow"><i class="bi bi-bullseye"></i> Goal-Based Planning</div>'
            '  <div class="landing-title">How Much SIP<br><span>Do You Actually Need?</span></div>'
            '  <div class="landing-sub">Add your financial goals — education, marriage, a house, anything — '
            'and this tool solves for the exact monthly SIP required to hit each one. '
            'No guessing, no rounding to a number that sounds nice.</div>'
            '</div>',
            unsafe_allow_html=True,
        )
        if st.button("Get Started →", type="primary", use_container_width=True):
            st.session_state.step = 1
            st.rerun()


def render_goal_builder():
    with centered(2.6):
        st.markdown("### Your Goals")
        st.caption("Add one or more goals. Each is solved independently for its required monthly SIP.")

        for i, g in enumerate(st.session_state.goals):
            c1, c2, c3 = st.columns([5, 1, 1])
            with c1:
                value_label = "future value" if g["amount_is_future_value"] else "today's value"
                step_up_label = f' · {g["step_up"]*100:.0f}% step-up' if g["step_up"] > 0 else ""
                color, bg, border = PRIORITY_STYLES.get(g.get("priority", "Dream goal"), PRIORITY_STYLES["Dream goal"])
                badge = (
                    f'<span class="priority-badge" style="color:{color};background:{bg};'
                    f'border:1px solid {border}">{g.get("priority", "Dream goal")}</span>'
                )
                st.markdown(
                    f'<div class="goal-card"><div class="goal-card-title">{g["name"]}{badge}</div>'
                    f'<div class="goal-card-sub">{g.get("category", "Other")} · {format_inr_compact(g["amount"])} ({value_label}) '
                    f'· {g["years"]:.0f} yrs · {g["return"]*100:.0f}% return{step_up_label}</div></div>',
                    unsafe_allow_html=True,
                )
            with c2:
                if st.button("Edit", key=f"edit_{i}", use_container_width=True):
                    st.session_state.editing_index = i
                    st.session_state.draft = dict(g)
                    st.rerun()
            with c3:
                if st.button("Remove", key=f"remove_{i}", use_container_width=True):
                    st.session_state.goals.pop(i)
                    st.session_state.editing_index = None
                    st.session_state.draft = None
                    st.rerun()

        st.markdown("---")

        editing = st.session_state.editing_index is not None
        draft = st.session_state.draft or {}
        # base_token forces a fresh set of widgets whenever we switch between "adding
        # new" and "editing goal N", between two different goals, or add a second goal
        # after the first (form_session bumps on every save/cancel).
        base_token = f"edit_{st.session_state.editing_index}" if editing else f"new_{st.session_state.form_session}"

        st.markdown(f"**{'Edit goal' if editing else 'Add a goal'}**")

        # Deliberately NOT wrapped in st.form: category-dependent slider defaults need
        # to update the instant the category changes, and st.form only reruns the
        # script (and reads widget values) once, on submit — by which point the
        # sliders would already be locked to whatever category was selected first.
        name = st.text_input("Goal name", value=draft.get("name", ""), placeholder="e.g. Child's Education", key=f"name_{base_token}")

        category_list = list(CATEGORY_DEFAULTS.keys())
        default_category = draft.get("category", category_list[0])
        category_choice = st.selectbox(
            "Category", category_list,
            index=category_list.index(default_category) if default_category in category_list else 0,
            key=f"category_{base_token}",
        )

        priority_choice = st.selectbox(
            "Priority", PRIORITY_OPTIONS,
            index=PRIORITY_OPTIONS.index(draft.get("priority", "Must-have")),
            key=f"priority_{base_token}",
            help="Helps you (and the affordability check) tell which goals are non-negotiable versus nice-to-have.",
        )

        category_defaults = CATEGORY_DEFAULTS[category_choice]
        # Sliders remount (fresh category-based defaults) whenever the category changes,
        # not just when base_token changes.
        slider_token = f"{base_token}_{category_choice}"

        col1, col2 = st.columns(2)
        with col1:
            amount = st.number_input(
                "Target amount (₹)", min_value=0, value=int(draft.get("amount", 2_000_000)), step=50_000,
                key=f"amount_{base_token}",
            )
            amount_is_future_value = st.checkbox(
                "This is already the future-date target (skip inflation adjustment)",
                value=draft.get("amount_is_future_value", False), key=f"fv_{base_token}",
            )
            years = st.number_input(
                "Years to goal", min_value=1, max_value=40, value=int(draft.get("years", 15)),
                key=f"years_{base_token}",
            )
        with col2:
            inflation_pct = st.slider(
                "Goal inflation rate", 0, 15,
                round(draft.get("inflation", category_defaults["inflation"]) * 100), 1,
                format="%d%%", key=f"inflation_{slider_token}", help=inflation_help(category_choice),
            )
            return_pct = st.slider(
                "Expected annual return", 0, 20,
                round(draft.get("return", category_defaults["return"]) * 100), 1,
                format="%d%%", key=f"return_{slider_token}", help=RETURN_HELP,
            )
            stepup_pct = st.slider(
                "Annual SIP step-up (0 = flat SIP)", 0, 30,
                round(draft.get("step_up", category_defaults["step_up"]) * 100), 1,
                format="%d%%", key=f"stepup_{slider_token}", help=STEPUP_HELP,
            )
            inflation, annual_return, step_up = inflation_pct / 100, return_pct / 100, stepup_pct / 100

        submitted = st.button(
            "Save Changes" if editing else "Add Goal", type="primary", use_container_width=True,
        )
        if submitted and name and amount > 0:
            new_goal = {
                "name": name,
                "category": category_choice,
                "priority": priority_choice,
                "amount": amount,
                "amount_is_future_value": amount_is_future_value,
                "years": years,
                "inflation": inflation,
                "return": annual_return,
                "step_up": step_up,
            }
            if editing:
                st.session_state.goals[st.session_state.editing_index] = new_goal
            else:
                st.session_state.goals.append(new_goal)
            st.session_state.editing_index = None
            st.session_state.draft = None
            st.session_state.form_session += 1
            st.rerun()

        if editing:
            if st.button("Cancel Edit"):
                st.session_state.editing_index = None
                st.session_state.draft = None
                st.session_state.form_session += 1
                st.rerun()

        st.markdown("<br>", unsafe_allow_html=True)
        if st.session_state.goals:
            if st.button("Continue to Income & Expenses →", type="primary", use_container_width=True):
                st.session_state.step = 2
                st.rerun()
        else:
            st.caption("Add at least one goal to continue.")


def render_income_step():
    with centered(2.4):
        st.markdown("### Income & Expenses")
        st.caption(
            "Used to check whether your total required SIP is actually affordable, year over year — "
            "before you see the plan, not buried in a tab afterward."
        )

        defaults = st.session_state.income_inputs
        default_horizon = defaults.get("horizon") or int(max((g["years"] for g in st.session_state.goals), default=15))

        c1, c2 = st.columns(2)
        with c1:
            salary = st.number_input("Starting annual salary (₹)", min_value=0, value=int(defaults.get("salary", 1_200_000)), step=50_000)
            hike_pct = st.slider("Annual salary hike %", 0, 30, round(defaults.get("hike", 0.08) * 100), 1, format="%d%%")
            horizon = st.number_input("Projection horizon (years)", min_value=1, max_value=40, value=default_horizon)
        with c2:
            expenses = st.number_input("Starting annual expenses (₹)", min_value=0, value=int(defaults.get("expenses", 600_000)), step=50_000)
            expense_inflation_pct = st.slider("Expense inflation %", 0, 20, round(defaults.get("expense_inflation", 0.06) * 100), 1, format="%d%%")
            emergency_savings = st.number_input(
                "Current liquid savings / emergency fund (₹)", min_value=0,
                value=int(defaults.get("emergency_savings", 0)), step=10_000,
                help="Cash, savings account, liquid funds, FDs you could access within a few days. Used to check against the recommended emergency-fund target.",
            )

        st.markdown("---")
        st.markdown("**Loans & EMIs**")
        st.caption(
            "List every active EMI separately — this feeds your affordability check and lets the "
            "Protection tab work out how much existing debt your family would need to cover."
        )

        for i, loan in enumerate(st.session_state.loans):
            lc1, lc2, lc3 = st.columns([5, 1, 1])
            with lc1:
                st.markdown(
                    f'<div class="goal-card"><div class="goal-card-title">{loan["purpose"]}</div>'
                    f'<div class="goal-card-sub">{format_inr_compact(loan["emi"])}/month · '
                    f'{loan["remaining_months"]} months left · {loan["rate"]*100:.1f}% p.a.</div></div>',
                    unsafe_allow_html=True,
                )
            with lc2:
                if st.button("Edit", key=f"loan_edit_{i}", use_container_width=True):
                    st.session_state.loan_editing_index = i
                    st.session_state.loan_draft = dict(loan)
                    st.rerun()
            with lc3:
                if st.button("Remove", key=f"loan_remove_{i}", use_container_width=True):
                    st.session_state.loans.pop(i)
                    st.session_state.loan_editing_index = None
                    st.session_state.loan_draft = None
                    st.rerun()

        loan_editing = st.session_state.loan_editing_index is not None
        loan_draft = st.session_state.loan_draft or {}
        loan_token = f"loanedit_{st.session_state.loan_editing_index}" if loan_editing else f"loannew_{st.session_state.loan_form_session}"

        st.markdown(f"_{'Edit loan' if loan_editing else 'Add a loan / EMI'}_")
        loan_purposes = ["Home Loan", "Car Loan", "Personal Loan", "Education Loan", "Credit Card EMI", "Other"]
        lcol1, lcol2, lcol3 = st.columns(3)
        with lcol1:
            purpose = st.selectbox(
                "Purpose", loan_purposes,
                index=loan_purposes.index(loan_draft.get("purpose", "Home Loan")) if loan_draft.get("purpose") in loan_purposes else 0,
                key=f"loan_purpose_{loan_token}",
            )
        with lcol2:
            loan_emi = st.number_input(
                "EMI (₹/month)", min_value=0, value=int(loan_draft.get("emi", 20_000)), step=1_000,
                key=f"loan_emi_{loan_token}",
            )
        with lcol3:
            loan_remaining_months = st.number_input(
                "Months remaining", min_value=1, max_value=480, value=int(loan_draft.get("remaining_months", 60)),
                key=f"loan_months_{loan_token}",
            )
        loan_rate_pct = st.slider(
            "Interest rate (% p.a.)", 0, 24, round(loan_draft.get("rate", 0.09) * 100), 1,
            format="%d%%", key=f"loan_rate_{loan_token}",
            help="Used to back out how much principal is actually still outstanding — needed for the life-insurance debt check. Doesn't affect your EMI affordability math.",
        )
        loan_rate = loan_rate_pct / 100

        loan_submitted = st.button(
            "Save Changes" if loan_editing else "Add Loan", key=f"loan_submit_{loan_token}", use_container_width=True,
        )
        if loan_submitted and loan_emi > 0:
            new_loan = {"purpose": purpose, "emi": loan_emi, "remaining_months": loan_remaining_months, "rate": loan_rate}
            if loan_editing:
                st.session_state.loans[st.session_state.loan_editing_index] = new_loan
            else:
                st.session_state.loans.append(new_loan)
            st.session_state.loan_editing_index = None
            st.session_state.loan_draft = None
            st.session_state.loan_form_session += 1
            st.rerun()

        if loan_editing:
            if st.button("Cancel Loan Edit"):
                st.session_state.loan_editing_index = None
                st.session_state.loan_draft = None
                st.session_state.loan_form_session += 1
                st.rerun()

        total_emi_monthly = sum(loan["emi"] for loan in st.session_state.loans)
        fixed_obligations = total_emi_monthly * 12
        if st.session_state.loans:
            st.caption(f"Total fixed obligations: {format_inr_compact(total_emi_monthly)}/month ({format_inr_compact(fixed_obligations)}/year), feeding into your affordability check.")

        hike, expense_inflation = hike_pct / 100, expense_inflation_pct / 100

        st.session_state.income_inputs = {
            "salary": salary, "hike": hike, "horizon": horizon,
            "expenses": expenses, "expense_inflation": expense_inflation,
            "fixed_obligations": fixed_obligations, "emergency_savings": emergency_savings,
        }

        st.markdown("<br>", unsafe_allow_html=True)
        bcol, ncol = st.columns([1, 3])
        with bcol:
            if st.button("← Back"):
                st.session_state.step = 1
                st.rerun()
        with ncol:
            if st.button("Continue to Protection →", type="primary", use_container_width=True):
                st.session_state.step = 3
                st.rerun()


def render_protection_step():
    with centered(2.4):
        st.markdown("### Protection")
        st.caption(
            "A wealth manager checks insurance and emergency cover before getting excited about goals — "
            "an unprotected family can lose everything a goal plan was building toward. A few questions:"
        )

        defaults = st.session_state.protection_inputs
        c1, c2 = st.columns(2)
        with c1:
            dependents = st.number_input(
                "Number of financial dependents", min_value=0, max_value=10,
                value=int(defaults.get("dependents", 2)),
                help="Spouse, children, dependent parents — anyone who relies on your income. Used to size both life and health cover.",
            )
            current_life_cover = st.number_input(
                "Current life insurance cover (₹)", min_value=0,
                value=int(defaults.get("current_life_cover", 0)), step=100_000,
                help="Total sum assured across all term/life policies. Enter 0 if you have none.",
            )
        with c2:
            city_tier = st.selectbox(
                "City tier (for health cover benchmark)", list(HEALTH_COVER_BY_TIER.keys()),
                index=list(HEALTH_COVER_BY_TIER.keys()).index(defaults.get("city_tier", "Metro / Tier-1")),
                help="Healthcare costs vary sharply by city — metro hospital bills run well above tier-2/3 towns.",
            )
            current_health_cover = st.number_input(
                "Current health insurance cover (₹)", min_value=0,
                value=int(defaults.get("current_health_cover", 0)), step=100_000,
                help="Family floater sum insured, including any employer-provided cover. Enter 0 if you have none — and note employer cover usually ends when you leave the job.",
            )

        st.session_state.protection_inputs = {
            "dependents": dependents, "current_life_cover": current_life_cover,
            "current_health_cover": current_health_cover, "city_tier": city_tier,
        }

        st.markdown("<br>", unsafe_allow_html=True)
        bcol, ncol = st.columns([1, 3])
        with bcol:
            if st.button("← Back", key="protection_back"):
                st.session_state.step = 2
                st.rerun()
        with ncol:
            if st.button("See My Plan →", type="primary", use_container_width=True, key="protection_continue"):
                st.session_state.step = 4
                st.rerun()


def render_results():
    results = sorted_by_priority(compute_results())
    total_sip = sum(r["result"].monthly_sip for r in results)

    with centered(2.8):
        st.markdown(
            '<div style="display:flex;align-items:center;gap:0.5rem;border:1px solid rgba(129,140,248,0.2);'
            'border-left:2px solid var(--acc);border-radius:0 6px 6px 0;padding:0.6rem 1rem;'
            'font-size:0.8rem;color:#A5B4FC;margin-bottom:0.6rem;background:rgba(129,140,248,0.04)">'
            '<i class="bi bi-lightbulb"></i><span>Most goal calculators pick a SIP amount that sounds '
            'round, then hope it\'s enough. This one always solves backwards from your target — checked '
            'against the original case study this is based on, the "round number" approach under-funded '
            'two of three goals by 6–8%.</span></div>',
            unsafe_allow_html=True,
        )
        st.markdown(
            f'<div class="sip-hero">'
            f'<div class="sip-hero-label">Total Required Monthly SIP</div>'
            f'<div class="sip-hero-amount">{format_inr_compact(total_sip)}</div>'
            f'</div>',
            unsafe_allow_html=True,
        )

        if st.button("← Edit Goals", key="back_to_builder"):
            st.session_state.step = 1
            st.rerun()

        tab_afford, tab_protection, tab_breakdown, tab_funds = st.tabs(
            ["  Affordability  ", "  Protection  ", "  Goal Breakdown  ", "  Fund Picks  "]
        )

        with tab_afford:
            inc = st.session_state.income_inputs
            if st.button("← Edit Income Assumptions", key="edit_income"):
                st.session_state.step = 2
                st.rerun()

            projection = project_cashflow(
                inc["salary"], inc["hike"], inc["expenses"], inc["expense_inflation"],
                inc["fixed_obligations"], total_sip, inc["horizon"],
            )
            shortfall_years = [p for p in projection if p.is_shortfall]

            if shortfall_years:
                st.markdown(
                    f'<div class="warn-banner"><i class="bi bi-exclamation-triangle"></i>'
                    f'<span>{len(shortfall_years)} of {inc["horizon"]} years show a shortfall — disposable income doesn\'t cover the total required SIP. '
                    f'Consider trimming "Dream goal" or "Good-to-have" goals first.</span></div>',
                    unsafe_allow_html=True,
                )
            else:
                st.markdown(
                    '<div class="ok-banner"><i class="bi bi-check-circle"></i>'
                    '<span>Disposable income covers the total required SIP in every projected year.</span></div>',
                    unsafe_allow_html=True,
                )

            proj_df = pd.DataFrame([{
                "Year": p.year_index, "Disposable Income": p.disposable_income,
                "Required SIP": p.total_sip_outflow, "Surplus/Deficit": p.surplus_or_deficit,
            } for p in projection])
            fig2 = go.Figure()
            fig2.add_trace(go.Bar(
                x=proj_df["Year"], y=proj_df["Surplus/Deficit"],
                marker_color=["#EF4444" if v < 0 else "#10B981" for v in proj_df["Surplus/Deficit"]],
                customdata=[format_inr_compact(v) for v in proj_df["Surplus/Deficit"]],
                hovertemplate="Year %{x}: %{customdata}<extra></extra>",
                name="Surplus / Deficit",
            ))
            apply_inr_yaxis(fig2, list(proj_df["Surplus/Deficit"]) + [0])
            fig2.update_layout(**PLOTLY_BASE, height=300, margin=dict(t=20, b=20, l=10, r=10))
            st.plotly_chart(fig2, use_container_width=True, key="affordability_chart")

            st.markdown("<br>", unsafe_allow_html=True)
            staggered_plan = build_staggered_plan(results, inc)
            note = build_advisory_note(staggered_plan, inc)

            risk_html = "".join(
                f'<div class="advisor-risk"><i class="bi bi-flag"></i><span>{r}</span></div>'
                for r in note["risk_notes"]
            )
            paras_html = "".join(f'<div class="advisor-para">{p}</div>' for p in note["paragraphs"])
            st.markdown(
                f'<div class="advisor-note">'
                f'<div class="advisor-label"><i class="bi bi-person-badge"></i> Advisor\'s Note</div>'
                f'<div class="advisor-headline">{note["headline"]}</div>'
                f'{paras_html}{risk_html}'
                f'</div>',
                unsafe_allow_html=True,
            )

            st.markdown("#### Funding Order — Detail")
            all_start_now = all(p.start_year == 0 for p in staggered_plan)

            if all_start_now:
                st.markdown(
                    '<div class="ok-banner"><i class="bi bi-check-circle"></i>'
                    '<span>Your income covers every goal\'s SIP starting today — no sequencing needed.</span></div>',
                    unsafe_allow_html=True,
                )
            else:
                st.caption(
                    "When income can't fund every goal at once, this funds them strictly in priority "
                    "order — a later goal only starts once an earlier one is fully covered, with its SIP "
                    "recomputed for the time it has left."
                )
                for p in staggered_plan:
                    color, bg, border = PRIORITY_STYLES.get(p.priority, PRIORITY_STYLES["Dream goal"])
                    badge = (
                        f'<span class="priority-badge" style="color:{color};background:{bg};'
                        f'border:1px solid {border}">{p.priority}</span>'
                    )
                    if p.at_risk:
                        st.markdown(
                            f'<div class="warn-banner"><i class="bi bi-exclamation-triangle"></i>'
                            f'<span><strong>{p.name}</strong> {badge} — won\'t be fundable within your projection '
                            f'horizon at this income. Consider raising income, deprioritizing other goals, or '
                            f'accepting a smaller/later target.</span></div>',
                            unsafe_allow_html=True,
                        )
                    elif p.start_year == 0:
                        st.markdown(
                            f'<div class="ok-banner"><i class="bi bi-check-circle"></i>'
                            f'<span><strong>{p.name}</strong> {badge} — start now at '
                            f'{format_inr_compact(p.monthly_sip_at_start)}/month.</span></div>',
                            unsafe_allow_html=True,
                        )
                    else:
                        st.markdown(
                            f'<div class="caution-banner"><i class="bi bi-clock-history"></i>'
                            f'<span><strong>{p.name}</strong> {badge} — start in Year {p.start_year} at '
                            f'{format_inr_compact(p.monthly_sip_at_start)}/month ({p.years_remaining_at_start:.0f} yrs left at that point; '
                            f'original full-horizon SIP was {format_inr_compact(p.original_monthly_sip)}/month).</span></div>',
                            unsafe_allow_html=True,
                        )

        with tab_protection:
            prot = st.session_state.protection_inputs
            if st.button("← Edit Protection Details", key="edit_protection"):
                st.session_state.step = 3
                st.rerun()

            st.caption(
                "Checked against your goals, loans, and income — not generic rules of thumb. "
                "Methodology: need-based life cover (debt + goal commitments + income replacement), "
                "Indian city-tier health insurance benchmarks, and bank-style FOIR for debt load."
            )

            monthly_income = inc["salary"] / 12
            total_monthly_emi = sum(loan["emi"] for loan in st.session_state.loans)

            life = recommended_life_cover(
                results, st.session_state.loans, inc["expenses"], prot.get("dependents", 0), prot.get("current_life_cover", 0),
            )
            health = recommended_health_cover(prot.get("dependents", 0), prot.get("city_tier", "Metro / Tier-1"), prot.get("current_health_cover", 0))
            ef = recommended_emergency_fund(inc["expenses"] / 12, prot.get("dependents", 0), inc.get("emergency_savings", 0))
            foir = compute_foir(total_monthly_emi, monthly_income)

            st.markdown("##### Life Insurance")
            l1, l2, l3 = st.columns(3)
            l1.markdown(f'<div class="metric-card"><div class="mc-num">{format_inr_compact(life.current_cover)}</div><div class="mc-label">Current Cover</div></div>', unsafe_allow_html=True)
            l2.markdown(f'<div class="metric-card"><div class="mc-num">{format_inr_compact(life.total_need)}</div><div class="mc-label">Recommended Cover</div></div>', unsafe_allow_html=True)
            l3.markdown(f'<div class="metric-card"><div class="mc-num">{format_inr_compact(life.gap)}</div><div class="mc-label">Gap</div></div>', unsafe_allow_html=True)
            st.caption(
                f"Recommended cover = outstanding loans ({format_inr_compact(life.debt_component)}) + lump-sum "
                f"equivalent of your goals ({format_inr_compact(life.goals_component)}) + {life.replacement_years} years "
                f"of income replacement for {prot.get('dependents', 0)} dependent(s) ({format_inr_compact(life.income_replacement_component)})."
            )
            if life.gap > 0:
                st.markdown(
                    f'<div class="warn-banner"><i class="bi bi-exclamation-triangle"></i>'
                    f'<span>Shortfall of {format_inr_compact(life.gap)} — if something happened to you today, your '
                    f'family would not have enough to clear debts, fund your goals, and replace your income for the '
                    f'years estimated above. Consider a term insurance top-up; term plans are the cheapest way to '
                    f'close this kind of gap.</span></div>',
                    unsafe_allow_html=True,
                )
            else:
                st.markdown(
                    '<div class="ok-banner"><i class="bi bi-check-circle"></i>'
                    '<span>Your current life cover meets the estimated need.</span></div>',
                    unsafe_allow_html=True,
                )

            st.markdown("##### Health Insurance")
            h1, h2, h3 = st.columns(3)
            h1.markdown(f'<div class="metric-card"><div class="mc-num">{format_inr_compact(health.current_cover)}</div><div class="mc-label">Current Cover</div></div>', unsafe_allow_html=True)
            h2.markdown(f'<div class="metric-card"><div class="mc-num">{format_inr_compact(health.recommended)}</div><div class="mc-label">Recommended Cover</div></div>', unsafe_allow_html=True)
            h3.markdown(f'<div class="metric-card"><div class="mc-num">{format_inr_compact(health.gap)}</div><div class="mc-label">Gap</div></div>', unsafe_allow_html=True)
            st.caption(f"Based on {prot.get('city_tier', 'Metro / Tier-1')} benchmarks for a family of {1 + prot.get('dependents', 0)}.")
            if health.gap > 0:
                st.markdown(
                    f'<div class="warn-banner"><i class="bi bi-exclamation-triangle"></i>'
                    f'<span>Shortfall of {format_inr_compact(health.gap)} — a single major hospitalization at this '
                    f'cover level could force you to liquidate investments meant for your goals. Consider a top-up or '
                    f'super top-up plan, which is usually cheaper than raising your base cover.</span></div>',
                    unsafe_allow_html=True,
                )
            else:
                st.markdown(
                    '<div class="ok-banner"><i class="bi bi-check-circle"></i>'
                    '<span>Your current health cover meets the benchmark for your family size and city tier.</span></div>',
                    unsafe_allow_html=True,
                )

            st.markdown("##### Emergency Fund")
            e1, e2, e3 = st.columns(3)
            e1.markdown(f'<div class="metric-card"><div class="mc-num">{format_inr_compact(ef.current_savings)}</div><div class="mc-label">Current Savings</div></div>', unsafe_allow_html=True)
            e2.markdown(f'<div class="metric-card"><div class="mc-num">{format_inr_compact(ef.recommended)}</div><div class="mc-label">Recommended ({ef.recommended_months} mo.)</div></div>', unsafe_allow_html=True)
            e3.markdown(f'<div class="metric-card"><div class="mc-num">{format_inr_compact(ef.gap)}</div><div class="mc-label">Gap</div></div>', unsafe_allow_html=True)
            if ef.gap > 0:
                st.markdown(
                    f'<div class="caution-banner"><i class="bi bi-info-circle"></i>'
                    f'<span>Build this up before increasing SIPs further — it\'s what keeps a job loss or medical '
                    f'emergency from forcing you to break your goal investments.</span></div>',
                    unsafe_allow_html=True,
                )
            else:
                st.markdown(
                    '<div class="ok-banner"><i class="bi bi-check-circle"></i>'
                    '<span>Your emergency fund meets the recommended target.</span></div>',
                    unsafe_allow_html=True,
                )

            st.markdown("##### Debt Load (FOIR)")
            foir_color = {"Safe": "ok-banner", "Caution": "caution-banner", "High": "warn-banner"}[foir.level]
            foir_icon = {"Safe": "bi-check-circle", "Caution": "bi-info-circle", "High": "bi-exclamation-triangle"}[foir.level]
            st.markdown(
                f'<div class="{foir_color}"><i class="bi {foir_icon}"></i>'
                f'<span><strong>{foir.level}</strong> — your EMIs are {foir.ratio*100:.0f}% of monthly income '
                f'({format_inr_compact(foir.total_monthly_emi)} of {format_inr_compact(foir.monthly_income)}). '
                f'Indian banks treat 40% or below as safe and rarely lend past 55%.</span></div>',
                unsafe_allow_html=True,
            )

        with tab_breakdown:
            for goal_idx, g in enumerate(results):
                r = g["result"]
                color, bg, border = PRIORITY_STYLES.get(g.get("priority", "Dream goal"), PRIORITY_STYLES["Dream goal"])
                badge = (
                    f'<span class="priority-badge" style="color:{color};background:{bg};'
                    f'border:1px solid {border}">{g.get("priority", "Dream goal")}</span>'
                )
                st.markdown(
                    f'<div style="display:flex;align-items:center;gap:0.5rem;margin-bottom:0.5rem">'
                    f'<h4 style="margin:0">{g["name"]}</h4>{badge}'
                    f'<span style="font-size:0.75rem;color:var(--t3)">{g.get("category","Other")}</span></div>',
                    unsafe_allow_html=True,
                )
                m1, m2, m3, m4 = st.columns(4)
                m1.markdown(f'<div class="metric-card"><div class="mc-num">{format_inr_compact(r.future_value_required)}</div><div class="mc-label">Target (Future Value)</div></div>', unsafe_allow_html=True)
                m2.markdown(f'<div class="metric-card"><div class="mc-num">{format_inr_compact(r.monthly_sip)}</div><div class="mc-label">Monthly SIP{" (Year 1)" if g["step_up"] > 0 else ""}</div></div>', unsafe_allow_html=True)
                m3.markdown(f'<div class="metric-card"><div class="mc-num">{format_inr_compact(r.total_invested)}</div><div class="mc-label">Total Invested</div></div>', unsafe_allow_html=True)
                m4.markdown(f'<div class="metric-card"><div class="mc-num">{format_inr_compact(r.wealth_gained)}</div><div class="mc-label">Wealth Gained</div></div>', unsafe_allow_html=True)

                schedule_df = pd.DataFrame(r.schedule)
                fig = go.Figure()
                fig.add_trace(go.Bar(
                    x=schedule_df["year"], y=schedule_df["contribution"], name="Contribution", marker_color="#818CF8",
                    customdata=[format_inr_compact(v) for v in schedule_df["contribution"]],
                    hovertemplate="Year %{x} contribution: %{customdata}<extra></extra>",
                ))
                fig.add_trace(go.Scatter(
                    x=schedule_df["year"], y=schedule_df["balance"], name="Balance", line=dict(color="#10B981", width=2),
                    customdata=[format_inr_compact(v) for v in schedule_df["balance"]],
                    hovertemplate="Year %{x} balance: %{customdata}<extra></extra>",
                ))
                apply_inr_yaxis(fig, list(schedule_df["balance"]) + [0])
                fig.update_layout(**PLOTLY_BASE, height=260, margin=dict(t=20, b=20, l=10, r=10),
                                   legend=dict(orientation="h", yanchor="bottom", y=1.02, x=1, xanchor="right"))
                st.plotly_chart(fig, use_container_width=True, key=f"goal_chart_{goal_idx}_{g['name']}")
                st.markdown("---")

            st.caption(
                "Next: set up each SIP with your fund house or broker on the 1st of the month, "
                "check the Affordability tab to confirm it fits your budget, then check Fund Picks "
                "for long-horizon goals."
            )

        with tab_funds:
            st.caption("Equity fund picks from Project 1's scored universe, for goals with a long enough horizon.")
            for g in results:
                rec = recommend_for_goal(g["years"])
                st.markdown(f"#### {g['name']}")
                if not rec["eligible"]:
                    st.markdown(f'<div class="caution-banner"><i class="bi bi-info-circle"></i><span>{rec["message"]}</span></div>', unsafe_allow_html=True)
                elif not rec["funds"]:
                    st.markdown(
                        '<div class="caution-banner"><i class="bi bi-info-circle"></i>'
                        '<span>No fund data available — run Project 1\'s pipeline to populate scored_funds.csv.</span></div>',
                        unsafe_allow_html=True,
                    )
                else:
                    st.caption(rec["message"])
                    for f in rec["funds"]:
                        st.markdown(
                            f'<div class="fund-pick"><span class="fund-rank">#{f.get("category_rank","—")}</span>'
                            f'<span style="flex:1">{f.get("scheme_name","—")}</span>'
                            f'<span style="color:#52525B;font-size:0.72rem">score {f.get("composite_score",0):.2f}</span></div>',
                            unsafe_allow_html=True,
                        )

        st.markdown("<br>", unsafe_allow_html=True)
        pdf_bytes = build_pdf_report(
            results, inc, st.session_state.loans, prot, staggered_plan, note, life, health, ef, foir,
        )
        st.download_button(
            "Download Full Wealth Plan (PDF)",
            data=pdf_bytes,
            file_name="wealth_plan.pdf",
            mime="application/pdf",
            type="primary",
            use_container_width=True,
        )
        st.caption("One report: goals, funding sequence, protection gaps, and your loan schedule — ready to print or share with an advisor.")

        st.markdown(
            '<div class="disclaimer"><strong>Disclaimer:</strong> Educational/portfolio tool, not financial advice. '
            'Return and inflation assumptions are user-editable estimates, not guarantees. Mutual fund investments '
            'are subject to market risk. Consult a SEBI-registered advisor before investing.</div>'
            '<div class="footer">Built by <strong>Veer Pratap Singh</strong> &nbsp;·&nbsp; '
            '<a href="https://github.com/VeerVVAPS-portfolio">GitHub</a> &nbsp;·&nbsp; '
            '<a href="https://linkedin.com/in/veer-pratap-singh-681a5530b">LinkedIn</a></div>',
            unsafe_allow_html=True,
        )


# ── Router ───────────────────────────────────────────────────────────────

step = st.session_state.step
if step == 0:
    render_landing()
elif step == 1:
    render_goal_builder()
elif step == 2:
    render_income_step()
elif step == 3:
    render_protection_step()
else:
    render_results()
