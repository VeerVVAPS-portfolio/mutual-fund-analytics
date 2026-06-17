"""
risk_profiler.py
Converts user questionnaire answers into a numeric risk score (0–100)
and maps it to a risk label + base allocation weights.
"""

from __future__ import annotations

# ── Scoring tables ────────────────────────────────────────────────────────────

# Each question has a max weight (sums to 100 across all questions).
# Higher answer index = higher risk tolerance.

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

# Base allocations per label (used for demo mode and prompt context)
BASE_ALLOCATIONS = {
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
    return BASE_ALLOCATIONS[label].copy()


def score_to_gauge_color(score: int) -> str:
    """Returns a hex color to use on the risk gauge: green → yellow → red."""
    if score <= 30:
        return "#10B981"   # green — Conservative
    elif score <= 55:
        return "#F59E0B"   # amber — Moderate Conservative
    elif score <= 70:
        return "#F97316"   # orange — Moderate Aggressive
    else:
        return "#EF4444"   # red — Aggressive


# ── Question metadata (used by Streamlit to render the form) ─────────────────

QUESTIONS = {
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
        "label": "If your portfolio dropped 20% tomorrow, you would…",
        "options": list(REACTION_SCORES.keys()),
        "help": "This reveals your emotional risk tolerance — often different from your stated preference.",
    },
    "debt": {
        "label": "What are your current debt obligations?",
        "options": list(DEBT_SCORES.keys()),
        "help": "High-interest debt should be cleared before investing aggressively.",
    },
}
