"""
shared/explainer.py — TrueSIP's LLM "explain-why" layer.

WHAT THIS MODULE OWNS
─────────────────────
The deterministic engine (planning_engine.py) computes every number.
This module's only job is to turn those numbers into plain-language prose
that explains the *reasoning* — why the horizons drove these allocations,
why a near-term goal stays debt-heavy, why the long-horizon goal carries
more equity, and so on.

HARD RULE — the product's credibility spine
────────────────────────────────────────────
The LLM NEVER emits a rupee SIP figure or any computed metric from the
plan. It receives numbers as INPUT context so it can reason qualitatively,
but the returned prose must stay number-light and never reproduce a ₹ SIP
figure. The finance-correctness-auditor can grep the returned string and
expect to find no "₹ + digit" pattern originating from the LLM.

Pattern reused from Project 2 (allocation_engine.py):
  • OpenAI-compatible Groq client  (base_url="https://api.groq.com/openai/v1")
  • model: llama-3.3-70b-versatile
  • resolve_api_key() checks st.secrets → .env → None
  • Any exception falls back to _demo_explanation() — never crashes the UI

INTERFACE (locked — matches streamlit-ux-builder's expectation)
──────────────────────────────────────────────────────────────
  explain_plan(plan: dict) -> str          — markdown prose, "Why this plan?"
  _demo_explanation(plan: dict) -> str     — deterministic, plan-aware fallback
  resolve_api_key() -> str | None          — checks st.secrets then .env
"""

from __future__ import annotations

import os
import json

# ── sys.path bootstrap (mirrors planning_engine.py's pattern) ─────────────────
# Lets `python shared/explainer.py` work without installing as a package.
if __package__ in (None, ""):
    import sys as _sys
    from pathlib import Path as _Path
    _ROOT = _Path(__file__).resolve().parent.parent
    if str(_ROOT) not in _sys.path:
        _sys.path.insert(0, str(_ROOT))


# ══════════════════════════════════════════════════════════════════════════════
# API KEY RESOLUTION  (Project 2 pattern — verbatim)
# ══════════════════════════════════════════════════════════════════════════════

def resolve_api_key() -> str | None:
    """
    Resolve GROQ_API_KEY from Streamlit secrets (deployed) or .env (local).

    Order:
      1. st.secrets["GROQ_API_KEY"]   — Streamlit Cloud / secrets.toml
      2. os.environ["GROQ_API_KEY"]   — loaded from .env by dotenv or shell
      3. None                         — demo mode, no crash
    """
    # Try Streamlit secrets first (won't exist outside a Streamlit process).
    try:
        import streamlit as st  # type: ignore[import]
        key = st.secrets.get("GROQ_API_KEY", None)
        if key:
            return key
    except Exception:
        pass

    # Fall back to environment / .env.
    try:
        from dotenv import load_dotenv  # type: ignore[import]
        load_dotenv()
    except Exception:
        pass

    return os.environ.get("GROQ_API_KEY") or None


# ══════════════════════════════════════════════════════════════════════════════
# PROMPT BUILDERS
# ══════════════════════════════════════════════════════════════════════════════

_SYSTEM_PROMPT = """\
You are a plain-language financial educator helping an Indian investor understand
why their SIP plan is structured the way it is.

Your ONLY job is to explain the REASONING behind the plan — the "why". The numbers
(SIP amounts, percentages, future values) have already been computed by a
deterministic engine and will be shown separately in the UI. Do NOT reproduce
any rupee SIP figure in your prose. Do NOT suggest or invent any new amount.

Write in clear, jargon-free English. No markdown headers — only prose paragraphs
with a blank line between them. Aim for 180–260 words total. Be warm but
direct — this is someone's real money.

You MUST respond with a single valid JSON object and nothing else:
{
  "plan_summary": "<1-paragraph overview of the overall plan logic>",
  "horizon_logic": "<1 paragraph on how each goal's time horizon drove its equity/debt/gold split>",
  "risk_tilt_note": "<1 paragraph on how the person's risk label tilted allocations within the horizon bands — or why it was capped>",
  "blended_return_note": "<1 paragraph on why near-term goals use a lower return assumption than long-horizon goals, and why that matters for the SIP>"
}

Rules:
1. No rupee signs followed by digits (no ₹ + number). Never name a specific SIP amount.
2. No percent signs that echo the plan's exact equity_pct / blended_return numbers.
3. Reference goal NAMES and their relative horizons ("short", "medium", "long") — not the exact year counts.
4. Never say "I recommend" or act as a SEBI-registered advisor.
5. Keep every paragraph under 80 words.
"""


