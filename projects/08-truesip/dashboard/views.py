"""
dashboard/views.py — TrueSIP screen bodies (kept out of app.py so the wizard
wiring in app.py stays thin and a partial write can't corrupt navigation).

Each `view_*` function renders ONE screen's body. app.py's render_step_*
placeholders call into these after drawing the step bar; nav buttons stay in
app.py via _nav_buttons(...).

Charts use Plotly (dark theme, transparent background, indigo accent).
COMPLIANCE: no view here pairs a NAMED fund with a personalized amount. Only
view_explore() names/ranks funds, on a neutral, opt-in, category-filtered
surface that never reads the user's profile/goals.
"""

from __future__ import annotations

import streamlit as st

# Shared engine + content modules (project root is on sys.path via app.py).
from shared.risk_profiler import (
    QUESTIONS,
    compute_risk_score,
    get_risk_label,
    get_base_allocation,
    score_to_gauge_color,
)
from shared.planning_engine import (
    reconcile_allocation,
    blended_expected_return,
    build_plan,
    MID_CAP,
    SMALL_CAP,
)
from shared import goal_calculator
from shared.explainer import explain_plan
from shared.data_store import get_top_funds, CATEGORIES
from shared import scoring
from shared import protection
from shared.cashflow_projection import project_cashflow


# ── shared formatting + chart helpers ────────────────────────────────────────

# Brand palette (mirrors shared/theme.py tokens for Plotly traces).
_ACCENT = "#818CF8"
_TEXT = "#F1F5F9"
_MUTED = "#94A3B8"
_SUCCESS = "#10B981"
_WARNING = "#F59E0B"
_DANGER = "#EF4444"
_ASSET_COLORS = {"equity": "#818CF8", "debt": "#38BDF8", "gold": "#FBBF24",
                 "alternatives": "#A78BFA"}

_DISCLAIMER = (
    "**Educational tool — not investment advice.** TrueSIP is not a "
    "SEBI-registered investment adviser. Figures use documented planning "
    "assumptions (not forecasts). Consult a SEBI-registered adviser before "
    "investing."
)


def _rupees(x: float) -> str:
    """Format a number as ₹ with Indian-style grouping (lakh/crore commas)."""
    try:
        x = float(x)
    except (TypeError, ValueError):
        return "₹0"
    neg = x < 0
    n = int(round(abs(x)))
    s = str(n)
    if len(s) > 3:
        last3 = s[-3:]
        rest = s[:-3]
        # Group the remaining digits in pairs (Indian numbering).
        parts = []
        while len(rest) > 2:
            parts.insert(0, rest[-2:])
            rest = rest[:-2]
        if rest:
            parts.insert(0, rest)
        s = ",".join(parts) + "," + last3
    return ("-₹" if neg else "₹") + s


def _lakh_cr(x: float) -> str:
    """Compact ₹ label for chart axes / headlines (₹1.2 Cr, ₹45.0 L)."""
    x = float(x)
    if abs(x) >= 1_00_00_000:
        return f"₹{x / 1_00_00_000:.2f} Cr"
    if abs(x) >= 1_00_000:
        return f"₹{x / 1_00_000:.1f} L"
    return _rupees(x)


def _base_layout(fig, height: int = 300):
    """Apply the dark transparent theme to a Plotly figure."""
    fig.update_layout(
        height=height,
        margin=dict(l=10, r=10, t=30, b=10),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Inter, sans-serif", color=_TEXT, size=13),
        legend=dict(font=dict(color=_MUTED)),
    )
    return fig


def _disclaimer():
    """Render the standard educational/SEBI disclaimer callout."""
    st.caption(_DISCLAIMER)


# ══════════════════════════════════════════════════════════════════════════════
# STEP 0 — DIAGNOSIS (the under-funding front door / hook)
# ══════════════════════════════════════════════════════════════════════════════

# Preset goal chips → a sensible default target + horizon so first-timers can
# move fast. "Custom" leaves the fields blank for free entry.
_GOAL_PRESETS = {
    "Retirement":         {"amount": 1_00_00_000, "years": 25},
    "Child's Education":  {"amount": 30_00_000,   "years": 15},
    "Home Down Payment":  {"amount": 20_00_000,   "years": 7},
    "Custom":             {"amount": 10_00_000,   "years": 10},
}


def _required_sip_preliminary(amount: float, years: float) -> tuple[float, float, dict]:
    """
    DETERMINISTIC preliminary required SIP for the diagnosis screen.

    Uses a horizon-appropriate MODERATE-AGGRESSIVE default mix (no quiz answered
    yet), blends its expected return, then solves the SIP via the same
    goal_calculator the full plan uses. Returns (required_sip, blended_return,
    asset_split). This is the SAME engine path the final plan uses — only the
    risk label is a stand-in until step 1 refines it.
    """
    alloc = reconcile_allocation(years, "Moderate Aggressive")
    asset_split = {k: alloc[k] for k in ("equity", "debt", "gold")}
    blended = blended_expected_return(asset_split)
    result = goal_calculator.solve_goal(
        present_value=amount,
        inflation_rate=0.06,   # typical goal inflation; full plan lets user change it
        years=years,
        annual_return=blended,
    )
    return result.monthly_sip, blended, asset_split


