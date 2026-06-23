"""
fund_recommender.py — surfaces top-ranked equity funds from Project 1 for
long-horizon goals. Degrades gracefully (returns an empty list) if
Project 1's scored_funds.csv isn't available.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SCORED_FUNDS_PATH = (
    PROJECT_ROOT.parent
    / "01-mutual-fund-analytics-automation"
    / "data"
    / "processed"
    / "scored_funds.csv"
)

# Below this horizon, equity SIPs aren't appropriate — Project 1 only
# scores equity schemes, so shorter goals get a caution, not a fund pick.
MIN_EQUITY_HORIZON_YEARS = 7

DEFAULT_CATEGORY = "Large Cap"  # core, lower-volatility equity holding


def get_top_funds(category: str = DEFAULT_CATEGORY, n: int = 3) -> list[dict]:
    """Top-n ranked funds for a category from Project 1's output. Empty list if unavailable."""
    if not SCORED_FUNDS_PATH.exists():
        return []

    try:
        df = pd.read_csv(SCORED_FUNDS_PATH)
        cat_df = df[df["category"] == category].sort_values("category_rank").head(n)
        if cat_df.empty:
            return []
        cols = ["scheme_name", "category_rank", "composite_score", "sharpe", "alpha", "consistency"]
        available = [c for c in cols if c in cat_df.columns]
        return cat_df[available].to_dict(orient="records")
    except Exception:
        return []


def recommend_for_goal(years: float) -> dict:
    """
    Returns either fund picks (long horizon) or a caution message (short
    horizon) for a given goal's time-to-goal.
    """
    if years < MIN_EQUITY_HORIZON_YEARS:
        return {
            "eligible": False,
            "message": (
                f"This goal is {years:.0f} years away — too short for equity SIPs to "
                "reliably ride out volatility. Consider debt or hybrid funds instead; "
                "this tool currently only scores equity schemes (from Project 1), so no "
                "specific fund pick is shown here."
            ),
            "funds": [],
        }

    funds = get_top_funds()
    return {
        "eligible": True,
        "message": f"{years:.0f}-year horizon suits equity. Top-ranked {DEFAULT_CATEGORY} funds:",
        "funds": funds,
    }
