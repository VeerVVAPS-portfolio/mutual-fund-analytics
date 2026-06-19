"""
Step 2 — per-asset return/risk statistics, covariance, and correlation.

Two conventions below were verified against the original Excel's
CALCULATIONS sheet by reproducing its numbers exactly, not assumed:

  - Per-asset mean/vol use the FULL 120-month history (2015-10 to 2025-09).
    Return is geometrically compounded: (1 + monthly_mean) ** 12 - 1.
    Volatility is simple sqrt-time scaling: monthly_std * sqrt(12).

  - The covariance and correlation MATRICES use a shorter, truncated
    window: 2019-08 onward only (REITS's first month of listed data),
    with population covariance (ddof=0) rather than the sample covariance
    used elsewhere. This means the original model mixes two different
    lookback windows — full history for individual asset stats, but a
    REITS-availability-constrained window for the covariance matrix that
    feeds the reverse optimization, BL blending, and the optimizer. This
    is an inherited inconsistency from the original Excel, not a deliberate
    design choice; it's replicated here for parity and called out in the
    README.
"""

import os

import pandas as pd

DATA_PROCESSED = os.path.join(os.path.dirname(__file__), "..", "data", "processed")
MONTHLY_RETURNS_CSV = os.path.join(DATA_PROCESSED, "monthly_returns.csv")
STATS_CSV = os.path.join(DATA_PROCESSED, "stats.csv")
COV_MONTHLY_CSV = os.path.join(DATA_PROCESSED, "covariance_monthly.csv")
COV_ANNUAL_CSV = os.path.join(DATA_PROCESSED, "covariance_annual.csv")
CORR_CSV = os.path.join(DATA_PROCESSED, "correlation.csv")

# First month REITS has listed data — the covariance/correlation matrices
# are computed over this truncated window, matching the original Excel.
COV_WINDOW_START = "2019-08-31"


def compute_stats(monthly_returns: pd.DataFrame) -> pd.DataFrame:
    monthly_mean = monthly_returns.mean()
    monthly_std = monthly_returns.std()
    annual_return = (1 + monthly_mean) ** 12 - 1
    annual_vol = monthly_std * (12 ** 0.5)
    return pd.DataFrame({
        "monthly_mean": monthly_mean,
        "annual_return": annual_return,
        "monthly_vol": monthly_std,
        "annual_vol": annual_vol,
    })


def main():
    if all(os.path.exists(p) for p in (STATS_CSV, COV_MONTHLY_CSV, COV_ANNUAL_CSV, CORR_CSV)):
        print("stats/covariance/correlation already exist, skipping")
        return
    print("Computing return/risk statistics and covariance matrix...")
    monthly_returns = pd.read_csv(MONTHLY_RETURNS_CSV, index_col=0, parse_dates=True)

    stats = compute_stats(monthly_returns)
    stats.to_csv(STATS_CSV)

    cov_window = monthly_returns.loc[monthly_returns.index >= COV_WINDOW_START]
    cov_monthly = cov_window.cov(ddof=0)
    cov_monthly.to_csv(COV_MONTHLY_CSV)

    cov_annual = cov_monthly * 12
    cov_annual.to_csv(COV_ANNUAL_CSV)

    corr = cov_window.corr()
    corr.to_csv(CORR_CSV)

    print(stats.round(4))


if __name__ == "__main__":
    main()
