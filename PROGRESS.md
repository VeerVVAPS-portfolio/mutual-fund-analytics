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
- **Project 1 scoring redesign (confirmed):** Normalize AUM/3Y/5Y/10Y/Beta/Sharpe to 0-100 per category, combine via **user-configurable weights** into a composite score, rank top picks per category. Documented in `projects/01-mutual-fund-analytics-automation/README.md`.
- **New project discovered:** "Portfolio"/"Calculation & Assumption"/"Projection" sheets in the same Excel = a separate goal-planning/SIP calculator tool → added as **Project #6** in global `PROJECTS.md`.

## Current Status: Project 1 — Mutual Fund Analytics Automation
**Status:** Design finalized, scaffold created, no code written yet.

**Open/unresolved:**
- AUM data source for ~2000 schemes at scale not yet confirmed (AMFI's NAVAll.txt doesn't include AUM directly — need to find/research a scheme-wise AUM source).
- MoneyControl star rating can't be replicated at scale (proprietary) — likely need an objective substitute (e.g., consistency of returns) for any "quality" filter.

## Next Step
Start `src/fetch_schemes.py`: pull AMFI `NAVAll.txt`, parse scheme list + category classification (Large/Mid/Small Cap, ELSS), teaching pandas basics (reading data, filtering, string parsing) along the way. Then tackle the AUM data source question.