def view_diagnosis(df) -> bool:
    """
    Goal-first front door. Collects ONE goal (target + horizon + the user's
    CURRENT monthly SIP for it), then reveals the shortfall vs the
    deterministically-solved required SIP.

    Writes session_state['goals'] (list with this one goal) and
    session_state['current_sip'] (for reference on later screens).

    Returns True when a valid goal has been entered (gates the Next button).
    COMPLIANCE: personalized SIP + amount only — no named fund on this screen.
    """
    st.caption(
        "A plan that *looks* complete can quietly under-fund a goal — "
        "this catches it before it costs you."
    )

    # Seed an editable goal so the screen is never blank.
    existing = st.session_state["goals"][0] if st.session_state.get("goals") else None

    preset = st.radio(
        "What are you saving for?",
        list(_GOAL_PRESETS.keys()),
        horizontal=True,
        index=0,
        help="Pick the closest match — you can fine-tune the numbers below.",
    )
    defaults = _GOAL_PRESETS[preset]

    # Custom goal gets a free-text name; presets use the chip label.
    if preset == "Custom":
        goal_name = st.text_input(
            "Name this goal",
            value=(existing["name"] if existing and existing.get("name") not in _GOAL_PRESETS else "My goal"),
        )
    else:
        goal_name = preset

    c1, c2 = st.columns(2)
    with c1:
        amount = st.number_input(
            "Target amount (in today's ₹)",
            min_value=10_000,
            max_value=100_00_00_000,
            value=int(existing["amount"]) if existing else int(defaults["amount"]),
            step=50_000,
            help="What this goal would cost TODAY. We inflate it to the goal date for you.",
        )
    with c2:
        years = st.number_input(
            "Years until you need it",
            min_value=1,
            max_value=50,
            value=int(existing["years"]) if existing else int(defaults["years"]),
            step=1,
        )

    current_sip = st.number_input(
        "Your CURRENT monthly SIP for this goal (₹)",
        min_value=0,
        max_value=10_00_000,
        value=int(st.session_state.get("current_sip", 0)),
        step=1_000,
        help="Enter ₹0 if you haven't started yet — we'll show what it would take.",
    )

    valid = amount > 0 and years > 0 and bool(str(goal_name).strip())

    # Persist immediately so Next (in app.py) advances with fresh data.
    if valid:
        st.session_state["goals"] = [
            {"name": str(goal_name).strip(), "amount": float(amount), "years": float(years)}
        ]
        st.session_state["current_sip"] = float(current_sip)

    # ── Diagnosis gate: suppress verdict on first paint ───────────────────────
    # Reset the reveal flag when the user switches presets (defaults change).
    if st.session_state.get("_last_preset") != preset:
        st.session_state["diagnosis_revealed"] = False
        st.session_state["_last_preset"] = preset

    st.markdown("---")

    if valid:
        if not st.session_state.get("diagnosis_revealed"):
            st.info(
                "Enter your current SIP (₹0 is fine) and hit **Check my SIP** — "
                "we'll show whether you're on track."
            )
            if st.button("Check my SIP →", key="diag_check", type="primary"):
                st.session_state["diagnosis_revealed"] = True
                st.rerun()
        else:
            required, blended, asset_split = _required_sip_preliminary(float(amount), float(years))
            _render_shortfall_reveal(goal_name, float(current_sip), required, blended, asset_split, float(years))

    _disclaimer()
    return valid


def _render_shortfall_reveal(goal_name, current_sip, required, blended, asset_split, years):
    """The hook payoff: current SIP vs required SIP, framed honestly as preliminary."""
    gap = required - current_sip
    on_track = current_sip >= required * 0.98  # within 2% counts as on track

    st.markdown("#### Your preliminary check")

    m1, m2, m3 = st.columns(3)
    with m1:
        st.metric("Saving now (/mo)", _rupees(current_sip))
    with m2:
        st.metric("Goal needs (/mo)", _rupees(required))
    with m3:
        if on_track:
            st.metric(
                "Status", "On track",
                delta="✓ On track",  # text-only delta; SVG suppressed by CSS
            )
        else:
            pct_short = (gap / required * 100) if required > 0 else 0
            st.metric("Shortfall (/mo)", _rupees(gap), delta=f"-{pct_short:.0f}%")

    if on_track:
        st.success(
            f"**Good news — at {_rupees(current_sip)}/month you're on track for "
            f"\"{goal_name}\".** Build the full plan to split this across the right "
            "assets and pressure-test it against your income."
        )
    else:
        pct_short = (gap / required * 100) if required > 0 else 0
        st.warning(
            f"**You're about {pct_short:.0f}% short on \"{goal_name}\".** "
            f"At {_rupees(current_sip)}/month you'd reach the finish line under-funded; "
            f"this goal needs roughly **{_rupees(required)}/month** to get there."
        )

    st.caption(
        f"Preliminary estimate only — assumes ~{blended * 100:.1f}% blended annual return "
        f"from a horizon-appropriate mix (equity {asset_split['equity']:.0f}% / "
        f"debt {asset_split['debt']:.0f}% / gold {asset_split['gold']:.0f}%) and 6% goal "
        "inflation. Your full plan refines this after the risk profile and income check."
    )


# ══════════════════════════════════════════════════════════════════════════════
# STEP 1 — PROFILE (5-question risk quiz)
# ══════════════════════════════════════════════════════════════════════════════

def view_profile() -> bool:
    """
    Render the risk quiz (exactly len(QUESTIONS) questions), score it, and show
    a risk gauge + base-allocation donut clearly labeled as a risk-profile
    output (NOT a fund recommendation).

    Writes risk_score, risk_label, base_allocation to session_state.
    Returns True (the quiz always has a valid default-selected answer set).
    """
    n_q = len(QUESTIONS)
    st.caption(f"{n_q} quick questions to gauge how you handle risk. There are no wrong answers.")

    answers: dict[str, str] = {}
    prev = st.session_state.get("_quiz_answers", {})

    for key, q in QUESTIONS.items():
        options = q["options"]
        default_idx = options.index(prev[key]) if prev.get(key) in options else 0
        answers[key] = st.radio(
            q["label"],
            options,
            index=default_idx,
            help=q.get("help"),
            key=f"quiz_{key}",
        )

    # Score live (the quiz is deterministic — no submit needed).
    score = compute_risk_score(
        age=answers["age"],
        horizon=answers["horizon"],
        goal=answers["goal"],
        reaction=answers["reaction"],
        debt=answers["debt"],
    )
    label = get_risk_label(score)
    base_alloc = get_base_allocation(label)

    st.session_state["_quiz_answers"] = answers
    st.session_state["risk_score"] = score
    st.session_state["risk_label"] = label
    st.session_state["base_allocation"] = base_alloc

    st.markdown("---")
    st.markdown("#### Your risk profile")

    g_col, d_col = st.columns([1, 1])
    with g_col:
        st.plotly_chart(_risk_gauge(score, label), use_container_width=True,
                        config={"displayModeBar": False})
    with d_col:
        st.plotly_chart(_allocation_donut(base_alloc, title="Whole-person base mix"),
                        use_container_width=True, config={"displayModeBar": False})

    st.info(
        f"**This is a risk-profiling output, not a fund recommendation.** "
        f"Your profile is **{label}** ({score}/100). The donut is a whole-person "
        "context mix — your actual per-goal allocation is set by each goal's time "
        "horizon on the next screens, with this profile acting only as a tilt."
    )
    _disclaimer()
    return True


