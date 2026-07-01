"""
shared/metrics.py — per-fund return/risk metric computation.

Adapted from projects/01-mutual-fund-analytics-automation/src/metrics.py.
CHANGES FROM ORIGINAL:
  - Removed load_nav_series() and load_nifty_returns() — file I/O is the
    pipeline's job (data-pipeline-runner agent). This module only holds the
    PURE MATH functions so downstream agents can call them on pre-loaded Series.
  - Removed main() and compute_consistency_table() (pipeline-only utilities;
    not needed at dashboard runtime — the seed CSV already has consistency scores).
  - cagr(), compute_fund_metrics() are kept as pure functions.
  - Exported constants: RISK_FREE_RATE, TRADING_DAYS_PER_YEAR, LOOKBACK_YEARS.

Note: At dashboard runtime, the pre-scored scored_funds.csv (loaded via
shared.data_store) already contains sharpe/alpha/consistency/composite_score.
These functions are here for the integration-logic-architect to reference the
exact methodology when building planning_engine.py, and for any future
pipeline re-run within the TrueSIP project.
"""

from __future__ import annotations

import pandas as pd

RISK_FREE_RATE = 0.07            # India 10Y G-Sec proxy
TRADING_DAYS_PER_YEAR = 252
LOOKBACK_YEARS = 3               # window for Beta / Sharpe / Alpha


def cagr(nav: pd.Series, years: float) -> float | None:
    """
    Compound annual growth rate over the trailing `years`, or None if the
    fund's history doesn't reach back that far.

    Args:
        nav:   NAV time-series indexed by date (datetime index, oldest first).
        years: Number of trailing years to measure.

    Returns:
        CAGR as a decimal (e.g. 0.12 for 12%), or None if insufficient history.
    """
    end_date = nav.index.max()
    start_date = end_date - pd.DateOffset(years=years)

    if nav.index.min() > start_date:
        return None

    start_nav = nav.loc[:start_date].iloc[-1]
    end_nav = nav.iloc[-1]
    return (end_nav / start_nav) ** (1 / years) - 1


def compute_fund_metrics(
    daily_returns: pd.Series,
    nifty_returns: pd.Series,
    nav: pd.Series,
) -> dict:
    """
    Compute return/risk metrics for a single fund.

    Args:
        daily_returns: Fund's daily pct_change series (datetime index).
        nifty_returns: NIFTY 50 daily pct_change series (datetime index).
        nav:           Fund NAV series (datetime index) — used only for CAGR.

    Returns:
        Dict with keys: return_1y, return_3y, return_5y, return_10y,
                        beta, sharpe, alpha.
        Numeric metrics are None when there is insufficient history.
    """
    metrics: dict[str, float | None] = {
        "return_1y": cagr(nav, 1),
        "return_3y": cagr(nav, 3),
        "return_5y": cagr(nav, 5),
        "return_10y": cagr(nav, 10),
    }

    cutoff = daily_returns.index.max() - pd.DateOffset(years=LOOKBACK_YEARS)
    recent_fund = daily_returns.loc[daily_returns.index > cutoff]

    aligned = pd.DataFrame({"fund": recent_fund, "market": nifty_returns}).dropna()

    if len(aligned) < 100:
        metrics.update({"beta": None, "sharpe": None, "alpha": None})
        return metrics

    beta = aligned["fund"].cov(aligned["market"]) / aligned["market"].var()
    fund_annual_return = aligned["fund"].mean() * TRADING_DAYS_PER_YEAR
    fund_annual_vol = aligned["fund"].std() * (TRADING_DAYS_PER_YEAR ** 0.5)
    sharpe = (fund_annual_return - RISK_FREE_RATE) / fund_annual_vol

    market_annual_return = aligned["market"].mean() * TRADING_DAYS_PER_YEAR
    expected_return = RISK_FREE_RATE + beta * (market_annual_return - RISK_FREE_RATE)
    alpha = fund_annual_return - expected_return

    metrics.update({"beta": beta, "sharpe": sharpe, "alpha": alpha})
    return metrics
