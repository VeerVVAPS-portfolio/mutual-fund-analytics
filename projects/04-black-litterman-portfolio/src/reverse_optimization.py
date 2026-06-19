"""
Step 3 — reverse optimization: derive the Black-Litterman "prior" (implied
equilibrium returns) from market-cap weights.

Functions here are pure (no file I/O for the core math) so the dashboard
can call them directly, the same way Project 1's dashboard imports
scoring.py functions for live recompute.
"""

import os

import numpy as np
import pandas as pd

DATA_PROCESSED = os.path.join(os.path.dirname(__file__), "..", "data", "processed")
STATS_CSV = os.path.join(DATA_PROCESSED, "stats.csv")
COV_MONTHLY_CSV = os.path.join(DATA_PROCESSED, "covariance_monthly.csv")
COV_ANNUAL_CSV = os.path.join(DATA_PROCESSED, "covariance_annual.csv")
MARKET_WEIGHTS_CSV = os.path.join(DATA_PROCESSED, "market_weights.csv")
IMPLIED_EXCESS_RETURNS_CSV = os.path.join(DATA_PROCESSED, "implied_excess_returns.csv")
IMPLIED_RETURNS_CSV = os.path.join(DATA_PROCESSED, "implied_returns.csv")
IMPLIED_EXCESS_RETURNS_CORRECTED_CSV = os.path.join(DATA_PROCESSED, "implied_excess_returns_corrected.csv")
IMPLIED_RETURNS_CORRECTED_CSV = os.path.join(DATA_PROCESSED, "implied_returns_corrected.csv")

ASSET_ORDER = ["GSEC", "NIFTY50", "AUTO", "BANK", "FINSERV", "FMCG", "IT", "OILGAS", "PHARMA", "REITS", "GOLD"]
EQUITY_ASSETS = ["NIFTY50", "AUTO", "BANK", "FINSERV", "FMCG", "IT", "OILGAS", "PHARMA"]

# Estimated market cap by asset CLASS (lakh-crore INR), as used in the
# original Excel's REVERSE OPTIMIZATION sheet.
MARKET_CAP_LAKH_CR = {
    "Indian Equities": 475,
    "Government Securities": 195,
    "Gold": 2.5,
    "REITs & InvITs": 5,
}

RISK_FREE_RATE = 0.056349  # RBI 365-day T-Bill, Sep 2025 (ASSUMPTIONS_MACRO sheet)


def compute_market_weights() -> pd.Series:
    """
    Market-cap weights per asset, in canonical order. The "Indian Equities"
    class weight is split EQUALLY across the 8 equity sub-indices — a
    simplifying assumption inherited from the original Excel (it does not
    use individual sector market caps), not a redesign choice.
    """
    total = sum(MARKET_CAP_LAKH_CR.values())
    class_weights = {k: v / total for k, v in MARKET_CAP_LAKH_CR.items()}

    weights = pd.Series(0.0, index=ASSET_ORDER)
    weights["GSEC"] = class_weights["Government Securities"]
    weights["REITS"] = class_weights["REITs & InvITs"]
    weights["GOLD"] = class_weights["Gold"]
    equity_weight_each = class_weights["Indian Equities"] / len(EQUITY_ASSETS)
    for asset in EQUITY_ASSETS:
        weights[asset] = equity_weight_each
    return weights


def compute_lambda(stats: pd.DataFrame, rf: float = RISK_FREE_RATE) -> float:
    """
    Risk-aversion coefficient, using NIFTY 50 as the market-portfolio proxy:
    lambda = (market annualized excess return) / (market annualized variance)
    """
    market_return = stats.loc["NIFTY50", "annual_return"]
    market_vol = stats.loc["NIFTY50", "annual_vol"]
    return (market_return - rf) / (market_vol ** 2)


