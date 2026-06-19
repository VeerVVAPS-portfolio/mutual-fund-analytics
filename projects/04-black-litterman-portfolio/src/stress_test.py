"""
Step 6 — stress test and Value at Risk.

Verified against the original Excel's STRESS_TEST sheet formulas directly
(not just values):
  Stressed Returns = SUMPRODUCT(weights, shocks)             -- no bug here
  95% Monthly VaR   = OPTIMIZER!C20/12 - 1.645*OPTIMIZER!C21/SQRT(12)
where OPTIMIZER!C20 is the (annualized) portfolio return and OPTIMIZER!C21
is the portfolio volatility computed from the MONTHLY covariance matrix
(see optimizer.py's docstring on the Sharpe-ratio unit mismatch). The VaR
formula divides that already-monthly volatility by sqrt(12) a second time,
making it artificially small — this is the same root-cause bug propagating
through, not a separate one.
"""

import math

import numpy as np
import pandas as pd

ASSET_ORDER = ["GSEC", "NIFTY50", "AUTO", "BANK", "FINSERV", "FMCG", "IT", "OILGAS", "PHARMA", "REITS", "GOLD"]

# Shock scenario per asset, matching the original STRESS_TEST sheet.
SHOCKS = pd.Series({
    "GSEC": 0.05,
    "NIFTY50": -0.20,
    "AUTO": -0.20,
    "BANK": -0.20,
    "FINSERV": -0.20,
    "FMCG": -0.20,
    "IT": -0.20,
    "OILGAS": -0.20,
    "PHARMA": -0.20,
    "REITS": -0.12,
    "GOLD": 0.08,
})


def stressed_return(weights: dict) -> float:
    w = pd.Series(weights)[ASSET_ORDER]
    return float(w @ SHOCKS[ASSET_ORDER])


def var_95_replica(annual_return: float, monthly_vol_from_monthly_cov: float) -> float:
    """
    Reproduces the original Excel's "95% Monthly VaR" exactly, including its
    double sqrt(12) division (the portfolio vol passed in is already a
    monthly figure, from a monthly covariance matrix — dividing by sqrt(12)
    again shrinks it further, on top of comparing it to a non-equivalent
    annualized return divided by 12).
    """
    return annual_return / 12 - 1.645 * monthly_vol_from_monthly_cov / math.sqrt(12)


def var_95_corrected(annual_return: float, annual_vol: float) -> float:
    """
    Properly annualized, internally-consistent 95% monthly VaR: convert the
    annual return to a monthly return once, and use the monthly volatility
    derived correctly from the annual vol (divide by sqrt(12) exactly once).
    """
    monthly_return = (1 + annual_return) ** (1 / 12) - 1
    monthly_vol = annual_vol / math.sqrt(12)
    return monthly_return - 1.645 * monthly_vol
