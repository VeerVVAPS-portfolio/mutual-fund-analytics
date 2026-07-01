"""
shared/data_store.py — cached loader for the committed fund seed.

Council flagged trap #1: NEVER silently return an empty DataFrame. The entire
"PICK" section of TrueSIP is meaningless without fund data, and a silent empty
frame produces a plausible-looking empty UI with no error — a product trust
failure. This module raises loudly instead.

The seed file lives at:
    projects/08-truesip/data/scored_funds.csv

It is committed to the repo (maintained by the data-pipeline-runner agent)
so Streamlit Cloud deploys succeed without running the pipeline at boot.

Public API:
    load_scored_funds() -> pd.DataFrame
        Returns the full scored-funds DataFrame.
        Raises RuntimeError (surfaced to the user via st.error + st.stop)
        if the file is missing or unreadable.

    get_top_funds(category, n, df) -> list[dict]
        Returns top-n funds for a category from a pre-loaded DataFrame.
        Returns [] if the category has no ranked funds (caller must handle).

    CATEGORIES -> list[str]
        Distinct category values present in the seed file at import time.
        Populated lazily on first load; empty list before first call.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import streamlit as st

# Canonical path: relative to this file (shared/ is one level below project root).
_SEED_PATH = Path(__file__).resolve().parent.parent / "data" / "scored_funds.csv"

# Populated on first successful load — downstream can inspect available categories.
CATEGORIES: list[str] = []

# Expected columns that must be present for the app to function.
_REQUIRED_COLUMNS = {"scheme_name", "category", "composite_score", "category_rank"}


@st.cache_data(show_spinner=False)
def load_scored_funds() -> pd.DataFrame:
    """
    Load and cache the scored_funds.csv seed.

    Returns:
        pd.DataFrame sorted by category then category_rank.

    Raises:
        RuntimeError if the file is missing, empty, or lacks required columns.
        (Callers should catch this and call st.error() + st.stop().)

    Usage in app.py:
        try:
            df = load_scored_funds()
        except RuntimeError as e:
            st.error(str(e))
            st.stop()
    """
    if not _SEED_PATH.exists():
        raise RuntimeError(
            f"Fund data file not found: {_SEED_PATH}\n\n"
            "The data-pipeline-runner agent must be run first to generate "
            "`projects/08-truesip/data/scored_funds.csv`. "
            "Without this file the Explore Funds screener cannot operate."
        )

    try:
        df = pd.read_csv(_SEED_PATH)
    except Exception as exc:
        raise RuntimeError(
            f"Could not read fund data from {_SEED_PATH}: {exc}"
        ) from exc

    if df.empty:
        raise RuntimeError(
            f"Fund data file exists but is empty: {_SEED_PATH}\n"
            "Re-run the data-pipeline-runner agent to regenerate it."
        )

    missing = _REQUIRED_COLUMNS - set(df.columns)
    if missing:
        raise RuntimeError(
            f"Fund data file is missing required columns: {sorted(missing)}\n"
            f"File: {_SEED_PATH}\n"
            "Re-run the data-pipeline-runner agent to regenerate it with the correct schema."
        )

    df = df.sort_values(["category", "category_rank"]).reset_index(drop=True)

    # Populate module-level CATEGORIES for any caller that needs the list
    # without re-reading the file.
    global CATEGORIES
    CATEGORIES = sorted(df["category"].dropna().unique().tolist())

    return df


def get_top_funds(
    category: str,
    n: int = 3,
    df: pd.DataFrame | None = None,
) -> list[dict]:
    """
    Return the top-n ranked funds for a given category.

    Args:
        category: Category string (must match a value in df["category"]).
        n:        Number of top funds to return (default 3).
        df:       Pre-loaded DataFrame from load_scored_funds(). If None,
                  load_scored_funds() is called internally — only safe inside
                  a Streamlit session where the cache is warm.

    Returns:
        List of dicts with fund-level fields. Empty list if the category
        has no funds or if df is unavailable. NEVER raises — callers must
        handle the empty-list case and display an informative message.
    """
    if df is None:
        try:
            df = load_scored_funds()
        except RuntimeError:
            return []

    cat_df = df[df["category"] == category].sort_values("category_rank").head(n)
    if cat_df.empty:
        return []

    display_cols = [
        "scheme_name", "category_rank", "composite_score",
        "sharpe", "alpha", "consistency",
        "return_1y", "return_3y", "return_5y",
        "total_aum_cr",
    ]
    available = [c for c in display_cols if c in cat_df.columns]
    return cat_df[available].to_dict(orient="records")
