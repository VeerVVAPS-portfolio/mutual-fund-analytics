"""
TrueSIP — dashboard/app.py
Single entry-point wizard driven by st.session_state['step'].

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
SESSION STATE CONTRACT
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Keys written by each step; downstream steps read from these.

  step : int
      Current wizard step (0–3). Also accepts 'explore' and 'advanced'.

  PRIMARY WIZARD FLOW
  ───────────────────
  # Step 0 — DIAGNOSIS (goal-first front door)
  session_state['goals'] : list[dict]
      Each dict: {
          'name':    str   — user-facing goal label (e.g. "Retirement", "Child's Education"),
          'amount':  float — today's cost of the goal in ₹,
          'years':   float — years until the goal date,
      }
      Written by: streamlit-ux-builder (render_step_diagnosis)

  # Step 1 — PROFILE (risk quiz)
  session_state['risk_score'] : int          — 0–100 from shared.risk_profiler.compute_risk_score()
  session_state['risk_label'] : str          — from shared.risk_profiler.get_risk_label()
  session_state['base_allocation'] : dict    — from shared.risk_profiler.get_base_allocation()
      Written by: streamlit-ux-builder (render_step_profile)

  # Step 2 — GOALS & INCOME
  session_state['income'] : dict
      {
          'monthly_income':       float — gross monthly take-home (₹),
          'monthly_expenses':     float — monthly living expenses (₹),
          'fixed_obligations':    float — fixed monthly EMIs/rent (₹),
          'salary_hike_pct':      float — expected annual raise (decimal, e.g. 0.08),
          'expense_inflation_pct':float — lifestyle inflation (decimal, e.g. 0.06),
      }
  session_state['sip_params'] : dict
      {
          'inflation_rate': float — goal inflation assumption (decimal),
          'step_up_pct':   float — annual SIP step-up (0 = flat SIP),
      }
      Written by: streamlit-ux-builder (render_step_goals_income)

  # Step 3 — RESULTS ("Your Plan")
  session_state['plan'] : dict
      Output of shared.planning_engine.build_plan() — set by integration-logic-architect.
      Schema documented in shared/planning_engine.py (filled by that agent).
  session_state['explanation'] : str
      Prose narrative from shared.explainer.explain_plan() — set by llm-reasoning-engineer.
      Falls back to a template string when no Groq key is present.
      Written by: integration-logic-architect + llm-reasoning-engineer pipeline

  ADVANCED / OPTIONAL
  ───────────────────
  session_state['advanced'] : dict | None
      Optional inputs for the "Advanced wealth check" expander:
      {
          'dependents':          int,
          'city_tier':           str  — "Metro / Tier-1" | "Tier-2" | "Tier-3",
          'current_life_cover':  float,
          'current_health_cover':float,
          'current_savings':     float,
          'loans': list[dict]    — each: {'emi', 'rate', 'remaining_months'},
      }
      Written by: streamlit-ux-builder (inside the advanced expander on step 3)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
STEP-FILL CONTRACT FOR DOWNSTREAM AGENTS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Each step body is a placeholder function. The named agent fills it:

  render_step_diagnosis(df)       → streamlit-ux-builder
  render_step_profile()           → streamlit-ux-builder
  render_step_goals_income()      → streamlit-ux-builder
  render_step_results(df)         → streamlit-ux-builder
      (Results calls planning_engine.build_plan from integration-logic-architect
       and explainer.explain_plan from llm-reasoning-engineer)

  render_explore_funds(df)        → streamlit-ux-builder
  render_advanced_check()         → streamlit-ux-builder (expander inside step 3)

  shared.planning_engine          → integration-logic-architect
      build_plan(goals, risk_label, income, sip_params, df) -> dict

  shared.explainer                → llm-reasoning-engineer
      explain_plan(plan) -> str

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
BUILD MANDATES (from council SYNTHESIS.md — every agent must respect these)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  1. ALL monthly SIP figures come from shared.goal_calculator.solve_goal().
     The LLM layer MUST NOT emit any monthly_sip_suggestion number.
  2. Each goal's equity allocation is set by shared.risk_profiler.horizon_equity_band()
     (horizon-authoritative). The person-level risk label is a tilt within that
     band, never an override.
  3. Only the equity rupees of a goal's SIP reach the fund screener. Debt/Gold/Alts
     are shown as named-but-explicitly-unranked categories (SGB / short-duration /
     PPF suggestions). Do NOT silently drop non-equity slices.
"""

from __future__ import annotations

import sys
from pathlib import Path

# ── Path setup (makes shared/ importable without installing as a package) ─────
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

# ── Streamlit imports (MUST precede any st.* call) ────────────────────────────
import streamlit as st

