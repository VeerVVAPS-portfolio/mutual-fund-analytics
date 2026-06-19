"""
Step 1 — turn the raw daily price CSVs into monthly returns.

Canonical asset order used everywhere downstream (matches the P-matrix
column order in the original Black-Litterman engine sheet):
GSEC, NIFTY50, AUTO, BANK, FINSERV, FMCG, IT, OILGAS, PHARMA, REITS, GOLD
"""

import os

import pandas as pd

DATA_RAW = os.path.join(os.path.dirname(__file__), "..", "data", "raw")
DATA_PROCESSED = os.path.join(os.path.dirname(__file__), "..", "data", "processed")
MONTHLY_RETURNS_CSV = os.path.join(DATA_PROCESSED, "monthly_returns.csv")

NAME_TO_TICKER = {
    "NIFTY 10 YR BENCHMARK G-SEC": "GSEC",
    "NIFTY 50": "NIFTY50",
    "NIFTY AUTO": "AUTO",
    "NIFTY BANK": "BANK",
    "NIFTY FINANCIAL SERVICES": "FINSERV",
    "NIFTY FMCG": "FMCG",
    "NIFTY IT": "IT",
    "NIFTY OIL & GAS": "OILGAS",
    "NIFTY PHARMA": "PHARMA",
    "NIFTY REITS & INVITS": "REITS",
}

ASSET_ORDER = ["GSEC", "NIFTY50", "AUTO", "BANK", "FINSERV", "FMCG", "IT", "OILGAS", "PHARMA", "REITS", "GOLD"]


def build_monthly_returns():
    eq_debt = pd.read_csv(os.path.join(DATA_RAW, "raw_eq_debt.csv"), parse_dates=["Date"])
    eq_debt["Ticker"] = eq_debt["Index Name"].map(NAME_TO_TICKER)
    wide_eq = eq_debt.pivot_table(index="Date", columns="Ticker", values="Close", aggfunc="last")

    gold = pd.read_csv(os.path.join(DATA_RAW, "raw_gold.csv"), parse_dates=["Date"])
    gold = gold.set_index("Date")[["Close"]].rename(columns={"Close": "GOLD"})
    # GOLDBEES did a 1:100 unit split effective 2019-12-19 (price drops from
    # ~3360 to ~33.55 overnight with no corresponding market move). Scale the
    # post-split leg back up by 100x so the price series is continuous —
    # matches the adjustment already baked into the original Excel's
    # CLEANED_GOLD sheet.
    gold.loc[gold.index >= "2019-12-19", "GOLD"] *= 100

    prices = wide_eq.join(gold, how="outer").sort_index()

    # Resample to month-end last available close, then compute simple monthly
    # returns. REITS has no listed history before mid-2019, so its early
    # months are left as NaN rather than dropped or filled — this preserves
    # pandas' pairwise-NaN-aware covariance behaviour later, matching how the
    # original Excel's correlation matrix has plausible non-zero values for
    # REITS despite its shorter history.
    monthly_prices = prices.resample("ME").last()
    monthly_returns = monthly_prices.pct_change()
    monthly_returns = monthly_returns[ASSET_ORDER]
    monthly_returns = monthly_returns.iloc[1:]  # drop the leading all-NaN row from pct_change

    monthly_returns.to_csv(MONTHLY_RETURNS_CSV)
    return monthly_returns


def main():
    if os.path.exists(MONTHLY_RETURNS_CSV):
        print("monthly_returns.csv already exists, skipping")
        return
    print("Building monthly returns from raw price data...")
    df = build_monthly_returns()
    print(f"  {len(df)} months, {df.shape[1]} assets, REITS non-null from {df['REITS'].first_valid_index().date()}")


if __name__ == "__main__":
    main()