def _build_context_block(plan: dict) -> str:
    """
    Summarise the plan dict into a compact context string for the LLM prompt.
    Gives the LLM enough qualitative shape to reason about WITHOUT sending
    raw ₹ figures it might echo back verbatim.
    """
    risk_label = plan.get("risk_label", "unknown")
    goals = plan.get("goals", [])
    affordability_ok = plan.get("affordability_ok", True)
    assumptions = plan.get("return_assumptions", {})

    goal_lines: list[str] = []
    for g in goals:
        years = g.get("years", 0)
        name = g.get("name", "goal")
        eq_pct = g.get("equity_pct", 0)
        blended = g.get("blended_return", 0)
        band = g.get("band", {})

        # Horizon label — qualitative, no raw year count sent to LLM.
        if years < 3:
            horizon_label = "short-term (under 3 years)"
        elif years < 7:
            horizon_label = "medium-term (3–7 years)"
        elif years < 15:
            horizon_label = "long-term (7–15 years)"
        else:
            horizon_label = "very long-term (over 15 years)"

        # Qualitative equity descriptor.
        if eq_pct < 15:
            eq_desc = "almost entirely debt and gold"
        elif eq_pct < 35:
            eq_desc = "mostly debt with a modest equity sleeve"
        elif eq_pct < 55:
            eq_desc = "balanced equity and debt"
        elif eq_pct < 70:
            eq_desc = "equity-leaning with a meaningful debt buffer"
        else:
            eq_desc = "predominantly equity"

        # Qualitative blended return descriptor.
        if blended < 0.08:
            return_desc = "conservative (debt-anchored)"
        elif blended < 0.10:
            return_desc = "moderate"
        else:
            return_desc = "growth-oriented (equity-anchored)"

        tilt = band.get("tilt", 0.5)
        tilt_desc = (
            "at the lower end of its band (panic-prone / conservative tilt)"
            if tilt <= 0.3
            else "near the top of its band (growth tilt)"
            if tilt >= 0.7
            else "near the midpoint of its band"
        )

        goal_lines.append(
            f'  • "{name}": {horizon_label}, allocation is {eq_desc}, '
            f"return assumption is {return_desc}, risk tilt is {tilt_desc}."
        )

    goals_block = "\n".join(goal_lines) if goal_lines else "  (no goals)"
    affordability_note = (
        "The total SIP is within the person's projected income over the plan horizon."
        if affordability_ok
        else "The total SIP creates a projected cashflow shortfall in some years — the person should review their goal amounts or timeline."
    )

    return f"""INVESTOR PROFILE
Risk label: {risk_label}

GOALS IN THIS PLAN
{goals_block}

RETURN ASSUMPTIONS USED (documented conservative estimates, not forecasts)
  Equity: {int(assumptions.get('equity', 0.12) * 100)}% p.a.
  Debt:   {int(assumptions.get('debt', 0.07) * 100)}% p.a.
  Gold:   {int(assumptions.get('gold', 0.06) * 100)}% p.a.

AFFORDABILITY
{affordability_note}
"""


# ══════════════════════════════════════════════════════════════════════════════
# DEMO FALLBACK  — deterministic, plan-aware (no API key needed)
# ══════════════════════════════════════════════════════════════════════════════

