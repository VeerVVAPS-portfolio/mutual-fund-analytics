"""
Step 5 — constrained mean-variance optimization (max Sharpe ratio).

The original Excel's weights are static Solver output, not live formulas.
Inferred constraints from those weights: no shorting, 25% cap per asset
(G-Sec and Gold both land exactly on that boundary), weights sum to 1.
SLSQP fits this naturally — bounds + one equality constraint, smooth
nonlinear ratio objective — no need for a QP/SOCP reformulation.
"""

import numpy as np
from scipy.optimize import minimize

ASSET_ORDER = ["GSEC", "NIFTY50", "AUTO", "BANK", "FINSERV", "FMCG", "IT", "OILGAS", "PHARMA", "REITS", "GOLD"]
WEIGHT_CAP = 0.25
N_RESTARTS = 20


def _portfolio_stats(weights: np.ndarray, expected_returns: np.ndarray, cov: np.ndarray, rf: float):
    port_return = weights @ expected_returns
    port_vol = float(np.sqrt(weights @ cov @ weights))
    sharpe = (port_return - rf) / port_vol if port_vol > 0 else 0.0
    return port_return, port_vol, sharpe


def optimize_portfolio(expected_returns, cov, rf: float, weight_cap: float = WEIGHT_CAP, seed: int = 42) -> dict:
    """
    Maximize Sharpe ratio subject to 0 <= w <= weight_cap, sum(w) = 1.

    `expected_returns` and `cov` should be on the SAME basis (both excess or
    both total return — and, in this codebase, both built from either the
    monthly or annual covariance matrix, matching whichever mode is in use).
    Uses multiple random restarts since the Sharpe-ratio objective can have
    more than one local optimum; keeps the best result found.
    """
    mu = np.asarray(expected_returns)
    sigma = np.asarray(cov)
    n = len(mu)

    def neg_sharpe(w):
        port_return = w @ mu
        port_vol = np.sqrt(w @ sigma @ w)
        return -(port_return - rf) / port_vol if port_vol > 0 else 0.0

    bounds = [(0.0, weight_cap)] * n
    constraints = [{"type": "eq", "fun": lambda w: np.sum(w) - 1.0}]

    rng = np.random.default_rng(seed)
    best = None
    for _ in range(N_RESTARTS):
        raw = rng.random(n)
        w0 = raw / raw.sum()
        w0 = np.clip(w0, 0, weight_cap)
        w0 = w0 / w0.sum()
        result = minimize(neg_sharpe, w0, method="SLSQP", bounds=bounds, constraints=constraints)
        if result.success and (best is None or result.fun < best.fun):
            best = result

    weights = np.clip(best.x, 0, None)
    weights = weights / weights.sum()

    port_return, port_vol, sharpe = _portfolio_stats(weights, mu, sigma, rf)
    return {
        "weights": dict(zip(ASSET_ORDER, weights)),
        "return": port_return,
        "volatility": port_vol,
        "sharpe": sharpe,
    }
