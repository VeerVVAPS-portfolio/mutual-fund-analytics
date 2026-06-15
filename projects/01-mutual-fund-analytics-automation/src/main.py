"""
Pipeline entrypoint - runs every step in order.

Fetch steps are skipped automatically if their output already exists,
since they're the slow/cached parts (NAV history takes ~10-40 minutes
the first time). Delete the relevant files/folders to force a re-fetch.
"""

import os

from fetch_benchmark import main as fetch_benchmark
from fetch_nav_history import main as fetch_nav_history
from fetch_schemes import build_schemes_table
from metrics import main as compute_metrics
from scoring import main as score_funds
from report import main as build_report


def main():
    if not os.path.exists("data/processed/schemes.csv"):
        print("=== Step 1: Building scheme universe ===")
        schemes = build_schemes_table("data/raw/mutual_fund_data.csv")
        schemes.to_csv("data/processed/schemes.csv", index=False)
    else:
        print("=== Step 1: schemes.csv already exists, skipping ===")

    if not os.path.exists("data/raw/nifty50.csv"):
        print("\n=== Step 2: Fetching NIFTY 50 benchmark ===")
        fetch_benchmark()
    else:
        print("\n=== Step 2: nifty50.csv already exists, skipping ===")

    print("\n=== Step 3: Fetching fund NAV history (cached, resumable) ===")
    fetch_nav_history()

    print("\n=== Step 4: Computing metrics ===")
    compute_metrics()

    print("\n=== Step 5: Scoring and ranking ===")
    score_funds()

    print("\n=== Step 6: Building Excel report ===")
    build_report()


if __name__ == "__main__":
    main()