def _risk_gauge(score: int, label: str):
    """Plotly gauge indicator coloured by score_to_gauge_color()."""
    import plotly.graph_objects as go

    color = score_to_gauge_color(score)
    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=score,
        number={"font": {"color": _TEXT, "size": 34, "family": "Space Grotesk"},
                "suffix": "/100"},
        title={"text": f"<b>{label}</b>", "font": {"color": _MUTED, "size": 14}},
        gauge={
            "axis": {"range": [0, 100], "tickcolor": _MUTED,
                     "tickfont": {"color": _MUTED, "size": 10}},
            "bar": {"color": color, "thickness": 0.75},
            "bgcolor": "rgba(255,255,255,0.04)",
            "borderwidth": 0,
            "steps": [
                {"range": [0, 30], "color": "rgba(16,185,129,0.12)"},
                {"range": [30, 55], "color": "rgba(245,158,11,0.12)"},
                {"range": [55, 70], "color": "rgba(249,115,22,0.12)"},
                {"range": [70, 100], "color": "rgba(239,68,68,0.12)"},
            ],
        },
    ))
    return _base_layout(fig, height=260)


def _allocation_donut(alloc: dict, title: str = ""):
    """Donut chart of an asset allocation dict (% values)."""
    import plotly.graph_objects as go

    labels, values, colors = [], [], []
    for k in ("equity", "debt", "gold", "alternatives"):
        if k in alloc and alloc[k] > 0:
            labels.append(k.capitalize())
            values.append(alloc[k])
            colors.append(_ASSET_COLORS[k])

    fig = go.Figure(go.Pie(
        labels=labels, values=values, hole=0.6,
        marker=dict(colors=colors, line=dict(color="#0A0A0E", width=2)),
        textinfo="label+percent", textfont=dict(color=_TEXT, size=12),
        sort=False, direction="clockwise",
        hovertemplate="%{label}: %{value:.0f}%<extra></extra>",
    ))
    fig.update_layout(showlegend=False)
    if title:
        fig.update_layout(title=dict(text=title, font=dict(color=_MUTED, size=13), x=0.5))
    return _base_layout(fig, height=260)


# ══════════════════════════════════════════════════════════════════════════════
# STEP 2 — GOALS & INCOME
# ══════════════════════════════════════════════════════════════════════════════

def view_goals_income() -> bool:
    """
    Let the user add/edit goals (the diagnosis goal is already present), then
    enter income / expenses / obligations / hikes and the SIP step-up + goal
    inflation assumptions.

    Writes session_state['goals'] (updated), ['income'], ['sip_params'].
    Validates disposable income vs a rough total-SIP estimate and WARNS (never
    blocks) on shortfall. Returns True when at least one valid goal exists.
    """
    st.caption("Add every goal you're funding, then tell us about your income so we can "
               "check the SIPs are affordable year-by-year.")

    _render_goal_editor()

    goals = st.session_state.get("goals", [])
    if not goals:
        st.warning("Add at least one goal to continue.")
        return False

    st.markdown("---")
    st.markdown("#### Your income")

    income_prev = st.session_state.get("income") or {}
    c1, c2 = st.columns(2)
    with c1:
        monthly_income = st.number_input(
            "Monthly take-home income (₹)", min_value=0, max_value=1_00_00_000,
            value=int(income_prev.get("monthly_income", 1_00_000)), step=5_000,
        )
        monthly_expenses = st.number_input(
            "Monthly living expenses (₹)", min_value=0, max_value=1_00_00_000,
            value=int(income_prev.get("monthly_expenses", 40_000)), step=2_500,
        )
        fixed_obligations = st.number_input(
            "Fixed monthly EMIs / rent (₹)", min_value=0, max_value=1_00_00_000,
            value=int(income_prev.get("fixed_obligations", 0)), step=2_500,
        )
    with c2:
        _salary_hike_disp = st.slider(
            "Expected annual salary hike", 0, 20,
            int(round(float(income_prev.get("salary_hike_pct", 0.08)) * 100)), 1,
            format="%d%%",
        )
        salary_hike_pct = _salary_hike_disp / 100.0
        _expense_inf_disp = st.slider(
            "Lifestyle (expense) inflation", 0, 15,
            int(round(float(income_prev.get("expense_inflation_pct", 0.06)) * 100)), 1,
            format="%d%%",
        )
        expense_inflation_pct = _expense_inf_disp / 100.0

    st.markdown("#### Plan assumptions")
    sip_prev = st.session_state.get("sip_params") or {}
    c3, c4 = st.columns(2)
    with c3:
        _inflation_disp = st.slider(
            "Goal cost inflation", 0, 15,
            int(round(float(sip_prev.get("inflation_rate", 0.06)) * 100)), 1,
            format="%d%%",
            help="How fast your goals' costs rise (e.g. education inflation runs high).",
        )
        inflation_rate = _inflation_disp / 100.0
    with c4:
        _step_up_disp = st.slider(
            "Annual SIP step-up", 0, 20,
            int(round(float(sip_prev.get("step_up_pct", 0.0)) * 100)), 1,
            format="%d%%",
            help="Raise your SIP by this % each year as income grows — lowers the "
                 "starting amount needed. 0% = a flat SIP.",
        )
        step_up_pct = _step_up_disp / 100.0

    st.session_state["income"] = {
        "monthly_income": float(monthly_income),
        "monthly_expenses": float(monthly_expenses),
        "fixed_obligations": float(fixed_obligations),
        "salary_hike_pct": float(salary_hike_pct),
        "expense_inflation_pct": float(expense_inflation_pct),
    }
    st.session_state["sip_params"] = {
        "inflation_rate": float(inflation_rate),
        "step_up_pct": float(step_up_pct),
    }

    _render_affordability_preview(goals, st.session_state["income"], st.session_state["sip_params"])
    _disclaimer()
    return True


_IMPORTANCE_OPTIONS = ["Essential", "Important", "Aspirational"]


