# Black-Litterman Portfolio Construction

[![Live Dashboard](https://img.shields.io/badge/Live%20Dashboard-Streamlit-FF4B4B?logo=streamlit)](https://mutual-fund-analytics-drxhyomvnbchzesuoxh2ro.streamlit.app/)

Rebuilds an Excel-based Black-Litterman portfolio model — originally built for a ₹100 Cr multi-asset investment-club case competition — as a reproducible Python pipeline and interactive dashboard. The original Excel's price history is the data source (extracted from its embedded raw sheets, not refetched), so the numbers below trace directly back to that source.

## The Problem with Naive Portfolio Optimization

Feeding raw historical returns straight into a mean-variance optimizer is notoriously unstable — small changes in return estimates can flip the recommended weights to extreme, concentrated bets. Black-Litterman fixes this by blending two sources of expected return instead of relying on history alone:

1. **Reverse optimization** — back out the returns implied by current market-cap weights (the "market's view"), using each asset's contribution to portfolio risk
2. **Investor views** — explicit opinions (e.g. "Bank will beat IT by 2.5%"), blended in via Bayesian updating
3. **Constrained optimization** — find the max-Sharpe allocation subject to no-shorting and a per-asset weight cap

## Methodology

```
Monthly returns (11 assets, 2015–2025)
        │
        ├─→ Reverse optimization: market-cap weights → λ (risk aversion) → implied returns (Π)
        │
        ├─→ Investor views: P-matrix + Q-targets → Ω (uncertainty) → Black-Litterman posterior returns
        │
        ├─→ Constrained mean-variance optimizer (SLSQP, max Sharpe, 0 ≤ w ≤ 25%, Σw = 1)
        │
        └─→ Stress test (-20% equity shock) + 95% monthly VaR
```

**Assets:** NIFTY 10Y G-Sec, NIFTY 50, Auto, Bank, Financial Services, FMCG, IT, Oil & Gas, Pharma, REITs, Gold.

**Default views:** Bank > IT by 2.5% (conf. 75%), Auto > FMCG by 3.0% (conf. 60%), G-Sec absolute target 7.0% (conf. 90%) — all editable live in the dashboard.

## A Bug Found While Rebuilding It

Reverse-engineering every formula (not just the output values) surfaced something the original spreadsheet got wrong: **it never built a separate annualized covariance matrix.** The same *monthly* covariance matrix is used throughout reverse optimization, Black-Litterman blending, and the optimizer — while annualized returns and the annual risk-free rate are combined into the same formulas at the final step. The clearest symptom: **Portfolio Volatility is computed from the monthly covariance matrix while Portfolio Return is annualized**, so the published Sharpe Ratio divides an annual number by a monthly one. The VaR formula compounds the same error by dividing an already-monthly volatility by `sqrt(12)` a second time.

This pipeline reproduces the original numbers exactly (**Replica** mode) for traceability with the resume/slide-deck claims, and also runs the identical math with the annualized covariance matrix used consistently throughout (**Corrected** mode), so return/volatility/Sharpe/VaR are all on the same time basis. Toggling between the two in the dashboard changes both the resulting allocation and the risk-adjusted return — not just the headline Sharpe number.

| Metric | Replica (matches Excel) | Corrected |
|---|---|---|
| Portfolio Return | 9.67% | 13.78% |
| Portfolio Volatility | 2.47%¹ | 8.25% |
| Sharpe Ratio | 1.64 | 0.99 |
| Stressed Return (-20% equity shock) | -6.59% | -6.75% |
| 95% Monthly VaR | -0.37% | -2.84% |

¹ *Computed from the monthly covariance matrix, not annualized — this is the bug, reproduced faithfully for parity with the original.*

## Other Inherited Assumptions

- **Equal-split equity market weights** — the 70.1% "Indian Equities" market-cap bucket is split equally across the 8 equity sub-indices, not by each sector's individual market cap.
- **Estimated market caps** — asset-class market caps (Equities ₹475, G-Secs ₹195, Gold ₹2.5, REITs ₹5, all lakh-crore) are analyst estimates from the original model, not live AUM data.
- **25% per-asset weight cap** — inferred from the Solver output (G-Sec and Gold both land exactly on 25%), not stated explicitly in the workbook. Confirmed by reproducing the exact same weights with this constraint via `scipy.optimize`.
- **Covariance window mismatch** — per-asset return/volatility use the full 2015–2025 history, but the covariance matrix uses only the period REITs has listed data (Aug 2019 onward), with population covariance — another inherited inconsistency, not a redesign choice.
- **Omega uses view cross-terms** — standard Black-Litterman assumes views are uncorrelated (diagonal Ω). The original model's Ω is the full `P·Σ·Pᵗ` including off-diagonal terms between views. Replicated exactly in Replica mode; Corrected mode diagonalizes Ω and scales it by stated view confidence (the original confidence inputs were never actually used in any formula).
- **GOLDBEES 1:100 unit split (2019-12-19)** — the raw ETF price data has a corporate-action discontinuity; the pipeline scales the pre-split leg to keep the price series continuous, matching the adjustment already present in the original Excel's cleaned data.

## Dashboard

- Sidebar toggle between Replica and Corrected mode
- Sliders for all 3 investor views (target spread + confidence) — every change recomputes the Black-Litterman blend, optimal allocation, and stress test live, in-memory
- Posterior-returns bar chart, allocation donut, metric cards, and a stress-test contribution table
- "Assumptions & limitations" expander with the same caveats listed above

## Pipeline

```
src/
  extract_excel.py        # Step 0: dumps the original Excel's raw price sheets to CSV
  clean_returns.py        # raw CSVs -> monthly returns (handles the Gold split adjustment)
  stats.py                 # per-asset return/vol + covariance/correlation matrices
  reverse_optimization.py  # market weights, lambda, implied returns (Pi)
  black_litterman.py       # views (P, Q), Omega, posterior blending
  optimizer.py             # SLSQP constrained max-Sharpe optimization
  stress_test.py           # shock scenarios + VaR (replica and corrected)
  report.py                # writes output/black_litterman_report.xlsx
  main.py                  # pipeline entrypoint — runs all steps, both modes
```

Run everything with one command (from the project root):
```
python src/main.py
```
Each step is skipped automatically if its cached output already exists.

## Run the Dashboard Locally

```
pip install -r requirements.txt
streamlit run dashboard/app.py
```

## Results Summary

A ₹100 Cr portfolio anchored by 25% debt (G-Sec) and 25% gold for stability, with the remaining ~50% tilted into the sectors the model favored on a risk-adjusted basis — Pharma (~20.5%) and FMCG (~17.0%) — and explicit 0% in Auto, Bank, and IT, where the model judged the volatility wasn't compensated by sufficient expected return.

---

*Methodology, financial parameters, and domain logic designed by Veer Pratap Singh, originally for an investment-club case competition. Reverse-engineered and rebuilt in Python, including identification of the original model's Sharpe/VaR unit-mismatch bug, with Claude Code (AI-assisted development).*