def _demo_explanation(plan: dict) -> str:
    """
    Plan-aware deterministic fallback used when no GROQ_API_KEY is present.

    This must produce genuinely sensible prose — not generic filler — because
    most portfolio visitors will hit this path. It reads the plan dict directly
    and constructs goal-specific language from it.

    Returns a markdown string with NO rupee-prefixed figures.
    """
    risk_label = plan.get("risk_label", "Moderate Aggressive")
    goals = plan.get("goals", [])
    affordability_ok = plan.get("affordability_ok", True)

    # ── Classify goals by horizon ──
    short_goals: list[str] = []
    medium_goals: list[str] = []
    long_goals: list[str] = []
    very_long_goals: list[str] = []

    for g in goals:
        name = g.get("name", "this goal")
        years = g.get("years", 0)
        if years < 3:
            short_goals.append(name)
        elif years < 7:
            medium_goals.append(name)
        elif years < 15:
            long_goals.append(name)
        else:
            very_long_goals.append(name)

    def _join(names: list[str]) -> str:
        if not names:
            return ""
        if len(names) == 1:
            return f'"{names[0]}"'
        return ", ".join(f'"{n}"' for n in names[:-1]) + f' and "{names[-1]}"'

    # ── Determine risk cap language ──
    conservative_labels = {"Conservative", "Moderate Conservative"}
    is_conservative = risk_label in conservative_labels

    # ── plan_summary ──
    n_goals = len(goals)
    goal_word = "goal" if n_goals == 1 else "goals"
    summary = (
        f"This plan covers {n_goals} financial {goal_word} "
        f"for an investor with a **{risk_label}** risk profile. "
        "Each goal gets its own tailored mix of equity, debt, and gold — "
        "because a one-size allocation would either over-risk money needed soon "
        "or under-invest money that has years to compound. "
        "Every SIP amount is solved backwards from the goal's inflation-adjusted "
        "future cost using a blended return that honestly reflects each goal's "
        "own asset mix — not a generic flat rate applied to all goals."
    )

    # ── horizon_logic ──
    horizon_parts: list[str] = []
    if short_goals:
        horizon_parts.append(
            f'{_join(short_goals)} {"is" if len(short_goals) == 1 else "are"} '
            "a near-term commitment, so the allocation stays almost entirely in "
            "debt and gold — capital protection matters far more than growth "
            "when the money is needed within a few years."
        )
    if medium_goals:
        horizon_parts.append(
            f'{_join(medium_goals)} {"sits" if len(medium_goals) == 1 else "sit"} '
            "in the medium-term band, where a modest equity sleeve is added "
            "alongside a debt-heavy core. The equity portion offers some upside "
            "without betting the goal on market timing."
        )
    if long_goals:
        horizon_parts.append(
            f'{_join(long_goals)} {"has" if len(long_goals) == 1 else "have"} '
            "enough runway to ride out market cycles, so equity takes a meaningful "
            "share — compounding over many years is what makes the eventual target "
            "reachable with a manageable monthly commitment."
        )
    if very_long_goals:
        horizon_parts.append(
            f'{_join(very_long_goals)} {"benefits" if len(very_long_goals) == 1 else "benefit"} '
            "from the longest horizon band, where equity is dominant. Time is "
            "the most powerful risk-reduction tool available — decades of "
            "compounding absorb volatility that would be catastrophic over one or "
            "two years."
        )
    if not horizon_parts:
        horizon_parts.append(
            "Each goal's time horizon was the primary input to its asset mix — "
            "the closer the goal, the more the allocation shifts toward capital "
            "preservation over growth."
        )

    horizon_logic = " ".join(horizon_parts)

    # ── risk_tilt_note ──
    if is_conservative:
        risk_tilt = (
            f"A **{risk_label}** profile means the investor is more sensitive to "
            "drawdowns than the average person. Rather than overriding the "
            "horizon band, this risk label acts as a cap — keeping equity at or "
            "below the midpoint of the horizon band for each goal. The plan "
            "still invests for growth where the horizon allows; it just doesn't "
            "push equity to the band ceiling the way an Aggressive profile would."
        )
    elif risk_label == "Aggressive":
        risk_tilt = (
            "An **Aggressive** risk profile means the investor has both the "
            "stomach and, where the horizon permits, the time to accept "
            "higher volatility in exchange for higher expected returns. "
            "The allocation tilts equity toward the top of each horizon band — "
            "but the band itself is still set by the goal's time horizon, "
            "not the risk label. Even for aggressive investors, a near-term "
            "goal stays debt-heavy because no amount of risk tolerance makes "
            "a two-year runway long enough to recover from an equity drawdown."
        )
    else:
        risk_tilt = (
            f"A **{risk_label}** profile places equity within the middle portion "
            "of each goal's horizon band — neither at the floor nor the ceiling. "
            "The risk label works as a fine-tuner: it shifts the allocation "
            "modestly within the range that the goal's horizon already "
            "determined is safe, rather than overriding that range entirely."
        )

    # ── blended_return_note ──
    blended_return_note = (
        "A near-term, debt-heavy goal is expected to grow more slowly than a "
        "long-term, equity-heavy one — and that difference in expected return "
        "directly affects how much needs to be set aside each month. "
        "Using a single flat return for every goal (as many planning tools do) "
        "would under-state the required SIP for conservative, short-horizon "
        "goals and over-state it for long-horizon equity goals. "
        "Instead, each goal's blended return is computed from its own "
        "asset mix, so the SIP solved from it is honest to the actual "
        "portfolio the money will be invested in."
    )

    # ── affordability note (appended only when there's a shortfall) ──
    affordability_line = ""
    if not affordability_ok:
        affordability_line = (
            "\n\n> **Note:** The projected cashflow shows that the combined "
            "monthly commitment may exceed available income in some years. "
            "Consider extending the timeline on lower-priority goals, "
            "reducing their target amounts, or revisiting this plan when "
            "income grows."
        )

    # ── Assemble markdown ──
    md = (
        f"**Why this plan?**\n\n"
        f"{summary}\n\n"
        f"{horizon_logic}\n\n"
        f"{risk_tilt}\n\n"
        f"{blended_return_note}"
        f"{affordability_line}"
    )
    return md