def _render_goal_editor() -> None:
    """Compact add/remove/edit list backed by session_state['goals'].
    Each goal row now includes a compact importance selector (default: Important).
    The importance field is written into each goal dict and consumed by the engine.
    """
    st.markdown("#### Your goals")
    # SEBI disclaimer before the goal editor (above any importance UI block).
    st.caption(
        "Educational tool — not investment advice. Not a SEBI-registered adviser."
    )
    goals = st.session_state.get("goals", [])

    remove_idx = None
    for i, g in enumerate(goals):
        # Ensure importance has a default so older goal dicts are safe.
        if "importance" not in g:
            g["importance"] = "Important"

        cols = st.columns([3, 3, 2, 2, 1])
        with cols[0]:
            g["name"] = st.text_input("Goal", value=g["name"], key=f"gname_{i}",
                                      label_visibility="collapsed" if i else "visible")
        with cols[1]:
            g["amount"] = float(st.number_input(
                "Amount (today's ₹)", min_value=10_000, max_value=100_00_00_000,
                value=int(g["amount"]), step=50_000, key=f"gamt_{i}",
                label_visibility="collapsed" if i else "visible"))
        with cols[2]:
            g["years"] = float(st.number_input(
                "Years", min_value=1, max_value=50, value=int(g["years"]), step=1,
                key=f"gyrs_{i}", label_visibility="collapsed" if i else "visible"))
        with cols[3]:
            imp_idx = _IMPORTANCE_OPTIONS.index(g["importance"]) if g.get("importance") in _IMPORTANCE_OPTIONS else 1
            g["importance"] = st.selectbox(
                "Importance",
                _IMPORTANCE_OPTIONS,
                index=imp_idx,
                key=f"gimp_{i}",
                help="Essential = capital protection matters; Aspirational = can take more risk for extra growth.",
                label_visibility="collapsed" if i else "visible",
            )
        with cols[4]:
            st.write("")
            if len(goals) > 1 and st.button("✕", key=f"gdel_{i}", help="Remove this goal"):
                remove_idx = i

    if remove_idx is not None:
        goals.pop(remove_idx)
        st.session_state["goals"] = goals
        st.rerun()

    if st.button("+ Add another goal", type="secondary"):
        goals.append({"name": "New goal", "amount": 10_00_000, "years": 10, "importance": "Important"})
        st.session_state["goals"] = goals
        st.rerun()


def _render_affordability_preview(goals, income, sip_params) -> None:
    """
    Rough total-SIP vs disposable-income check shown inline (a fast preview; the
    full year-by-year projection lives on the Results screen). Warns, never blocks.
    """
    total_required = 0.0
    for g in goals:
        try:
            req, _, _ = _required_sip_preliminary(float(g["amount"]), float(g["years"]))
            total_required += req
        except Exception:
            continue

    disposable = (income["monthly_income"] - income["monthly_expenses"]
                  - income["fixed_obligations"])

    st.markdown("---")
    c1, c2 = st.columns(2)
    with c1:
        st.metric("Monthly disposable income", _rupees(disposable))
    with c2:
        st.metric("Est. total SIP (/mo)", _rupees(total_required))

    if total_required > disposable and disposable >= 0:
        st.warning(
            f"Heads up — the estimated SIP (**{_rupees(total_required)}/mo**) exceeds your "
            f"disposable income (**{_rupees(disposable)}/mo**). You can still continue; the "
            "plan will flag exactly which years fall short so you can stretch timelines or "
            "trim targets. A yearly SIP step-up can also lower the starting amount."
        )
    elif disposable < 0:
        st.error(
            "Your expenses and EMIs already exceed your income. Revisit those numbers — "
            "no SIP is affordable until disposable income is positive."
        )
    else:
        st.success(
            f"Looks affordable so far — the estimated SIP fits inside your "
            f"{_rupees(disposable)}/mo disposable income. The plan confirms this year-by-year."
        )


# ══════════════════════════════════════════════════════════════════════════════
# STEP 3 — RESULTS ("Your Plan")
# ══════════════════════════════════════════════════════════════════════════════

