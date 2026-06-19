"""
Pipeline entrypoint - runs every step in order.

Each step is skipped automatically if its cached output already exists.
Delete the relevant files in data/processed/ to force a recompute.

Runs the full chain in BOTH modes:
  - "replica":   uses the monthly covariance matrix throughout, exactly
                 matching the original Excel's published numbers.
  - "corrected": uses the annualized covariance matrix throughout, so
                 returns/volatility/Sharpe/VaR are all on consistent units.
"""

import os

import pandas as pd

import black_litterman
import clean_returns
import extract_excel
import optimizer
import report
import reverse_optimization
import stats
import stress_test

DATA_PROCESSED = os.path.join(os.path.dirname(__file__), "..", "data", "processed")
RISK_FREE_RATE = reverse_optimization.RISK_FREE_RATE


def run_mode(mode: str, cov_monthly: pd.DataFrame, cov_annual: pd.DataFrame) -> dict:
    cov = cov_monthly if mode == "replica" else cov_annual

    market_weights = reverse_optimization.compute_market_weights()
    asset_stats = pd.read_csv(os.path.join(DATA_PROCESSED, "stats.csv"), index_col=0)
    lam = reverse_optimization.compute_lambda(asset_stats)
    pi_excess = reverse_optimization.compute_implied_excess_returns(cov, market_weights, lam)

    posterior = black_litterman.compute_posterior(
        cov, pi_excess, black_litterman.DEFAULT_VIEWS, rf=RISK_FREE_RATE, mode=mode
    )

    opt_result = optimizer.optimize_portfolio(
        posterior.loc[optimizer.ASSET_ORDER].values,
        cov.loc[optimizer.ASSET_ORDER, optimizer.ASSET_ORDER].values,
        rf=RISK_FREE_RATE,
    )

    return {"posterior": posterior, "optimizer": opt_result}


def main():
    print("=== Step 0: Extracting raw data from Excel ===")
    extract_excel.main()

    print("\n=== Step 1: Cleaning returns ===")
    clean_returns.main()

    print("\n=== Step 2: Computing statistics & covariance ===")
    stats.main()

    print("\n=== Step 3: Reverse optimization ===")
    reverse_optimization.main()

    cov_monthly = pd.read_csv(os.path.join(DATA_PROCESSED, "covariance_monthly.csv"), index_col=0)
    cov_annual = pd.read_csv(os.path.join(DATA_PROCESSED, "covariance_annual.csv"), index_col=0)

    print("\n=== Step 4-5: Black-Litterman blending + optimization (replica mode) ===")
    replica = run_mode("replica", cov_monthly, cov_annual)

    print("\n=== Step 4-5: Black-Litterman blending + optimization (corrected mode) ===")
    corrected = run_mode("corrected", cov_monthly, cov_annual)

    print("\n=== Step 6: Stress test & VaR ===")
    stressed_return = stress_test.stressed_return(replica["optimizer"]["weights"])
    var_replica = stress_test.var_95_replica(replica["optimizer"]["return"], replica["optimizer"]["volatility"])
    var_corrected = stress_test.var_95_corrected(corrected["optimizer"]["return"], corrected["optimizer"]["volatility"])

    results = {
        "posterior_replica": replica["posterior"],
        "posterior_corrected": corrected["posterior"],
        "optimizer_replica": replica["optimizer"],
        "optimizer_corrected": corrected["optimizer"],
        "stressed_return": stressed_return,
        "var_replica": var_replica,
        "var_corrected": var_corrected,
    }

    print("\n=== Step 7: Building Excel report ===")
    report.main(results)

    print("\nReplica  -> return {:.4f}, vol {:.4f}, sharpe {:.4f}".format(
        replica["optimizer"]["return"], replica["optimizer"]["volatility"], replica["optimizer"]["sharpe"]))
    print("Corrected-> return {:.4f}, vol {:.4f}, sharpe {:.4f}".format(
        corrected["optimizer"]["return"], corrected["optimizer"]["volatility"], corrected["optimizer"]["sharpe"]))


if __name__ == "__main__":
    main()