# ── Single st.set_page_config call for the entire app ────────────────────────
st.set_page_config(
    page_title="TrueSIP — Goal-First SIP Planner",
    page_icon="📐",
    layout="centered",
    initial_sidebar_state="collapsed",
    menu_items={
        "Report a bug": None,
        "Get help": None,
        "About": (
            "TrueSIP by Veer Pratap Singh — "
            "goal-first, deterministic SIP planning. "
            "Not SEBI-registered investment advice."
        ),
    },
)

# ── Shared package imports ────────────────────────────────────────────────────
from shared.theme import inject_theme
from shared.data_store import load_scored_funds

# ── Screen bodies (kept in a sibling module so this wizard wiring stays thin) ──
import views

# ── Inject theme (once per render, after set_page_config) ────────────────────
inject_theme()

# ── Initialise session state keys (idempotent) ────────────────────────────────

_STATE_DEFAULTS: dict[str, object] = {
    "step": 0,                # int 0–3, or str 'explore'
    "goals": [],              # list[dict] — from step 0
    "current_sip": 0,         # float — diagnosis "current SIP" (reference)
    "risk_score": None,       # int — from step 1
    "risk_label": None,       # str — from step 1
    "base_allocation": None,  # dict — from step 1
    "income": None,           # dict — from step 2
    "sip_params": None,       # dict — from step 2
    "plan": None,             # dict — from step 3 engine
    "explanation": None,      # str  — from step 3 LLM
    "advanced": None,         # dict | None — advanced check inputs
}

for _key, _default in _STATE_DEFAULTS.items():
    if _key not in st.session_state:
        st.session_state[_key] = _default


# ── Load fund seed data (surface error clearly if missing) ────────────────────
try:
    _funds_df = load_scored_funds()
except RuntimeError as e:
    st.error(
        f"**TrueSIP cannot start: fund data is unavailable.**\n\n{e}\n\n"
        "Please contact the site owner or check back later."
    )
    st.stop()


# ═══════════════════════════════════════════════════════════════════════════════
# STEP RENDER FUNCTIONS
# Each function draws the step bar + title, delegates its body to views.py,
# then renders the Back/Next nav controls. The original per-step docstrings are
# retained below as the session_state contract reference.
# ═══════════════════════════════════════════════════════════════════════════════

def render_step_bar(current_step: int, total_steps: int = 4) -> None:
    """Render a step bar with numbered pill + segment label for each step."""
    labels = ["Goals", "Profile", "Income", "Your Plan"]
    cols = st.columns(total_steps)
    for i, (col, label) in enumerate(zip(cols, labels)):
        if i < current_step:
            state_bar = "done"
            state_num = "done"
            state_lbl = "done"
        elif i == current_step:
            state_bar = "active"
            state_num = "active"
            state_lbl = "active"
        else:
            state_bar = ""
            state_num = ""
            state_lbl = ""
        with col:
            st.markdown(
                f'<div class="truesip-step-label">'
                f'<div class="truesip-step {state_bar}"></div>'
                f'<span class="truesip-step-num {state_num}">{i + 1}</span>'
                f'<span class="truesip-step-seg-label {state_lbl}">{label}</span>'
                f'</div>',
                unsafe_allow_html=True,
            )


def _nav_buttons(
    back_step: int | str | None = None,
    next_step: int | str | None = None,
    next_label: str = "Next →",
    back_label: str = "← Back",
    next_disabled: bool = False,
) -> None:
    """
    Render Back / Next navigation buttons.

    Args:
        back_step:     step value to set when Back is clicked (None = hide Back).
        next_step:     step value to set when Next is clicked (None = hide Next).
        next_label:    Label for the Next button.
        back_label:    Label for the Back button.
        next_disabled: If True, Next button is shown but disabled.
    """
    st.markdown("---")
    col_back, col_spacer, col_next = st.columns([1, 4, 1])

    if back_step is not None:
        with col_back:
            if st.button(back_label, key=f"back_{st.session_state['step']}", type="secondary"):
                st.session_state["step"] = back_step
                st.rerun()

    if next_step is not None:
        with col_next:
            if st.button(
                next_label,
                key=f"next_{st.session_state['step']}",
                type="primary",
                disabled=next_disabled,
                use_container_width=True,
            ):
                st.session_state["step"] = next_step
                st.rerun()


# ── Step 0: DIAGNOSIS ─────────────────────────────────────────────────────────