def view_results(df) -> None:
    """
    Build and render the full plan. Calls planning_engine.build_plan() and
    explainer.explain_plan(), then renders per-goal cards, the SEBI disclaimer
    (before any fund mention), the explanation, totals + affordability verdict,
    a clear next-step line, and hosts the Advanced wealth-check expander.

    Reads goals/risk_label/income/sip_params from session_state; writes
    session_state['plan'] and session_state['explanation'].
    """
    goals = st.session_state.get("goals") or []
    if not goals:
        st.warning("No goals yet — go back and add at least one goal to see your plan.")
        return

    risk_label = st.session_state.get("risk_label") or "Moderate Aggressive"
    income = st.session_state.get("income")
    sip_params = st.session_state.get("sip_params")

    # Build the plan (deterministic). Surface any contract break clearly rather
    # than rendering wrong money.
    with st.spinner("Sizing each goal's SIP and reconciling allocations…"):
        try:
            plan = build_plan(goals, risk_label, income, sip_params, df)
        except AssertionError as e:
            st.error(f"**Plan failed an internal consistency check** and was not shown.\n\n`{e}`")
            return
        except Exception as e:  # noqa: BLE001 — last-resort guard so the screen never crashes
            st.error(f"**Could not build the plan.**\n\n`{e}`")
            return
    st.session_state["plan"] = plan

    # ── Headline summary — Total SIP hero card ──
    total = plan["total_monthly_sip"]
    st.markdown(
        f'<div class="truesip-sip-hero">'
        f'<div class="truesip-sip-hero-label">Total Monthly SIP</div>'
        f'<div class="truesip-sip-hero-amount">{_rupees(total)}<span style="font-size:1.2rem;font-weight:400;color:var(--text-muted)">/month</span></div>'
        f'<div class="truesip-sip-hero-sub">'
        f'Across {len(plan["goals"])} goal(s) &nbsp;·&nbsp; '
        f'risk profile <strong>{risk_label}</strong> (tilt within each goal\'s horizon band)'
        f'</div>'
        f'</div>',
        unsafe_allow_html=True,
    )
    st.caption("Fixed planning assumptions: equity 12% · debt 7% · gold 6% expected annual "
               "return. Inflation and SIP step-up are editable on the previous step.")

    if plan["affordability_ok"]:
        st.success("**Affordable.** No projected year falls short of your income over the plan horizon.")
    else:
        st.warning("**Tight fit.** At least one projected year falls short — see the year-by-year "
                   "chart in *Advanced wealth check* below, and consider stretching timelines, "
                   "trimming targets, or adding a SIP step-up.")

    # ── SEBI disclaimer BEFORE any fund/category mention (SACRED — must stay here) ──
    st.markdown(
        '<div class="truesip-disclaimer">'
        '<strong>Educational, not investment advice. Not a SEBI-registered adviser.</strong> '
        'SIP amounts are deterministically solved from your goals using documented '
        'planning assumptions (not forecasts). Fund <em>categories</em> are shown for the '
        'equity slice; specific funds are never recommended for you here — explore '
        'them yourself on the neutral <em>Explore Funds</em> screen.'
        '</div>',
        unsafe_allow_html=True,
    )

    # ── Per-goal cards ──
    st.markdown("---")
    for g in plan["goals"]:
        _render_goal_card(g)

    # ── Why this plan? (LLM / demo prose) — shimmer skeleton during wait ──
    st.markdown("---")
    _expl_placeholder = st.empty()
    _expl_placeholder.markdown(
        '<div class="truesip-skeleton-card">'
        '<div class="truesip-skeleton-line w-80"></div>'
        '<div class="truesip-skeleton-line w-60"></div>'
        '<div class="truesip-skeleton-line w-70"></div>'
        '</div>',
        unsafe_allow_html=True,
    )
    explanation = explain_plan(plan)
    _expl_placeholder.empty()
    st.session_state["explanation"] = explanation
    st.markdown(explanation)
    st.caption("Explanation is generated to describe the *reasoning*; all numbers above "
               "come from the deterministic engine, not the language model.")

    # ── What to do next ──
    st.markdown("---")
    st.markdown("#### What to do next")
    st.markdown(
        "1. **Review the SIP amounts above** with a SEBI-registered adviser or distributor "
        "who can set them up for you.\n"
        "2. For each goal's **equity slice**, open *Explore Funds* (button on each card) to compare "
        "ranked funds in that category — then pick what fits.\n"
        "3. The **debt/gold slices** name the instrument types (SGB, PPF, "
        "short-duration debt) — these are planning pointers, not ranked picks.\n"
        "4. Open **Advanced wealth check** below to confirm insurance, emergency fund and "
        "year-by-year affordability."
    )

    # ── Advanced expander (hosted here) ──
    with st.expander("Advanced wealth check — insurance, emergency fund, FOIR & affordability"):
        view_advanced(plan)


def _render_goal_card(g: dict) -> None:
    """
    One goal: solved SIP + target, a horizon-band allocation donut, the SIP
    split across asset classes in ₹, the equity-category hand-off button, and
    debt/gold named-but-UNRANKED notes.

    COMPLIANCE: this card NEVER names a fund. The equity slice routes to
    Explore Funds by CATEGORY STRING only (Mandate #4).
    """
    name = g["name"]
    with st.container(border=True):
        st.markdown(f"#### {name}")
        st.caption(
            f"Target {_lakh_cr(g['amount'])} today → "
            f"{_lakh_cr(g['future_value_required'])} in {g['years']:.0f} years "
            f"· blended return assumption {g['blended_return'] * 100:.1f}%"
        )

        top = st.columns(3)
        with top[0]:
            st.metric("Monthly SIP", _rupees(g["monthly_sip"]))
        with top[1]:
            st.metric("You invest", _lakh_cr(g["total_invested"]))
        with top[2]:
            st.metric("Growth", _lakh_cr(g["wealth_gained"]))

        left, right = st.columns([1, 1])
        with left:
            band = g["band"]
            st.plotly_chart(
                _allocation_donut(g["asset_split"],
                                  title=f"Allocation (equity band {band['band_low']:.0f}–{band['band_high']:.0f}%)"),
                use_container_width=True, config={"displayModeBar": False})
        with right:
            st.markdown("**Where each ₹ of this SIP goes**")
            split = g["sip_split"]
            st.plotly_chart(_sip_split_bar(split), use_container_width=True,
                            config={"displayModeBar": False})

        # ── Importance context + volatility caveat (PASS 4) ──
        cat = g.get("equity_category")
        importance = g.get("importance", "Important")
        if cat in (MID_CAP, SMALL_CAP):
            cat_label = _clean_category(cat)
            st.markdown(
                f'<div class="truesip-vol-caveat">'
                f'<i class="bi bi-exclamation-triangle"></i> '
                f'This goal ({g["years"]:.0f}-year horizon, {importance}) sits in the '
                f'<strong>{cat_label}</strong> band — higher volatility than large-cap funds. '
                f'Explore those funds below and confirm fit with an adviser.'
                f'</div>',
                unsafe_allow_html=True,
            )
        elif cat:
            cat_label = _clean_category(cat)
            st.caption(
                f"This goal ({g['years']:.0f}-year horizon, {importance}) maps to the "
                f"**{cat_label}** equity band — explore those funds below."
            )

        # ── Equity slice → category hand-off (NEVER a named fund here) ──
        st.markdown("**Equity slice**")
        eq_rupees = g["sip_split"]["equity"]
        if cat and eq_rupees > 0:
            ec1, ec2 = st.columns([3, 2])
            with ec1:
                st.markdown(
                    f"{_rupees(eq_rupees)}/mo → **{_clean_category(cat)}** funds. "
                    "We don't pick a fund *for you*; compare the ranked options yourself."
                )
            with ec2:
                if st.button(f"Explore ranked {_clean_category(cat)} funds →",
                             key=f"explore_{name}", type="secondary"):
                    # Hand off the category to a NEUTRAL, default-weight screener.
                    st.session_state["explore_category"] = cat
                    st.session_state["explore_reset_weights"] = True
                    st.session_state["step"] = "explore"
                    st.rerun()
        else:
            st.caption(
                "This goal is too near-term for a meaningful equity sleeve — it's funded "
                "debt/gold-first for capital protection, so there's nothing to screen."
            )

        # ── Debt / Gold: named but explicitly UNRANKED (Mandate #3) ──
        notes = g.get("non_equity_notes") or []
        if notes:
            st.markdown("**Debt & gold slices** (named, but *not ranked* — these metrics "
                        "are equity-vs-index and don't apply here)")
            for note in notes:
                sleeve = note["sleeve"].capitalize()
                rupees = g["sip_split"].get(note["sleeve"], 0)
                st.markdown(f"- **{sleeve} · {_rupees(rupees)}/mo** → {note['instrument']}  \n"
                            f"  <span class='text-muted'>{note['note']}</span>",
                            unsafe_allow_html=True)


