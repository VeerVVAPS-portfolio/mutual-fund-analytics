"""
shared/scoring.py — fund eligibility filter + composite score.

Adapted from projects/01-mutual-fund-analytics-automation/src/scoring.py.
CHANGES FROM ORIGINAL:
  - Removed the main() pipeline runner (file I/O lives in data_store.py).
  - Functions are pure: they take DataFrames and return DataFrames; no CSV reads/writes.
  - Both functions are importable at module level with no side effects.
  - AUM_THRESHOLD_CR and WEIGHTS exposed as module-level constants so downstream
    agents (streamlit-ux-builder, integration-logic-architect) can read/override them.

Scoring methodology (unchanged from Project 1):
  Stage 1 — Eligibility: total_aum_cr >= AUM_THRESHOLD_CR AND return_5y not null.
  Stage 2 — Composite: Sharpe, Jensen's Alpha, Consistency each converted to a
             within-category percentile rank (0–1), then weighted-summed.
"""

import pandas as pd

AUM_THRESHOLD_CR = 1000  # ₹1,000 crore liquidity gate

# Weights must sum to 1. Downstream agents may pass a custom dict to
# compute_composite_score(); this is the default used if none is supplied.
WEIGHTS: dict[str, float] = {
    "sharpe": 1 / 3,
    "alpha": 1 / 3,
    "consistency": 1 / 3,
}


def apply_eligibility_filter(df: pd.DataFrame) -> pd.DataFrame:
    """
    Return the subset of df that passes the two-stage eligibility gate.
    Input df must have columns: total_aum_cr, return_5y.
    Returns a copy (original is untouched).
    """
    big_enough = df["total_aum_cr"] >= AUM_THRESHOLD_CR
    has_track_record = df["return_5y"].notna()
    return df[big_enough & has_track_record].copy()


def compute_composite_score(
    df: pd.DataFrame,
    weights: dict[str, float] | None = None,
) -> pd.DataFrame:
    """
    Add within-category percentile columns (<metric>_pct), a composite_score
    (0–1), and a category_rank (1 = best) to df.

    Input df must have columns: category, sharpe, alpha, consistency.
    Returns a new DataFrame (original is untouched).

    Args:
        df:      Eligible-funds DataFrame (output of apply_eligibility_filter).
        weights: Optional weight dict overriding WEIGHTS. Must sum to ~1 and
                 keys must be a subset of {sharpe, alpha, consistency}.
    """
    if weights is None:
        weights = WEIGHTS
    df = df.copy()

    for metric in weights:
        df[f"{metric}_pct"] = df.groupby("category")[metric].rank(pct=True)

    df["composite_score"] = sum(weights[m] * df[f"{m}_pct"] for m in weights)
    df["category_rank"] = (
        df.groupby("category")["composite_score"]
        .rank(ascending=False, method="min")
        .astype(int)
    )
    return df
