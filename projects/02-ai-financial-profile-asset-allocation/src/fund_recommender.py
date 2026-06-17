"""
fund_recommender.py
Maps an equity allocation to relevant mutual fund categories from Project 1,
and pulls the top-ranked funds from scored_funds.csv when available.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

# Path to Project 1's output (relative to this file's project root)
PROJECT_ROOT = Path(__file__).resolve().parent.parent
SCORED_FUNDS_PATH = (
    PROJECT_ROOT.parent
    / "01-mutual-fund-analytics-automation"
    / "data"
    / "processed"
    / "scored_funds.csv"
)

# ── Category recommendation logic ─────────────────────────────────────────────

def recommend_categories(
    equity_pct: int,
    risk_label: str,
    goal: str,
) -> list[dict]:
    """
    Returns a list of recommended fund categories with rationale,
    based on how much equity is in the allocation and the investor's profile.
    """
    categories = []

    if equity_pct == 0:
        return categories

    # Large Cap is always the core equity holding for stability
    categories.append({
        "category": "Large Cap",
        "rationale": "Core equity holding — top 100 companies by market cap. Lower volatility than mid/small caps with reliable long-term compounding.",
        "suggested_weight": "Primary",
    })

    if risk_label in ("Moderate Aggressive", "Aggressive"):
        categories.append({
            "category": "Flexi Cap",
            "rationale": "Fund manager dynamically allocates across market caps, giving exposure to mid and small cap growth without you having to rebalance manually.",
            "suggested_weight": "Secondary",
        })

    if risk_label == "Aggressive":
        categories.append({
            "category": "Mid Cap",
            "rationale": "Higher growth potential than Large Cap with more volatility — suitable for investors with a 7+ year horizon and high risk tolerance.",
            "suggested_weight": "Satellite",
        })

    if goal == "Tax saving (ELSS)":
        categories.append({
            "category": "ELSS",
            "rationale": "Equity Linked Saving Scheme qualifies for ₹1.5L deduction under Section 80C with a 3-year lock-in — the shortest among 80C instruments.",
            "suggested_weight": "Tax-saving allocation",
        })

    return categories


def get_top_funds(category: str, n: int = 3) -> list[dict]:
    """
    Reads Project 1's scored_funds.csv and returns the top-n funds
    for the given category. Returns an empty list if the file isn't found
    (so the app degrades gracefully without Project 1 data).
    """
    if not SCORED_FUNDS_PATH.exists():
        return []

    try:
        df = pd.read_csv(SCORED_FUNDS_PATH)

        # Filter to the requested category and top-ranked funds
        cat_df = (
            df[df["category"] == category]
            .sort_values("category_rank")
            .head(n)
        )

        if cat_df.empty:
            return []

        cols = ["scheme_name", "category_rank", "composite_score",
                "sharpe", "alpha", "consistency"]
        available = [c for c in cols if c in cat_df.columns]

        return cat_df[available].to_dict(orient="records")

    except Exception:
        return []


def build_fund_recommendations(
    equity_pct: int,
    risk_label: str,
    goal: str,
) -> list[dict]:
    """
    Returns enriched category cards: category info + top fund picks if available.
    """
    categories = recommend_categories(equity_pct, risk_label, goal)

    for cat in categories:
        cat["top_funds"] = get_top_funds(cat["category"])

    return categories
