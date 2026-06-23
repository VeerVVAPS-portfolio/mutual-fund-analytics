# Goal-Based Wealth Planner

Started as a generalized goal-based SIP calculator and grew into a fuller wealth-management tool: goal funding, affordability sequencing, insurance/emergency-fund adequacy, and debt load — the things an actual financial consultant checks before getting excited about goals. Built from a Bajaj Capital internship deliverable (`Redesigned_portfolio.xlsx` — "Portfolio", "Calculation & Assumption", "Projection" sheets), a one-off plan for a single fictional client ("Mr. Peter") with three goals: education, marriage, and a house.

## The Gap in the Original Model

The original Excel computes each goal's inflation-adjusted future value correctly:
```
Future Value = Present Value × (1 + inflation)^years
```
But only the **House** goal actually *solves* for the SIP needed to hit that target (via a tuned step-up SIP, landing within ~0.1% of its ₹1.51 Cr target). The **Education** and **Marriage** goals never solve anything — their monthly SIP amounts (₹8,000 and ₹3,500) are hardcoded guesses, picked by summing four pre-selected mutual fund schemes. Running those guessed amounts back through the same annuity formula shows both goals **fall short**:

| Goal | Future Value Required | Original SIP | Maturity Value of Original SIP | Shortfall |
|---|---|---|---|---|
| Education | ₹59,04,327 | ₹8,000/mo | ₹55,12,839 | ~6.6% short |
| Marriage | ₹1,08,54,865 | ₹3,500/mo | ₹1,00,26,584 | ~7.6% short |
| House | ₹1,51,12,475 | step-up SIP | ₹1,51,31,650 | on target |

This tool's core change: **every goal is solved for, never guessed.** Given a target and a horizon, it always derives the exact SIP required.

## Design

**Core math (`src/goal_calculator.py`)**
- `future_value_required` — same inflation-adjustment formula as the original.
- `required_fixed_sip` — solves the future-value-of-an-annuity-due formula directly for the monthly payment: `FV = PMT × ((1+r)ⁿ − 1) × (1+r) / r`.
- `required_stepup_sip` — for goals with an annual step-up (like House), simulates month-by-month contribution growth and solves for the starting SIP by linear scaling (future value is linear in the starting SIP amount, so one simulation run plus a scale factor replaces a numerical solver). This is also more precise than the original's approach, which compounded annual lump sums at the yearly rate instead of simulating monthly compounding.

**Generalization** — no hardcoded goals. The dashboard lets you add any number of goals (name, target amount, horizon, inflation rate, expected return, optional step-up %), with editable templates for Education / Marriage / House / Custom.

**Affordability check (`src/cashflow_projection.py`)** — generalizes the original "Projection" sheet's salary/expense table: projects disposable income (salary − expenses − fixed obligations) year over year against the total required SIP outflow, and flags any year where it falls short. The original never checked this.

**Fund picks (`src/fund_recommender.py`)** — for goals with a 7+ year horizon, surfaces top-ranked equity funds from [Project 1](../01-mutual-fund-analytics-automation)'s `scored_funds.csv`. Shorter goals get a plain caution instead of a fabricated recommendation, since Project 1 only scores equity schemes.

**Funding sequencer (`src/funding_sequencer.py`)** — when income can't fund every goal's SIP starting today, funds them strictly in priority order (Must-have → Good-to-have → Dream goal, nearest deadline as tie-break). A deferred goal's SIP is recomputed for its now-shorter remaining horizon, not just delayed at the original number. Goals that never become affordable within the horizon are flagged at-risk, not dropped silently.

**Advisor's Note (`src/advisory.py`)** — turns the staggered plan into a written, consultant-style note: a headline verdict, the quantified cost of deferring each goal, and explicit risk flags (e.g. assumed salary growth not outpacing assumed expense growth). Deliberately rule-based rather than LLM-generated, so every sentence traces back to a specific computed number.

**Protection adequacy (`src/protection.py`)** — life insurance need via a DIME-style needs-based method (outstanding loan balances + each goal's lump-sum equivalent + income-replacement years for dependents, minus existing cover); health insurance via Indian city-tier sum-insured benchmarks, scaled for family size (interpolated for solo/small families rather than handing everyone the family-of-4 figure); emergency fund via months-of-expenses guidance scaled by dependents; and FOIR (Fixed Obligation to Income Ratio) using the same ≤40%-safe / ≤55%-ceiling thresholds Indian banks use for loan eligibility. Outstanding loan principal is back-calculated from EMI + rate + remaining tenure via the standard amortization formula, so the user never has to know a number they don't have handy.

**PDF report (`src/report_pdf.py`)** — one downloadable wealth plan combining the advisor's note, goal plan, funding sequence, protection summary, and loan schedule. Built with reportlab (pure-Python, no system dependencies) using a bundled Noto Sans font (`assets/NotoSans.ttf`) — reportlab's built-in fonts don't include the ₹ glyph, so this avoids the report silently printing missing-glyph boxes wherever a currency value appears.

## Assumption Note

The original Excel assumed 16–17% annual equity returns per goal. This rebuild keeps that as an *editable default* but pre-fills a more conservative 12% — 16–17% is optimistic for long-horizon SIP planning. Adjust per goal in the dashboard; the README and UI both disclose this is a planning estimate, not a guarantee.

## Dashboard

```
cd projects/06-goal-based-sip-planner
streamlit run dashboard/app.py
```

Wizard flow: add/edit goals → income, expenses & loans/EMIs → protection (dependents, existing insurance, city tier) → results (Affordability, Protection, Goal Breakdown, Fund Picks) → download the full plan as a PDF.

No external data fetching — this project is pure computation, so there's no pipeline `main.py` like Project 1; the dashboard calls the calculator modules directly.

## Files

```
src/
  goal_calculator.py      # FV, fixed/step-up SIP solvers, year-by-year schedules
  cashflow_projection.py  # salary/expense affordability projection
  funding_sequencer.py    # priority-ordered staggered funding plan
  advisory.py             # consultant-style written note
  protection.py           # life/health/emergency-fund adequacy + FOIR
  fund_recommender.py     # pulls top equity funds from Project 1
  report_pdf.py           # PDF report (reportlab)
dashboard/
  app.py                  # Streamlit wizard
assets/
  NotoSans.ttf            # bundled font so the PDF renders ₹ correctly
```