def compute_implied_excess_returns(cov: pd.DataFrame, market_weights: pd.Series, lam: float) -> pd.Series:
    """
    Pi (excess) = lambda * Sigma . w_mkt.

    `cov` is passed in rather than hardcoded so the same function can run in
    "replica" mode (pass the MONTHLY covariance matrix — this is what the
    original Excel actually uses here, confirmed by reproducing its implied
    returns exactly) or "corrected" mode (pass the annualized covariance
    matrix, so the resulting Pi is on the same annual footing as `rf`).

    This stays in excess-return space deliberately: the Black-Litterman
    blending formula (see black_litterman.py) must operate on excess
    returns throughout and have the risk-free rate added back only once,
    at the very end — adding it here and feeding a "total" Pi into the
    blending formula would contaminate the matrix solve (confirmed against
    the original Excel's own intermediate "Term3" calculation, which is
    exactly lambda * w_mkt, i.e. Sigma^-1 @ Pi_excess simplified — the
    Sigma and Sigma^-1 cancel only because Pi_excess excludes rf).
    """
    sigma = cov.loc[ASSET_ORDER, ASSET_ORDER].values
    w = market_weights.loc[ASSET_ORDER].values
    pi_excess = lam * sigma.dot(w)
    return pd.Series(pi_excess, index=ASSET_ORDER)


def compute_implied_returns(cov: pd.DataFrame, market_weights: pd.Series, lam: float, rf: float = RISK_FREE_RATE) -> pd.Series:
    """Total implied return = Pi (excess) + rf. See compute_implied_excess_returns."""
    return compute_implied_excess_returns(cov, market_weights, lam) + rf


def main():
    output_files = (
        MARKET_WEIGHTS_CSV, IMPLIED_EXCESS_RETURNS_CSV, IMPLIED_RETURNS_CSV,
        IMPLIED_EXCESS_RETURNS_CORRECTED_CSV, IMPLIED_RETURNS_CORRECTED_CSV,
    )
    if all(os.path.exists(p) for p in output_files):
        print("market_weights.csv and implied_returns CSVs already exist, skipping")
        return
    print("Running reverse optimization...")
    stats = pd.read_csv(STATS_CSV, index_col=0)
    cov_monthly = pd.read_csv(COV_MONTHLY_CSV, index_col=0)
    cov_annual = pd.read_csv(COV_ANNUAL_CSV, index_col=0)

    market_weights = compute_market_weights()
    lam = compute_lambda(stats)
    # Replica: uses the monthly covariance matrix, matching the original
    # Excel exactly (verified against its REVERSE OPTIMIZATION sheet).
    pi_excess_replica = compute_implied_excess_returns(cov_monthly, market_weights, lam)
    # Corrected: uses the annualized covariance matrix, so Pi is on the same
    # annual footing as the risk-free rate it's added to.
    pi_excess_corrected = compute_implied_excess_returns(cov_annual, market_weights, lam)

    market_weights.to_csv(MARKET_WEIGHTS_CSV, header=["weight"])
    pi_excess_replica.to_csv(IMPLIED_EXCESS_RETURNS_CSV, header=["implied_excess_return"])
    (pi_excess_replica + RISK_FREE_RATE).to_csv(IMPLIED_RETURNS_CSV, header=["implied_return"])
    pi_excess_corrected.to_csv(IMPLIED_EXCESS_RETURNS_CORRECTED_CSV, header=["implied_excess_return"])
    (pi_excess_corrected + RISK_FREE_RATE).to_csv(IMPLIED_RETURNS_CORRECTED_CSV, header=["implied_return"])
    implied_returns_replica = pi_excess_replica + RISK_FREE_RATE
    implied_returns_corrected = pi_excess_corrected + RISK_FREE_RATE

    print(f"  lambda = {lam:.4f}")
    print("  replica (monthly cov):")
    print(implied_returns_replica.round(4))
    print("  corrected (annual cov):")
    print(implied_returns_corrected.round(4))


if __name__ == "__main__":
    main()