# ══════════════════════════════════════════════════════════════════════════════
# MAIN PUBLIC INTERFACE
# ══════════════════════════════════════════════════════════════════════════════

def explain_plan(plan: dict) -> str:
    """
    Return a markdown prose string ("Why this plan?") explaining the reasoning
    behind the deterministic plan.

    The LLM receives the plan's qualitative shape as context and returns
    reasoning-only prose — no rupee SIP figures, no invented metrics.
    On any error (missing key, API failure, timeout), falls back to
    _demo_explanation() so the results screen never crashes.

    Args:
        plan: the dict returned by planning_engine.build_plan().

    Returns:
        A markdown string. Never raises.
    """
    api_key = resolve_api_key()
    if not api_key:
        return _demo_explanation(plan)

    try:
        from openai import OpenAI  # type: ignore[import]

        client = OpenAI(api_key=api_key, base_url="https://api.groq.com/openai/v1")

        context_block = _build_context_block(plan)
        user_message = (
            "Here is the investor's plan context:\n\n"
            f"{context_block}\n\n"
            "Now write the qualitative explanation JSON as instructed. "
            "Remember: no rupee figures, no specific percentages from the plan, "
            "just the reasoning in plain English."
        )

        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": _SYSTEM_PROMPT},
                {"role": "user", "content": user_message},
            ],
            response_format={"type": "json_object"},
            temperature=0.4,
            max_tokens=600,
        )

        raw = response.choices[0].message.content or ""
        data = json.loads(raw)

        # ── Assemble the four prose fields into markdown ──
        plan_summary = data.get("plan_summary", "").strip()
        horizon_logic = data.get("horizon_logic", "").strip()
        risk_tilt = data.get("risk_tilt_note", "").strip()
        blended_note = data.get("blended_return_note", "").strip()

        parts = [p for p in [plan_summary, horizon_logic, risk_tilt, blended_note] if p]
        if not parts:
            return _demo_explanation(plan)

        md = "**Why this plan?**\n\n" + "\n\n".join(parts)

        # ── Guard: if the LLM slipped a ₹+digit pattern in, fall back ──
        import re
        if re.search(r"₹\s*[\d,]+", md):
            return _demo_explanation(plan)

        return md

    except Exception:
        # Any API / parse error → demo fallback, never crash.
        return _demo_explanation(plan)


# ══════════════════════════════════════════════════════════════════════════════
# SELF-CHECK  /  verify the demo path and the no-₹-figure guarantee
#   Run:  python shared/explainer.py
# ══════════════════════════════════════════════════════════════════════════════

