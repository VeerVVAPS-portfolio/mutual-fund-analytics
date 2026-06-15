# Progress Log — AmEx GenAI Portfolio Build

Running log so work can resume after `/clear`. Update this at the end of each session / major step. See also the global `ABOUT_VEER.md` and `PROJECTS.md` (`C:\Users\VEER\.claude\`) for broader context.

## Overall Plan
Build/improve the 5 projects on Veer's AmEx-tailored resume, one at a time, with a learning-focused approach (explain pandas/APIs/libraries as we go). Then build a portfolio website from both resumes + finished projects.

Order: **#1 Mutual Fund Analytics Automation → #2 AI Asset Allocation Tool → #3 LLM Doc Summarizer → #4 Black-Litterman Portfolio → #5 WACC Analysis → #6 Goal Planning/SIP Tool (newly discovered) → Portfolio website**

## Workspace
- Repo initialized at `Portfolio_project/` (git, local identity set to Veer / singh02sorav@gmail.com).
- `projects/01-mutual-fund-analytics-automation/` scaffolded: `data/raw/`, `data/processed/`, `src/`, `output/`, `README.md`.

## Decisions Made So Far
- **Veer's skill level:** Python basics solid; new to pandas, APIs, library usage → explain concepts as we build.
- **Project 1 data scope:** Cover all ~2000 AMFI equity scheme universe (not just a small subset).
- **Project 1 source material:** `Redesigned_portfolio.xlsx` → "Scheme Recommendation" sheet = original manual methodology (AUM x 3Y x 5Y x 10Y, RANK.EQ, pre-filtered to AUM>10,000cr & MC rating>=4).
- **Project 1 scoring redesign (FINAL, confirmed 2026-06-15):** Two-stage design. Stage 1 = eligibility filters (AUM >= threshold, track record >= 5yrs, not scored). Stage 2 = composite score from percentile ranks of Sharpe Ratio, Jensen's Alpha (CAPM-based vs NIFTY), and Consistency (rolling 3yr win-rate vs category avg), combined via user-configurable weights. Avoids double-counting return/risk across metrics. Documented in `projects/01-mutual-fund-analytics-automation/README.md`.
- **Working style preference (confirmed 2026-06-15):** For design/methodology decisions, always do Listen -> Understand -> Analyze -> Teach -> Suggest before proceeding. Don't just replicate Veer's initial idea or jump to "here's the plan" — critique first, explain tradeoffs, then recommend. Saved to global `ABOUT_VEER.md`.
- **New project discovered:** "Portfolio"/"Calculation & Assumption"/"Projection" sheets in the same Excel = a separate goal-planning/SIP calculator tool → added as **Project #6** in global `PROJECTS.md`.

## Current Status: Project 1 — Mutual Fund Analytics Automation
**Status:** `fetch_schemes.py` done and run successfully.

- **Category scope expanded from 4 -> 10** diversified equity categories (Large Cap, Large & Mid Cap, Mid Cap, Small Cap, Multi Cap, Flexi Cap, Value, Focused, Dividend Yield, ELSS) — confirmed 2026-06-15, sectoral/debt/hybrid/index deferred to later.
- **AUM data source resolved:** `InertExpert2911/Mutual_Fund_Data` GitHub CSV (AMFI-derived, per-plan Average_AUM_Cr) — downloaded to `data/raw/mutual_fund_data.csv` (gitignored).
- `src/fetch_schemes.py` builds one row per fund: sums AUM across all plans, picks Direct Growth as reference plan (Regular Growth fallback). Result: **184 of 186 funds** got a usable reference plan -> `data/processed/schemes.csv`. The 2 skipped (Samco Mid Cap, Samco Small Cap) have non-standard plan names with no "Growth" keyword and are tiny/new funds — left out for now, low impact.
- Removed `src/explore_data.py` (exploration scratch file, no longer needed).
- README.md updated to document the 10-category scope.

- `src/fetch_nav_history.py` done and run successfully: all **184/184 funds** cached to `data/raw/nav_history/{scheme_code}.json` (full daily NAV history per fund, e.g. 2,951 records spanning 2014-2026 for a typical fund). API (`mfapi.in`) is slow (~13s/request for full history) but caching makes this a one-time cost; script is resumable (skips already-cached files). First run: 167/184 succeeded, 17 timed out at 15s; retried with 30s timeout -> 0 failures.

**Open/unresolved:**
- Risk-free rate assumption for Sharpe/Alpha (CAPM) — asked Veer to confirm hardcoding ~7% (India 10Y G-sec proxy); awaiting answer before starting `metrics.py`.

## Next Step
Once risk-free rate is confirmed, build `src/metrics.py`: from cached NAV history, compute daily returns (`pct_change`), CAGR (1Y/3Y/5Y/10Y), Beta vs NIFTY 50 (via `yfinance` `^NSEI`), Sharpe Ratio, Jensen's Alpha (CAPM), and the Consistency metric (rolling 3yr win-rate vs category average).