def _clean_category(cat: str) -> str:
    """Trim the 'Equity Scheme - ' prefix for tidy in-card labels."""
    return cat.replace("Equity Scheme - ", "").replace(" Fund", "")


def _sip_split_bar(split: dict):
    """Horizontal stacked bar of the ₹ SIP split across asset classes."""
    import plotly.graph_objects as go

    order = ["equity", "debt", "gold"]
    fig = go.Figure()
    for k in order:
        val = split.get(k, 0)
        if val <= 0:
            continue
        fig.add_trace(go.Bar(
            y=["SIP"], x=[val], orientation="h", name=k.capitalize(),
            marker=dict(color=_ASSET_COLORS[k]),
            hovertemplate=f"{k.capitalize()}: ₹%{{x:,.0f}}/mo<extra></extra>",
        ))
    # Build lakh/crore tick labels for the x-axis (amount axis on a horizontal bar).
    all_sip_vals = [split.get(k, 0) for k in order if split.get(k, 0) > 0]
    total_sip = sum(all_sip_vals)
    if total_sip > 0:
        raw_step = total_sip / 4
        if raw_step >= 1_00_00_000:
            tick_step_s = round(raw_step / 1_00_00_000) * 1_00_00_000
        elif raw_step >= 1_00_000:
            tick_step_s = round(raw_step / 1_00_000) * 1_00_000
        else:
            tick_step_s = round(raw_step / 1_000) * 1_000
        tick_step_s = max(tick_step_s, 1)
        sip_tickvals = [i * tick_step_s for i in range(6)]
        sip_ticktext = [_lakh_cr(v) for v in sip_tickvals]
    else:
        sip_tickvals = None
        sip_ticktext = None

    fig.update_layout(
        barmode="stack", showlegend=True,
        xaxis=dict(
            showgrid=False, zeroline=False,
            tickfont=dict(color=_MUTED, size=10),
            tickvals=sip_tickvals, ticktext=sip_ticktext,
        ),
        yaxis=dict(showticklabels=False),
        legend=dict(orientation="h", yanchor="bottom", y=-0.4, font=dict(color=_MUTED)),
    )
    return _base_layout(fig, height=180)


# ── Advanced wealth check (expander body on the Results screen) ──────────────

def view_advanced(plan: dict) -> None:
    """
    Optional deeper check: life/health cover gaps (DIME + tier benchmarks),
    emergency-fund gap, FOIR, and a year-by-year affordability chart.

    Uses shared.protection + shared.cashflow_projection. Inputs collected here
    are written to session_state['advanced']. Degrades gracefully if income
    wasn't entered.
    """
    income = st.session_state.get("income") or {}
    adv_prev = st.session_state.get("advanced") or {}

    st.caption("Optional — a quick read on whether your safety net keeps pace with the plan.")

    c1, c2 = st.columns(2)
    with c1:
        dependents = st.number_input("Financial dependents", min_value=0, max_value=10,
                                     value=int(adv_prev.get("dependents", 0)), step=1)
        city_tier = st.selectbox(
            "City tier", ["Metro / Tier-1", "Tier-2", "Tier-3"],
            index=["Metro / Tier-1", "Tier-2", "Tier-3"].index(
                adv_prev.get("city_tier", "Metro / Tier-1")),
        )
    with c2:
        current_life_cover = st.number_input(
            "Existing life cover (₹)", min_value=0, max_value=100_00_00_000,
            value=int(adv_prev.get("current_life_cover", 0)), step=5_00_000)
        current_health_cover = st.number_input(
            "Existing health cover (₹)", min_value=0, max_value=10_00_00_000,
            value=int(adv_prev.get("current_health_cover", 0)), step=2_00_000)

    current_savings = st.number_input(
        "Current emergency savings / liquid funds (₹)", min_value=0, max_value=100_00_00_000,
        value=int(adv_prev.get("current_savings", 0)), step=50_000)

    st.markdown("**Existing loans** (for life-cover & FOIR — leave at 0 if none)")
    lc1, lc2, lc3 = st.columns(3)
    with lc1:
        loan_emi = st.number_input("Loan EMI (₹/mo)", min_value=0, max_value=10_00_000,
                                   value=int(adv_prev.get("_loan_emi", 0)), step=2_500)
    with lc2:
        _loan_rate_disp = st.slider(
            "Loan interest", 0.0, 20.0,
            round(float(adv_prev.get("_loan_rate", 0.09)) * 100, 1),
            0.5, format="%.1f%%",
        )
        loan_rate = _loan_rate_disp / 100.0
    with lc3:
        loan_months = st.number_input("Months remaining", min_value=0, max_value=480,
                                      value=int(adv_prev.get("_loan_months", 0)), step=6)

    loans = ([{"emi": float(loan_emi), "rate": float(loan_rate),
               "remaining_months": int(loan_months)}] if loan_emi > 0 and loan_months > 0 else [])

    st.session_state["advanced"] = {
        "dependents": int(dependents),
        "city_tier": city_tier,
        "current_life_cover": float(current_life_cover),
        "current_health_cover": float(current_health_cover),
        "current_savings": float(current_savings),
        "loans": loans,
        # remembered raw widget values for re-entry
        "_loan_emi": float(loan_emi), "_loan_rate": float(loan_rate),
        "_loan_months": int(loan_months),
    }

    if not income:
        st.info("Enter your income on the previous step to unlock the full affordability "
                "and insurance read-out.")
        return

    monthly_income = income.get("monthly_income", 0.0)
    monthly_expenses = income.get("monthly_expenses", 0.0)
    annual_expenses = monthly_expenses * 12

    # ── Insurance + emergency-fund gaps ──
    goals_results = [{"result": g["result"], "return": g["blended_return"], "years": g["years"]}
                     for g in plan["goals"]]
    life = protection.recommended_life_cover(
        goals_results=goals_results, loans=loans, annual_expenses=annual_expenses,
        dependents=int(dependents), current_cover=float(current_life_cover))
    health = protection.recommended_health_cover(
        dependents=int(dependents), city_tier=city_tier, current_cover=float(current_health_cover))
    emergency = protection.recommended_emergency_fund(
        monthly_expenses=monthly_expenses, dependents=int(dependents),
        current_savings=float(current_savings))

    total_emi = sum(l["emi"] for l in loans) + income.get("fixed_obligations", 0.0)
    foir = protection.compute_foir(total_monthly_emi=total_emi, monthly_income=monthly_income)

    st.markdown("---")
    st.markdown("##### Safety-net gaps")
    g1, g2, g3 = st.columns(3)
    with g1:
        _gap_metric("Life cover gap", life.gap, life.total_need)
    with g2:
        _gap_metric("Health cover gap", health.gap, health.recommended)
    with g3:
        _gap_metric(f"Emergency fund gap ({emergency.recommended_months} mo)",
                    emergency.gap, emergency.recommended)

    foir_color = {"Safe": _SUCCESS, "Caution": _WARNING, "High": _DANGER}[foir.level]
    st.markdown(
        f"**Debt burden as % of income (FOIR): "
        f"<span style='color:{foir_color}'>{foir.ratio * 100:.0f}% — {foir.level}</span>**",
        unsafe_allow_html=True)
    st.caption(
        "FOIR = EMIs + fixed obligations ÷ income. Lenders typically view above ~50–55% as "
        "stretched — a planning benchmark, not a guarantee of loan eligibility. Lender criteria vary."
    )
    if foir.level == "High":
        st.caption("Above ~55%, new SIPs compete with EMIs for disposable income. "
                   "Consider prioritising high-interest debt before adding new SIPs.")

    # ── Year-by-year affordability chart ──
    st.markdown("##### Year-by-year affordability")
    horizon = max(1, round(max(g["years"] for g in plan["goals"])))
    rows = project_cashflow(
        starting_salary=monthly_income * 12,
        salary_hike_pct=income.get("salary_hike_pct", 0.0),
        starting_expenses=annual_expenses,
        expense_inflation_pct=income.get("expense_inflation_pct", 0.0),
        fixed_obligations=income.get("fixed_obligations", 0.0) * 12,
        total_monthly_sip=plan["total_monthly_sip"],
        horizon_years=horizon,
    )
    st.plotly_chart(_cashflow_chart(rows), use_container_width=True,
                    config={"displayModeBar": False})
    shortfall_years = [r.year_index + 1 for r in rows if r.is_shortfall]
    if shortfall_years:
        st.caption(f"Projected shortfall in year(s): {', '.join(map(str, shortfall_years))}. "
                   "Disposable income (after expenses + EMIs) dips below the total SIP outflow "
                   "those years.")
    else:
        st.caption("Disposable income stays above the total SIP outflow every projected year.")