def _selfcheck() -> None:
    """
    Build a sample plan via planning_engine.build_plan, call explain_plan with
    no API key (demo path), and assert:
      1. The returned string is non-empty.
      2. No ₹ + digit pattern appears in the prose (the hard rule).
      3. Goal names from the plan appear in the prose (plan-aware, not filler).
    """
    import re
    import sys
    import pandas as pd

    # Windows consoles — force UTF-8 for the ₹ symbol in assertions.
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

    # Ensure GROQ_API_KEY is absent so we exercise the demo path.
    os.environ.pop("GROQ_API_KEY", None)

    print("=" * 74)
    print("TrueSIP explainer.py — self-check (demo path only)")
    print("=" * 74)

    from shared.planning_engine import build_plan, LARGE_CAP, LARGE_AND_MID_CAP, FLEXI_CAP

    # Minimal DataFrame seed (only 'category' is read by build_plan).
    df = pd.DataFrame({
        "category": [LARGE_CAP, LARGE_AND_MID_CAP, FLEXI_CAP],
        "scheme_name": ["A", "B", "C"],
        "composite_score": [1, 2, 3],
        "category_rank": [1, 1, 1],
    })

    # ── Test 1: multi-goal plan (short + long + very-long) ──
    print("\n[1] Multi-goal plan — Emergency + Education + Retirement")
    plan_a = build_plan(
        goals=[
            {"name": "Emergency top-up", "amount": 2_00_000, "years": 2},
            {"name": "Child Education",  "amount": 30_00_000, "years": 10},
            {"name": "Retirement",       "amount": 50_00_000, "years": 25},
        ],
        risk_label="Moderate Aggressive",
        income={
            "monthly_income": 1_50_000, "monthly_expenses": 50_000,
            "fixed_obligations": 20_000, "salary_hike_pct": 0.08,
            "expense_inflation_pct": 0.06,
        },
        sip_params={"inflation_rate": 0.06, "step_up_pct": 0.0},
        df=df,
    )

    explanation_a = explain_plan(plan_a)

    assert explanation_a, "explain_plan returned empty string"
    assert "Why this plan?" in explanation_a, "Missing heading in explanation"

    # Hard rule: no ₹ + digit originating from LLM.
    rupee_matches = re.findall(r"₹\s*[\d,]+", explanation_a)
    assert not rupee_matches, (
        f"VIOLATION — ₹-prefixed figure found in prose: {rupee_matches}"
    )

    # Plan-aware: goal names should appear (demo fallback references them).
    assert "Emergency top-up" in explanation_a, "Goal name not mentioned in prose"
    assert "Retirement" in explanation_a, "Goal name not mentioned in prose"

    print(f"    Explanation length: {len(explanation_a)} chars  ✓")
    print(f"    No ₹-figure leaked  ✓")
    print(f"    Goal names present  ✓")
    print()
    print("── Explanation preview (first 500 chars) ──")
    print(explanation_a[:500])

    # ── Test 2: single short-term goal (Conservative profile) ──
    print("\n[2] Single near-term goal — Conservative profile")
    plan_b = build_plan(
        goals=[{"name": "House Down Payment", "amount": 10_00_000, "years": 3}],
        risk_label="Conservative",
        income=None,
        sip_params={"inflation_rate": 0.06, "step_up_pct": 0.0},
        df=df,
    )

    explanation_b = explain_plan(plan_b)

    assert explanation_b, "explain_plan returned empty string for plan_b"
    rupee_b = re.findall(r"₹\s*[\d,]+", explanation_b)
    assert not rupee_b, f"VIOLATION — ₹-figure found in plan_b prose: {rupee_b}"
    assert "House Down Payment" in explanation_b, "Goal name missing from plan_b prose"
    assert "Conservative" in explanation_b, "Risk label missing from plan_b prose"

    print(f"    Explanation length: {len(explanation_b)} chars  ✓")
    print(f"    No ₹-figure leaked  ✓")
    print(f"    Goal name + risk label present  ✓")

    print()
    print("=" * 74)
    print("ALL SELF-CHECKS PASSED")
    print("=" * 74)


if __name__ == "__main__":
    _selfcheck()
