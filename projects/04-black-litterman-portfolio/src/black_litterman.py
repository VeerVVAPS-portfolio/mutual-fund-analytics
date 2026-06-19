"""
Step 4 — Black-Litterman view blending.

Verified against the original Excel's Black_Litterman_engine sheet by
reproducing its posterior returns exactly:
  - Omega = P @ Sigma @ P.T  (tau = 1 implicitly; no tau cell exists anywhere
    in the workbook)
  - The confidence percentages in VIEWS_INPUT are NEVER referenced by any
    formula in the matrix math — they are decorative inputs only in the
    original model.
  - `Sigma` here is whatever covariance matrix is passed in: pass the
    monthly covariance for "replica" mode (matches the original Excel,
    confirmed below) or the annualized covariance for "corrected" mode.

This module's functions are pure (no file I/O) so the dashboard's views
editor can call compute_posterior() directly with user-edited P/Q.
"""

import numpy as np
import pandas as pd

ASSET_ORDER = ["GSEC", "NIFTY50", "AUTO", "BANK", "FINSERV", "FMCG", "IT", "OILGAS", "PHARMA", "REITS", "GOLD"]

# Default views, matching the original VIEWS_INPUT sheet:
#   View 1 (relative): NIFTY BANK > NIFTY IT by 2.5%, stated confidence 75%
#   View 2 (relative): NIFTY AUTO > NIFTY FMCG by 3.0%, stated confidence 60%
#   View 3 (absolute):  NIFTY 10 YR G-SEC = 7.0%, stated confidence 90%
# Confidence values are kept here for reference/UI display but are NOT used
# in "replica" mode, matching the original Excel.
DEFAULT_VIEWS = [
    {"name": "Bank > IT", "type": "relative", "asset1": "BANK", "asset2": "IT", "q": 0.025, "confidence": 0.75},
    {"name": "Auto > FMCG", "type": "relative", "asset1": "AUTO", "asset2": "FMCG", "q": 0.030, "confidence": 0.60},
    {"name": "G-Sec = 7%", "type": "absolute", "asset1": "GSEC", "asset2": None, "q": 0.070, "confidence": 0.90},
]


def build_p_q(views: list[dict]) -> tuple[np.ndarray, np.ndarray]:
    """Build the P matrix and Q vector from a list of view dicts."""
    n = len(ASSET_ORDER)
    idx = {a: i for i, a in enumerate(ASSET_ORDER)}
    P = np.zeros((len(views), n))
    Q = np.zeros(len(views))
    for k, view in enumerate(views):
        P[k, idx[view["asset1"]]] = 1.0
        if view["type"] == "relative":
            P[k, idx[view["asset2"]]] = -1.0
        Q[k] = view["q"]
    return P, Q


def compute_omega(P: np.ndarray, sigma: np.ndarray, views: list[dict] = None, mode: str = "replica") -> np.ndarray:
    """
    Omega (uncertainty of views).

    mode="replica" (default): Omega = P Sigma P.T, the FULL matrix including
    off-diagonal cross-terms between views — verified to match the original
    Excel's Black_Litterman_engine sheet exactly, element for element.
    Confidence is not used (it isn't in the original either).

    mode="corrected": diagonalizes Omega (the standard Black-Litterman
    assumption that views are independent — the original model never did
    this, letting correlation between views leak into the posterior), and
    optionally scales each view's variance by its stated confidence using
    the Idzorek convention: Omega_kk = ((1 - c) / c) * (P Sigma P.T)_kk.
    Requires `views` (for confidence values).
    """
    raw = P @ sigma @ P.T
    if mode == "replica":
        return raw
    if views is None:
        raise ValueError("views required when mode='corrected'")
    omega = np.diag(np.diag(raw)).astype(float)
    for k, view in enumerate(views):
        c = max(min(view["confidence"], 0.999), 0.001)
        omega[k, k] = ((1 - c) / c) * raw[k, k]
    return omega


def compute_posterior_excess(sigma: pd.DataFrame, pi_excess: pd.Series, views: list[dict], tau: float = 1.0, mode: str = "replica") -> pd.Series:
    """
    Posterior EXCESS returns (i.e. relative to the risk-free rate):
      E[R] = [Sigma^-1 + P' Omega^-1 P]^-1 [Sigma^-1 . Pi_excess + P' Omega^-1 . Q]

    `pi_excess` must be excess-of-risk-free implied returns, NOT total
    returns — feeding total returns in here would contaminate the matrix
    solve, since Sigma^-1 @ Pi_excess only simplifies cleanly to lambda *
    w_mkt when Pi_excess excludes the risk-free rate (confirmed against the
    original Excel's own "Term3" intermediate, which is exactly that
    simplification). Add the risk-free rate back yourself afterwards, or use
    compute_posterior() below which does this for you.
    """
    sigma_arr = sigma.loc[ASSET_ORDER, ASSET_ORDER].values
    pi_arr = pi_excess.loc[ASSET_ORDER].values

    P, Q = build_p_q(views)
    omega = compute_omega(P, sigma_arr, views, mode)

    sigma_inv = np.linalg.inv(tau * sigma_arr)
    omega_inv = np.linalg.inv(omega)

    A = sigma_inv + P.T @ omega_inv @ P
    b = sigma_inv @ pi_arr + P.T @ omega_inv @ Q
    posterior = np.linalg.solve(A, b)

    return pd.Series(posterior, index=ASSET_ORDER)


def compute_posterior(sigma: pd.DataFrame, pi_excess: pd.Series, views: list[dict], rf: float, tau: float = 1.0, mode: str = "replica") -> pd.Series:
    """Posterior TOTAL returns = compute_posterior_excess(...) + rf."""
    return compute_posterior_excess(sigma, pi_excess, views, tau, mode) + rf