def _gap_metric(label: str, gap: float, target: float) -> None:
    """Show a gap as a metric, green when fully covered."""
    if gap <= 0:
        # Single clean metric card (st.metric can't host an inline HTML icon; a
        # separate span would double-render "Covered"). Word alone is unambiguous.
        st.metric(label, "Covered")
    else:
        st.metric(label, _lakh_cr(gap),
                  delta=f"of {_lakh_cr(target)} needed", delta_color="off")


def _cashflow_chart(rows):
    """Grouped bars: disposable income vs total SIP outflow per year.
    Y-axis uses lakh/crore labels (via _lakh_cr tickvals+ticktext) — no raw "M" suffix.
    """
    import plotly.graph_objects as go

    years = [f"Y{r.year_index + 1}" for r in rows]
    disposable = [r.disposable_income for r in rows]
    sip = [r.total_sip_outflow for r in rows]

    # Build tickvals/ticktext in ₹ lakh/crore — Plotly has no native Indian formatter.
    all_vals = [v for v in disposable + sip if v is not None and v > 0]
    max_val = max(all_vals) if all_vals else 1_00_00_000
    tick_count = 5
    raw_step = max_val / tick_count
    if raw_step >= 1_00_00_000:
        tick_step = round(raw_step / 1_00_00_000) * 1_00_00_000
    elif raw_step >= 1_00_000:
        tick_step = round(raw_step / 1_00_000) * 1_00_000
    else:
        tick_step = round(raw_step / 10_000) * 10_000
    tick_step = max(tick_step, 1)
    tickvals = [i * tick_step for i in range(tick_count + 2)]
    ticktext = [_lakh_cr(v) for v in tickvals]

    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=years, y=disposable, name="Disposable income",
        marker=dict(color=_ACCENT),
        hovertemplate="%{x}: %{customdata}<extra>Disposable income</extra>",
        customdata=[_lakh_cr(v) for v in disposable],
    ))
    fig.add_trace(go.Bar(
        x=years, y=sip, name="Total SIP outflow",
        marker=dict(color=_WARNING),
        hovertemplate="%{x}: %{customdata}<extra>Total SIP outflow</extra>",
        customdata=[_lakh_cr(v) for v in sip],
    ))
    fig.update_layout(
        barmode="group",
        xaxis=dict(showgrid=False, tickfont=dict(color=_MUTED, size=10)),
        yaxis=dict(
            showgrid=True, gridcolor="rgba(255,255,255,0.06)",
            tickfont=dict(color=_MUTED, size=10),
            tickvals=tickvals, ticktext=ticktext,  # replaces tickprefix="₹"
        ),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, font=dict(color=_MUTED)),
    )
    return _base_layout(fig, height=320)


# ══════════════════════════════════════════════════════════════════════════════
# EXPLORE FUNDS — the ONLY screen that names + ranks specific funds.
# General, decoupled, neutral-weighted. Does NOT read the user's profile/goals.
# ══════════════════════════════════════════════════════════════════════════════