def render_step_diagnosis(df) -> None:
    """
    PLACEHOLDER — to be filled by: streamlit-ux-builder

    PURPOSE:
      Goal-first front door. The user names and sizes their goals before
      answering any profile questions. This is the council-locked sequence:
      goal → profile → income → plan (not profile-first).

    COLLECTS (must be written to session_state before advancing):
      session_state['goals'] : list[dict]
        Each dict: {'name': str, 'amount': float, 'years': float}
        Minimum 1 goal required before Next is enabled.

    UI NOTES:
      - "What are you saving for?" framing — not "what is your risk profile".
      - Let user add multiple goals (e.g. + Add another goal button).
      - Show preset goal chips: Retirement / Child's Education / Home Down Payment /
        Emergency Fund Top-up / Custom.
      - Validate: amount > 0, years > 0, at least 1 goal.

    COMPLIANCE NOTE:
      This screen collects goal names and sizes only. No fund names, no SIP
      amounts, no asset allocation on this screen.
    """
    render_step_bar(0)
    st.title("Is your SIP actually on track?")
    st.caption("Start with one goal — we'll show you instantly whether your current SIP gets you there.")

    has_goal = views.view_diagnosis(df)

    _nav_buttons(
        back_step=None,
        next_step=1,
        next_label="Build my full plan →",
        next_disabled=not has_goal,
    )


# ── Step 1: PROFILE ───────────────────────────────────────────────────────────

def render_step_profile() -> None:
    """
    PLACEHOLDER — to be filled by: streamlit-ux-builder

    PURPOSE:
      5-question risk quiz. Maps to shared.risk_profiler.compute_risk_score()
      and get_risk_label(). Shows a risk gauge on completion.

    COLLECTS (must be written to session_state before advancing):
      session_state['risk_score']    : int   (0–100)
      session_state['risk_label']    : str   (e.g. "Moderate Aggressive")
      session_state['base_allocation']: dict  (equity/debt/gold/alternatives %)

    UI NOTES:
      - Use shared.risk_profiler.QUESTIONS dict for question text + options.
      - Show a gauge/indicator after scoring (score_to_gauge_color() for color).
      - Display the base allocation as a donut or bar — NOT as a fund recommendation.
        These are the whole-person context numbers; per-goal equity is set separately
        by horizon_equity_band() in the planning engine.

    COMPLIANCE NOTE:
      Do NOT show any fund names or specific asset allocation percentages as
      "what you should invest in" — label this clearly as a risk profiling
      output, not advice.
    """
    render_step_bar(1)
    st.title("Your Risk Profile")
    st.caption("A few quick questions to understand how you handle risk.")

    views.view_profile()

    _nav_buttons(back_step=0, next_step=2, next_label="Next: Goals & Income →")


# ── Step 2: GOALS & INCOME ────────────────────────────────────────────────────

def render_step_goals_income() -> None:
    """
    PLACEHOLDER — to be filled by: streamlit-ux-builder

    PURPOSE:
      Collect income/expense data and SIP parameters (inflation assumption,
      step-up rate). Goals were already named in step 0; this step lets the
      user refine them and add inflation + return assumptions.

    COLLECTS (must be written to session_state before advancing):
      session_state['income'] : dict
        {
          'monthly_income':        float,   # gross take-home (₹/month)
          'monthly_expenses':      float,   # living expenses (₹/month)
          'fixed_obligations':     float,   # EMIs / rent (₹/month)
          'salary_hike_pct':       float,   # e.g. 0.08 for 8%
          'expense_inflation_pct': float,   # e.g. 0.06
        }
      session_state['sip_params'] : dict
        {
          'inflation_rate': float,   # goal inflation (e.g. 0.06)
          'step_up_pct':   float,    # SIP annual step-up (0 = flat)
        }

    UI NOTES:
      - Show goal list from session_state['goals'] in a compact read-only
        summary so the user knows what they're funding.
      - Use sliders + number inputs; avoid free-text for numeric fields.
      - Sensible defaults: salary_hike 8%, expense_inflation 6%, goal_inflation 6%.
      - Validate: income > expenses + fixed_obligations (else warn before Next).
    """
    render_step_bar(2)
    st.title("Your Goals & Income")
    st.caption("Fine-tune your goals and add income — we'll check the SIPs are affordable year-by-year.")

    ready = views.view_goals_income()

    _nav_buttons(back_step=1, next_step=3, next_label="See My Plan →", next_disabled=not ready)


# ── Step 3: RESULTS ───────────────────────────────────────────────────────────

