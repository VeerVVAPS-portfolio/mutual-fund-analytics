# Mutual Fund Analytics Automation

Automates the mutual fund screening & ranking process Veer originally did manually during the Bajaj Capital internship (sourcing data from MoneyControl, filtering, and scoring funds by hand in Excel).

## Original Manual Process (`Redesigned_portfolio.xlsx` → "Scheme Recommendation" sheet)

- **Universe:** Equity mutual funds across 4 categories — Large Cap, Mid Cap, Small Cap, ELSS
- **Pre-filters (applied manually):** AUM > ₹10,000 Cr, MoneyControl star rating ≥ 4
- **Score:** `AUM × 3Y return × 5Y return × 10Y return` (Beta and Sharpe Ratio were captured but not actually used in the score)
- **Ranking:** `RANK.EQ` within each category — top-ranked fund = recommendation

## Automated, Improved Version (this project)

**Scope:** All AMFI-registered equity mutual fund schemes (~2000), not just a hand-picked shortlist.

**Scoring methodology — Weighted Composite Score:**
1. For each category, compute for every scheme: AUM, 1Y/3Y/5Y returns (CAGR), Beta (vs NIFTY 50), Sharpe Ratio.
2. **Normalize** each metric to a 0–100 scale within its category (so AUM in crores and returns in % are comparable, and one metric can't dominate by sheer magnitude — this was the main flaw in the original `AUM × ... ` product formula).
3. Beta is normalized so **lower volatility scores higher** (configurable — some users may prefer higher beta for aggressive growth).
4. Combine normalized metrics into a single score using **user-configurable weights** (e.g., `AUM: 15%, 3Y: 25%, 5Y: 20%, Beta: 15%, Sharpe: 25%`) — this delivers on the "give weight based on preference" idea from the original sheet, which wasn't actually implemented.
5. Rank within each category; output top N per category plus full ranked list.

## Data Sources
- **Scheme list & categories:** AMFI `NAVAll.txt`
- **Historical NAV (for returns/Beta/Sharpe):** `mfapi.in` (free, mirrors AMFI data)
- **Benchmark (NIFTY 50, for Beta):** `yfinance` (`^NSEI`)
- **AUM:** TBD — researching a scheme-wise source (AMFI average AUM reports)

## Pipeline
```
src/
  fetch_schemes.py     # scheme list + category classification
  fetch_nav_history.py # historical NAV per scheme, cached to data/raw/
  metrics.py            # returns, Beta, Sharpe Ratio
  scoring.py            # normalization + weighted composite score + ranking
  report.py             # multi-sheet Excel output
  main.py               # pipeline entrypoint
```

## Status
In progress — see [PROJECTS.md](C:\Users\VEER\.claude\PROJECTS.md) for overall tracker.