def view_explore(df) -> None:
    """
    Standalone, opt-in fund screener. Category dropdown + composite-weight
    sliders → live re-ranked table. This is the compliance "second mode": it
    NEVER reads risk_label / goals / income into the ranking, and it pairs named
    funds with metrics ONLY — never with a personalized SIP amount.
    """
    st.caption("Browse and rank equity funds by the metrics you care about. This screener is "
               "general — it does **not** use your profile or goals.")

    st.warning(
        "**Educational, not investment advice. Not a SEBI-registered adviser.** Rankings are "
        "built from historical metrics (Sharpe, Jensen's Alpha, return consistency vs the "
        "category). **Past performance does not indicate future results.**"
    )

    categories = sorted(df["category"].dropna().unique().tolist())
    if not categories:
        st.error("No fund categories available in the data.")
        return

    # Honor a category hand-off from a goal card (neutral weights), else default.
    handoff = st.session_state.pop("explore_category", None)
    reset_weights = st.session_state.pop("explore_reset_weights", False)
    if handoff in categories:
        default_cat_idx = categories.index(handoff)
        st.info(f"Showing **{_clean_category(handoff)}** funds with neutral, equal weights — "
                "the same view for everyone. Adjust the weights below to explore.")
    else:
        default_cat_idx = 0

    category = st.selectbox("Fund category", categories, index=default_cat_idx)

    st.markdown("**How much should each metric count?**")
    st.caption(
        "Set the relative importance of each metric — we normalise them to always total 100%."
    )
    w1, w2, w3 = st.columns(3)
    # Neutral 1/3 each on hand-off or first load; otherwise remember last weights.
    saved = st.session_state.get("_explore_weights") if not reset_weights else None
    with w1:
        ws = st.slider(
            "Return per unit of risk (Sharpe)", 0, 100,
            int((saved or {}).get("sharpe", 33)), 1,
            help="How much return this fund delivered per unit of price swings — historically. "
                 "Past performance does not indicate future results.",
        )
    with w2:
        wa = st.slider(
            "Manager's track record (Alpha)", 0, 100,
            int((saved or {}).get("alpha", 33)), 1,
            help="Return added beyond what the market's own movement would produce (after beta). "
                 "Based on historical data. Past performance does not indicate future results.",
        )
    with w3:
        wc = st.slider(
            "How often it beat benchmark (Consistency)", 0, 100,
            int((saved or {}).get("consistency", 34)), 1,
            help="Share of rolling periods it outperformed its category benchmark — historically. "
                 "Past performance does not indicate future results.",
        )
    st.session_state["_explore_weights"] = {"sharpe": ws, "alpha": wa, "consistency": wc}

    total_w = ws + wa + wc
    if total_w == 0:
        st.warning("Set at least one weight above zero to rank funds.")
        return
    weights = {"sharpe": ws / total_w, "alpha": wa / total_w, "consistency": wc / total_w}
    # Live caption showing normalised split (tells the truth about how ranking works)
    w_sharpe_pct = round(ws / total_w * 100)
    w_alpha_pct = round(wa / total_w * 100)
    w_cons_pct = 100 - w_sharpe_pct - w_alpha_pct
    st.caption(
        f"Your weights → Sharpe **{w_sharpe_pct}%** · Alpha **{w_alpha_pct}%** · "
        f"Consistency **{w_cons_pct}%** (always totals 100%)"
    )

    # Re-score the chosen category LIVE with these weights (Project 1 methodology).
    cat_df = df[df["category"] == category].copy()
    metric_cols = {"sharpe", "alpha", "consistency"}
    if cat_df.empty or not metric_cols.issubset(cat_df.columns):
        st.info("No rankable funds in this category with the available metrics.")
        return

    ranked = scoring.compute_composite_score(cat_df, weights=weights)
    ranked = ranked.sort_values("category_rank")

    st.markdown(f"#### {_clean_category(category)} — {len(ranked)} fund(s)")
    _render_fund_table(ranked)

    with st.expander("Why these metrics?"):
        st.markdown(
            "- **Return per unit of risk (Sharpe Ratio)** — how much return this fund has "
            "historically delivered for each unit of price swings it took on. Higher = smoother "
            "ride for the same return, historically.  \n"
            "  *Past performance does not indicate future results.*\n\n"
            "- **Manager's track record above expected (Jensen's Alpha)** — return added beyond "
            "what the market's own movement would produce (after adjusting for beta); positive = "
            "added value historically; negative = did not, vs this period's benchmark.  \n"
            "  *Calculated from historical data. Manager performance and market conditions change. "
            "Past performance does not indicate future results.*\n\n"
            "- **How often it beat its benchmark (Consistency)** — share of rolling periods it "
            "outperformed its category benchmark. 80% ≈ 4 of 5 periods — historically.  \n"
            "  *Measured over past periods. Past consistency does not guarantee future consistency. "
            "Past performance does not indicate future results.*\n\n"
            "Each metric is converted to a *within-category percentile* (so funds are compared "
            "only against peers), then blended by your weights. This mirrors the Project 1 "
            "mutual-fund analytics methodology."
        )

    st.caption(_DISCLAIMER)


def _render_fund_table(ranked) -> None:
    """Render the ranked-funds table with friendly columns and % formatting."""
    show = ranked.copy()
    col_map = {
        "category_rank": "Rank",
        "scheme_name": "Scheme",
        "composite_score": "Score",
        "sharpe": "Sharpe",
        "alpha": "Alpha",
        "consistency": "Consistency",
        "return_1y": "1Y", "return_3y": "3Y", "return_5y": "5Y",
        "total_aum_cr": "AUM (₹ Cr)",
    }
    cols = [c for c in col_map if c in show.columns]
    show = show[cols].rename(columns=col_map)

    # Percent-format return columns (stored as decimals).
    for c in ("1Y", "3Y", "5Y"):
        if c in show.columns:
            show[c] = (show[c] * 100).round(1)
    for c in ("Score", "Sharpe", "Alpha", "Consistency"):
        if c in show.columns:
            show[c] = show[c].round(3)
    if "AUM (₹ Cr)" in show.columns:
        show["AUM (₹ Cr)"] = show["AUM (₹ Cr)"].round(0)

    st.dataframe(
        show, use_container_width=True, hide_index=True,
        column_config={
            "1Y": st.column_config.NumberColumn("1Y", format="%.1f%%"),
            "3Y": st.column_config.NumberColumn("3Y", format="%.1f%%"),
            "5Y": st.column_config.NumberColumn("5Y", format="%.1f%%"),
            "Score": st.column_config.ProgressColumn(
                "Score", min_value=0.0, max_value=1.0, format="%.2f"),
        },
    )