def render_step_results(df) -> None:
    """
    PLACEHOLDER — to be filled by: streamlit-ux-builder
    (planning_engine filled by: integration-logic-architect)
    (explainer filled by: llm-reasoning-engineer)

    PURPOSE:
      Show the complete plan: per-goal SIPs, asset split, equity fund picks
      (equity slice only), and LLM prose narrative. Also hosts the
      "Advanced wealth check" expander.

    READS from session_state:
      goals, risk_label, income, sip_params  (set by steps 0–2)

    WRITES to session_state (via planning_engine + explainer):
      session_state['plan']        : dict  — from shared.planning_engine.build_plan()
      session_state['explanation'] : str   — from shared.explainer.explain_plan()

    PLAN DICT SCHEMA (set by integration-logic-architect in shared/planning_engine.py):
      {
        'goals': list[dict],     # one per goal; each has GoalResult + equity_pct + asset_split
        'total_monthly_sip': float,
        'affordability_ok':  bool,
        'cashflow_rows':     list[ProjectionYear],   # from cashflow_projection
      }

    DISPLAY RULES (council mandates):
      - Only the equity rupees of each goal's SIP reach the fund screener.
      - Debt/Gold/Alts: show category name + example instrument (SGB, PPF, etc.)
        but NO composite_score ranking for non-equity.
      - The LLM explanation is labeled "Why this plan?" and framed as methodology
        context, not personalized advice.
      - SEBI disclaimer must appear before any fund names.

    ADVANCED WEALTH CHECK (expander, optional):
      - Uses shared.cashflow_projection.project_cashflow() for affordability chart.
      - Uses shared.protection functions for insurance/emergency-fund gaps.
      - Filled by streamlit-ux-builder.
    """
    render_step_bar(3)
    st.title("Your Plan")
    st.caption("Deterministic SIPs, sized from your goals — not guessed.")

    # Renders headline totals, affordability verdict, the SEBI disclaimer (before
    # any fund/category mention), per-goal cards, the "Why this plan?" prose, the
    # next-step guidance, and the Advanced wealth-check expander.
    views.view_results(df)

    _nav_buttons(back_step=2, next_step=None, back_label="← Revise Goals")

    # Explore Funds shortcut
    st.markdown("---")
    col1, col2 = st.columns(2)
    with col1:
        if st.button("Explore all funds →", type="secondary"):
            st.session_state["step"] = "explore"
            st.rerun()
    with col2:
        if st.button("Start over", type="secondary"):
            for key in _STATE_DEFAULTS:
                st.session_state[key] = _STATE_DEFAULTS[key]
            st.rerun()


# ── Explore Funds view ────────────────────────────────────────────────────────

def render_explore_funds(df) -> None:
    """
    PLACEHOLDER — to be filled by: streamlit-ux-builder

    PURPOSE:
      Standalone fund screener — the standalone Project 1 equivalent inside
      TrueSIP. Accessible from the Results screen and from a top-level link.
      Decoupled from the personal plan: no user-specific data shown here.

    COMPLIANCE NOTE (council mandate #3 + compliance guardrail):
      This is the only screen that names and ranks specific funds.
      It is framed as a methodology screener, not as personalized advice.
      Users reach it via an opt-in click, not as part of the wizard flow.
      SEBI disclaimer must be shown before the fund table.

    READS from:
      df : pd.DataFrame — the full scored_funds DataFrame from load_scored_funds().
      shared.data_store.get_top_funds(category, n, df) for category filtering.
      shared.data_store.CATEGORIES for the category selector.

    UI NOTES:
      - Category dropdown → composite-score weight sliders → ranked table.
      - Show Sharpe, Alpha, Consistency, AUM, returns for each fund.
      - "Why these metrics?" expander pointing to the Project 1 methodology.
    """
    st.title("Explore Funds")
    st.caption("A general, neutral screener — ranked equity funds, category by category.")

    views.view_explore(df)

    st.markdown("---")
    # Back target: return to the plan if one exists, else the start.
    back_target = 3 if st.session_state.get("plan") else 0
    back_label = "← Back to My Plan" if back_target == 3 else "← Back to start"
    if st.button(back_label, type="secondary"):
        st.session_state["step"] = back_target
        st.rerun()


# ═══════════════════════════════════════════════════════════════════════════════
# MAIN RENDER ROUTER
# Routes session_state['step'] to the correct render function.
# ═══════════════════════════════════════════════════════════════════════════════

def main() -> None:
    step = st.session_state["step"]

    if step == "explore":
        render_explore_funds(_funds_df)
    elif step == 0:
        render_step_diagnosis(_funds_df)
    elif step == 1:
        render_step_profile()
    elif step == 2:
        render_step_goals_income()
    elif step == 3:
        render_step_results(_funds_df)
    else:
        st.error(f"Unknown step: {step!r}. Resetting to start.")
        st.session_state["step"] = 0
        st.rerun()


if __name__ == "__main__":
    main()
