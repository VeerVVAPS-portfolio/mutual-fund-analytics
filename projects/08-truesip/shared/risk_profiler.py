"""
shared/risk_profiler.py — risk questionnaire scoring + base allocation weights.

Adapted from projects/02-ai-financial-profile-asset-allocation/src/risk_profiler.py.
CHANGES FROM ORIGINAL:
  - Added horizon_equity_band() — NEW function implementing the council's
    BUILD MANDATE #2: horizon-authoritative allocation (reconciliation rule).
    The per-goal equity band is set by the goal's time horizon; the risk profile
    is demoted to a tilt within that band. Panic-prone investors (Conservative /
    Moderate Conservative) are capped at band midpoint.
  - All other logic (scoring tables, labels, BASE_ALLOCATIONS, QUESTIONS) is
    copied verbatim from the original to preserve consistency with Project 2.
  - Removed no functions; everything in the original is kept.

Council mandate (SYNTHESIS.md, Build Mandate #2):
  Horizon bands: <3y → 0–10%  |  3–7y → 20–40%  |  7–15y → 50–70%  |  >15y → 70–85%
  Risk tilt within band: Aggressive → top of band; Conservative → mid or lower.
"""

from __future__ import annotations

# ── Scoring tables ────────────────────────────────────────────────────────────

AGE_SCORES = {
    "Under 25": 25,
    "25–35": 20,
    "35–50": 12,
    "50+": 5,
}  # weight: 25

HORIZON_SCORES = {
    "Less than 3 years": 5,
    "3–7 years": 15,
    "7–15 years": 22,
    "More than 15 years": 30,
}  # weight: 30

GOAL_SCORES = {
    "Capital preservation": 3,
    "Regular income": 8,
    "Tax saving (ELSS)": 12,
    "Wealth creation": 20,
}  # weight: 20

REACTION_SCORES = {
    "I would sell immediately to stop further losses": 2,
    "I would hold and wait for recovery": 10,
    "I would invest more — it's a buying opportunity": 15,
}  # weight: 15

DEBT_SCORES = {
    "High (home loan, car loan, etc.)": 2,
    "Moderate (credit card, personal loan)": 5,
    "None": 10,
}  # weight: 10

# ── Risk label mapping ────────────────────────────────────────────────────────

RISK_LABELS = [
    (0,  30, "Conservative"),
    (31, 55, "Moderate Conservative"),
    (56, 70, "Moderate Aggressive"),
    (71, 100, "Aggressive"),
]

# Base allocations per label (used for whole-person context + LLM prompt input;
# NOT used for per-goal SIP sizing — use horizon_equity_band() for that).
BASE_ALLOCATIONS: dict[str, dict[str, int]] = {
    "Conservative": {
        "equity": 20, "debt": 55, "gold": 15, "alternatives": 10
    },
    "Moderate Conservative": {
        "equity": 40, "debt": 40, "gold": 12, "alternatives": 8
    },
    "Moderate Aggressive": {
        "equity": 60, "debt": 25, "gold": 10, "alternatives": 5
    },
    "Aggressive": {
        "equity": 75, "debt": 15, "gold": 7, "alternatives": 3
    },
}

# ── Horizon equity bands (council SYNTHESIS.md Build Mandate #2) ─────────────
# Each tuple: (min_equity_pct, max_equity_pct)
_HORIZON_BANDS: list[tuple[float, float, float, float]] = [
    # years_min, years_max, eq_low, eq_high
    (0,   3,    0,   10),
    (3,   7,   20,   40),
    (7,  15,   50,   70),
    (15, 999,  70,   85),
]

# Risk label → tilt position within band (0.0 = bottom, 1.0 = top).
# Panic-prone labels capped at 0.5 (midpoint) per the mandate.
_LABEL_TILT: dict[str, float] = {
    "Conservative":        0.0,
    "Moderate Conservative": 0.5,   # capped at midpoint
    "Moderate Aggressive": 0.75,
    "Aggressive":          1.0,
}


def horizon_equity_band(years: float, risk_label: str) -> dict[str, float]:
    """
    Determine a goal's equity allocation using the council's reconciliation rule.

    The goal's time horizon sets the baseline equity band; the risk-profile label
    is a tilt within that band (never a competing person-level override).

    Args:
        years:      Time horizon for the specific goal (not the whole profile).
        risk_label: Output of get_risk_label() from the person-level quiz.

    Returns:
        Dict with keys:
          equity_pct      — resolved equity % for this goal (0–100)
          band_low        — band floor %
          band_high       — band ceiling %
          tilt            — 0–1 tilt applied within the band
    """
    band_low, band_high = 0.0, 10.0
    for y_min, y_max, eq_low, eq_high in _HORIZON_BANDS:
        if y_min <= years < y_max:
            band_low, band_high = float(eq_low), float(eq_high)
            break

    tilt = _LABEL_TILT.get(risk_label, 0.5)
    equity_pct = band_low + tilt * (band_high - band_low)

    return {
        "equity_pct": round(equity_pct, 1),
        "band_low":   band_low,
        "band_high":  band_high,
        "tilt":       tilt,
    }


# ── Public API ────────────────────────────────────────────────────────────────

def compute_risk_score(
    age: str,
    horizon: str,
    goal: str,
    reaction: str,
    debt: str,
) -> int:
    """Return a 0–100 risk score from questionnaire answers."""
    score = (
        AGE_SCORES.get(age, 0)
        + HORIZON_SCORES.get(horizon, 0)
        + GOAL_SCORES.get(goal, 0)
        + REACTION_SCORES.get(reaction, 0)
        + DEBT_SCORES.get(debt, 0)
    )
    return min(max(score, 0), 100)


def get_risk_label(score: int) -> str:
    for low, high, label in RISK_LABELS:
        if low <= score <= high:
            return label
    return "Moderate Aggressive"


def get_base_allocation(label: str) -> dict[str, int]:
    """Whole-person base allocation (context for LLM layer, not per-goal SIP sizing)."""
    return BASE_ALLOCATIONS[label].copy()


def score_to_gauge_color(score: int) -> str:
    """Returns a hex color for the risk gauge: green → amber → orange → red."""
    if score <= 30:
        return "#10B981"   # green — Conservative
    elif score <= 55:
        return "#F59E0B"   # amber — Moderate Conservative
    elif score <= 70:
        return "#F97316"   # orange — Moderate Aggressive
    else:
        return "#EF4444"   # red — Aggressive


# ── Question metadata (used by streamlit-ux-builder to render the form) ──────

QUESTIONS: dict[str, dict] = {
    "age": {
        "label": "What is your age?",
        "options": list(AGE_SCORES.keys()),
        "help": "Younger investors can afford more risk — time smooths out volatility.",
    },
    "horizon": {
        "label": "How long can you stay invested without needing this money?",
        "options": list(HORIZON_SCORES.keys()),
        "help": "The single biggest driver of how much equity you should hold.",
    },
    "goal": {
        "label": "What is your primary investment goal?",
        "options": list(GOAL_SCORES.keys()),
        "help": "ELSS qualifies for ₹1.5 L tax deduction under Section 80C.",
    },
    "reaction": {
        "label": "If your portfolio dropped 20% tomorrow, what would you do?",
        "options": list(REACTION_SCORES.keys()),
        "help": "This reveals your emotional risk tolerance — often different from your stated preference.",
    },
    "debt": {
        "label": "What are your current debt obligations?",
        "options": list(DEBT_SCORES.keys()),
        "help": "High-interest debt should be cleared before investing aggressively.",
    },
}
