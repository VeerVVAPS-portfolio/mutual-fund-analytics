# Technical Architect — Product Council Critique
## Project: PROFILE → PICK → SIZE Unified Wealth Platform
**Date:** 2026-06-30  
**Lens:** Integration Architecture / Migration Risk

---

## 1. VERDICT

**Build a unified Streamlit multipage app that promotes the existing `src/` modules to a shared internal library — do not rebuild, do not reach for React/FastAPI.**

Why: the three apps share identical CSS variables, the same PLOTLY_BASE pattern, the same Bootstrap Icons CDN import, and the same dark design system. That is not a coincidence — the groundwork for a unified app was already laid project by project. The real work is wiring session state across stages and making `scored_funds.csv` a first-class dependency rather than a silent relative-path read. React + FastAPI is architecturally cleaner but Veer cannot maintain it when things break at 11 PM before an interview — that tradeoff does not close in favour of React at this skill level and deployment constraint.

---

## 2. TARGET ARCHITECTURE

### 2a. Module / Package Layout

The single most important structural decision: promote the three `src/` trees into a shared importable package rather than duplicating or rewriting them.

Proposed layout:

```
projects/08-unified-wealth-platform/
├── shared/
│   ├── __init__.py
│   ├── risk_profiler.py        # copy-imported from P2 src/ — pure functions, zero UI deps
│   ├── allocation_engine.py    # copy-imported from P2 src/
│   ├── prompts.py              # copy-imported from P2 src/
│   ├── scoring.py              # copy-imported from P1 src/ (apply_eligibility_filter, compute_composite_score)
│   ├── goal_calculator.py      # copy-imported from P6 src/
│   ├── cashflow_projection.py  # copy-imported from P6 src/
│   ├── fund_recommender.py     # REWRITTEN — unified version that handles both P2 and P6 call sites
│   ├── protection.py           # copy-imported from P6 src/
│   ├── formatting.py           # copy-imported from P6 src/
│   └── data_store.py           # NEW — handles scored_funds.csv lifecycle (see 2c)
├── pages/
│   ├── 1_Profile.py            # risk questionnaire (P2 wizard, steps 1–5 + income)
│   ├── 2_Allocation.py         # LLM allocation results + fund category picks (P2 results screen)
│   ├── 3_Goals.py              # goal builder + income/loans/protection (P6 wizard, steps 1–3)
│   └── 4_Plan.py               # full results: affordability + breakdown + fund picks + PDF (P6 results)
├── dashboard/
│   └── app.py                  # entry point: st.set_page_config once, CSS once, global sidebar
├── data/
│   └── scored_funds.csv        # committed seed file (see 2c)
└── requirements.txt            # per-project docs; root requirements.txt carries the real union
```

**"Copy-imported" means:** literally copy the file into `shared/` at project creation and adapt the one import line that sets `SCORED_FUNDS_PATH`. Do not use relative `../01-mutual-fund-analytics-automation/...` paths — they are fragile and will break the moment the unified app deploys to Streamlit Cloud because it runs from the repo root, not a project subdirectory. The source-of-truth for each module stays in its original project; `shared/` is the integration copy.

**Why not symlinks:** Streamlit Cloud clones the repo and does not follow symlinks reliably across Windows/Linux dev environments. Copy is the safe call.

### 2b. State Passing Between Stages

Current situation: each app uses its own `st.session_state` with no shared schema. P2's result screen produces `risk_label`, `allocation`, and `monthly_sip_suggestion`. P6's goal builder consumes nothing from P2 — the user currently re-enters income manually, which is a design gap: P2 already collected `monthly_income` in its Step 6 but throws it away when the user navigates to P6.

**Target: a flat session state schema defined once and shared across all pages.**

Define this in `dashboard/app.py` as a single initialisation block:

```python
# shared/state_schema.py
DEFAULT_STATE = {
    # Stage 1 (PROFILE) outputs
    "profile_answers": {},      # age/horizon/goal/reaction/debt
    "monthly_income": 0,
    "risk_score": None,
    "risk_label": None,
    "allocation": None,         # {"equity": 60, "debt": 25, "gold": 10, "alternatives": 5}
    "allocation_reasoning": {},
    "allocation_is_demo": True,
    # Stage 2 (GOALS) outputs
    "goals": [],
    "loans": [],
    "income_inputs": {},
    "protection_inputs": {},
    # Cross-stage convenience
    "profile_complete": False,
    "goals_complete": False,
}
```

Streamlit multipage apps (`pages/`) share `st.session_state` natively across pages within a single Streamlit process — this is the key fact that makes the multipage approach work here without any backend session store. The user's `monthly_income` from PROFILE automatically populates the default in GOALS' income step. The `allocation` dict tells GOALS which fund categories to surface without any re-query.

No FastAPI, no Redis, no database needed. `st.session_state` IS the session store. The only caveat: Streamlit Cloud does not persist session state across browser refreshes — but that is true for all three existing apps today and is acceptable.

**Cross-stage navigation guardrails:** each page checks whether its prerequisite stage is complete:

```python
# pages/3_Goals.py — top of file
if not st.session_state.get("profile_complete"):
    st.warning("Complete your risk profile first (Step 1).")
    st.page_link("pages/1_Profile.py", label="Go to Profile →")
    st.stop()
```

This replaces the current "manual handoff" the LinkedIn post honestly admits to. It is not full automation — the user still navigates pages — but it surfaces their Stage 1 results into Stage 2 forms without re-entry.

### 2c. scored_funds.csv: Making It First-Class

The current architecture has two copies of the same fragile relative-path read:

- `P2/src/fund_recommender.py` line 14-21: hardcodes `../../01-mutual-fund-analytics-automation/data/processed/scored_funds.csv`
- `P6/src/fund_recommender.py` line 13-20: same relative path

On Streamlit Cloud, the CWD during app execution is unpredictable (typically the repo root, not the project subdirectory). Both existing apps survive only because their fund recommendations degrade silently to empty lists when the path fails — users see nothing rather than an error. That is acceptable for portfolio demos but cannot be the architecture of a flagship unified product.

**Solution: commit a seed `scored_funds.csv` into the unified project's own `data/` folder.**

Mechanism in `shared/data_store.py`:

```python
from pathlib import Path
import pandas as pd
import streamlit as st

# Primary: bundled seed file committed to the repo
SEED_PATH = Path(__file__).resolve().parent.parent / "data" / "scored_funds.csv"

# Optional override: if P1 has been run locally, prefer the fresher file
P1_LIVE_PATH = (
    Path(__file__).resolve().parent.parent.parent.parent
    / "01-mutual-fund-analytics-automation"
    / "data" / "processed" / "scored_funds.csv"
)

@st.cache_data(ttl=3600)  # cache for 1 hour, not for the full app lifetime
def load_scored_funds() -> pd.DataFrame | None:
    for path in [P1_LIVE_PATH, SEED_PATH]:
        if path.exists():
            try:
                return pd.read_csv(path)
            except Exception:
                continue
    return None
```

**The seed file:** run P1's pipeline once locally, copy `scored_funds.csv` into `projects/08-unified-wealth-platform/data/`, add it to git (it is ~200KB — well within git's reasonable file size for a CSV). Add a comment in the file header noting the snapshot date. Document in the README: "fund data is a snapshot from [date]; to refresh, re-run Project 1's pipeline and replace `data/scored_funds.csv`."

**What if AMFI fetch fails on Streamlit Cloud:** it does not matter, because the unified app never runs the P1 pipeline. It only reads a committed CSV. The pipeline remains a local dev/refresh tool. Streamlit Cloud does not need internet access to AMFI to serve the app.

**Cache TTL:** `st.cache_data(ttl=3600)` is set so that if you do replace the CSV via a redeploy, the new data loads within an hour. Without a TTL, Streamlit caches for the lifetime of the Streamlit process, which means a fresh deploy is needed to invalidate — that is fine but slightly surprising. An explicit TTL is clearer.

### 2d. Streamlit Cloud root-requirements.txt Implications

Current root `requirements.txt` includes: `pandas`, `streamlit`, `plotly`, `requests`, `yfinance`, `openai`, `python-dotenv`, `numpy`, `scipy`, `reportlab`, `openpyxl`.

The unified app needs all of the above (it wraps all three apps) plus nothing new. No additions are required. This is actually an argument FOR the multipage approach: the dependency footprint is the union of what is already declared, so no new deploy risks.

One gotcha: `reportlab` is P6's PDF dependency. It is already in the root `requirements.txt`. The unified app inherits P6's PDF report — no change needed.

If the unified app adds Groq/LLM calls (it will — inheriting P2's `allocation_engine.py`), `openai>=1.0` is already listed (P2 uses it as the Groq OpenAI-compatible client). The `GROQ_API_KEY` secret must be added to the unified app's Streamlit Cloud secrets the same way P2's deployment has it.

---

## 3. POSITIONS ON D1–D5

### D1 — Stack: Unified Streamlit Multipage

**Pick: unified Streamlit multipage app, not React/Next + FastAPI, not hybrid.**

The multipage case (`pages/*.py`) is the right architecture because:

1. **`st.session_state` is shared natively across pages** — this is not a workaround; it is the intended Streamlit multipage pattern. Each page file is just a Python module that imports from `shared/` and reads/writes the same session state dict.
2. **`st.set_page_config` must be called once, in the entry-point `app.py`** — this is the primary technical reason the three existing apps cannot simply be glued together. Each currently calls `st.set_page_config` at the top of its `dashboard/app.py`. In the unified app, `st.set_page_config` moves to `dashboard/app.py` (the entry point), and the page files do NOT call it. This is a clean migration — not a deep rewrite.
3. **CSS lives in one place** — the three apps share ~95% of the same CSS variables. The remaining 5% (P1 has `.ph-title` at 3.8rem, P2 has `.landing-title` at 3.4rem, P6 has `.landing-title` at 3.2rem) are resolved by unifying into one stylesheet injected from `dashboard/app.py` via `st.markdown(CSS, unsafe_allow_html=True)`.
4. **Veer can maintain this** — it is still just Python and Streamlit. No build step, no npm, no API server to keep running, no Docker, no CORS headers, no JWT tokens.

React + FastAPI is not wrong. It would produce a better product. But "better product that breaks in production and Veer cannot debug alone" is worse than "slightly less polished product that works."

**Not a single-page wizard:** the multipage approach is better than a single mega-wizard because it lets users navigate back to the Allocation results while filling in goals (a real workflow need), without losing state.

### D2 — Integration Depth: Structured Hub with Automatic State Threading

**Pick: not zero-handoff, not separate apps — structured hub with automatic state threading.**

The LinkedIn post honestly admits "the handoff between tools is manual today." The unified app removes the manual navigation friction (separate URLs, starting over) without claiming full automation. Concretely:

- The GOALS page auto-populates `monthly_income` from the PROFILE stage's session state. The user does not re-enter their income.
- The PLAN page auto-loads the allocation percentages from the PROFILE stage to contextualise which fund categories the SIP is feeding.
- Each page is still discrete — the user navigates deliberately. But state flows forward without copy-paste.

This is the right tradeoff: it delivers the integration story for the portfolio/LinkedIn narrative while keeping the technical complexity manageable.

### D3 — Portfolio: Flagship-On-Top, Keep the Three Apps Live

**Pick: flagship-on-top. Do NOT replace the three existing deployed apps.**

Reasons:
1. The LinkedIn post links to all three individual apps. Replacing them breaks those URLs for anyone who saved them from the post.
2. Streamlit Community Cloud free tier: four deployed apps (P1, P2, P4, P6) are already live. Adding P8 makes five. Free tier limit is one app per workspace unless grandfathered — check this before committing. If at the limit, the flagship could replace P6 (the most recently added, least-linked).
3. From a portfolio narrative standpoint, having both the individual tools AND the unified platform demonstrates architectural thinking — "I built modular tools that compose."

If forced to choose one URL for a résumé, the unified app wins (fuller story). But do not delete the originals.

### D4 — MVP Technical Core

**The single MVP deliverable:** a working multipage Streamlit app where:

1. PROFILE page (adapted from P2): risk questionnaire → LLM allocation — this is already 100% built; the migration cost is removing `st.set_page_config` from P2's `dashboard/app.py` and moving CSS to the entry point.
2. Shared state: the `monthly_income` and `allocation` outputs from Stage 1 are accessible on Stage 2 pages via `st.session_state`.
3. GOALS page (adapted from P6): goal builder + income + protection — same migration: remove `st.set_page_config`, import from `shared/` instead of `src/`.
4. PLAN page (adapted from P6 results): affordability + PDF — same.
5. `data_store.py` with committed `scored_funds.csv` — replaces the fragile relative-path reads in both P2 and P6's `fund_recommender.py`.

MVP does NOT require: a new UI, a new design, a new backend, any LLM changes, any new calculations.

Honest effort estimate for MVP: **8–12 hours** of focused work across two sessions.

- Session 1 (~5h): create `shared/` package, copy+adapt modules, fix SCORED_FUNDS_PATH, create `dashboard/app.py` with single `st.set_page_config` and unified CSS, stub out `pages/1_Profile.py` importing from shared.
- Session 2 (~4–6h): port remaining pages, implement session state threading, test navigation flow end-to-end, commit seed `scored_funds.csv`, update root `requirements.txt` (likely no changes needed), test deploy.

### D5 — Name

**Defer.** Not the technical architect's call. The PROFILE → PICK → SIZE framing in the LinkedIn post is the clearest description of what the tool does and should guide whatever the formal name becomes. "Wealth Platform" is generic. "Fund Planner" undersells it. Suggest the product council's marketing/reader lens take the lead here.

---

## 4. BIGGEST TECHNICAL RISK

**The `scored_funds.csv` data freshness problem, compounded by Streamlit Cloud's ephemeral filesystem.**

The three existing apps all treat `scored_funds.csv` as something that lives on the local developer's machine and is refreshed by running P1's pipeline. On Streamlit Cloud, this file does not exist unless it is committed to the repo or regenerated at app startup. The current P2 and P6 apps survive this by silently degrading to "no fund picks shown." The unified flagship app cannot afford this — "PICK" is a third of the product's name.

The proposed fix (committed seed CSV) solves the deployment problem but creates a data staleness problem: fund metrics (Sharpe, Alpha, Consistency) are computed from historical NAV data that goes stale. If the seed CSV is 6 months old, the "top-ranked funds" shown in the unified app may no longer reflect current rankings. There is no automated refresh mechanism — the developer must remember to run P1 locally, regenerate `scored_funds.csv`, and push a new commit.

This is not a blocker for MVP — a fresh seed file is accurate enough at launch. But it is a real operational debt. If this becomes a live product rather than a portfolio piece, the correct fix is a GitHub Actions workflow that runs P1's pipeline on a schedule and commits the updated CSV. That is a separate engineering task (not MVP scope) but it should be documented as the known debt from day one.

A secondary risk: Streamlit's multipage architecture changed meaningfully between versions 1.20 and 1.36 (the `pages/` directory pattern stabilised but sidebar behaviour, page titles, and `st.navigation()` all have version-specific quirks). The root `requirements.txt` pins `streamlit>=1.35` — this is recent enough that the stable multipage patterns work, but Veer should test on the exact version Streamlit Cloud deploys (currently 1.41.x as of mid-2026) before assuming the local behaviour matches deployed behaviour.

---

## 5. TOP 3 RECOMMENDATIONS + HONEST EFFORT ESTIMATES

### Recommendation 1: One `st.set_page_config` call, one CSS block — do this first.

The highest-value, lowest-risk first step is to prove the multipage skeleton works before porting any business logic. Create `dashboard/app.py` with only `st.set_page_config` and the unified CSS (merge the three nearly-identical CSS blocks into one, resolve the trivial font-size differences). Create `pages/1_Profile.py` as a stub that says "Profile page — coming soon" and `pages/2_Goals.py` as another stub. Confirm the sidebar navigation renders and the dark theme applies across pages. Only then port the real logic page by page.

**Why first:** `st.set_page_config` is the one call that will crash with a `StreamlitAPIException` if called twice in a single app run. Getting this right first avoids a class of confusing errors where the second page import crashes the entire app.

Effort: **1 hour**.

### Recommendation 2: Replace the two independent `fund_recommender.py` files with one unified version that reads from `shared/data_store.py`.

Currently P2 and P6 each have a `fund_recommender.py` that independently hardcodes the relative path to P1's `scored_funds.csv`. They differ only in their call signatures (`build_fund_recommendations(equity_pct, risk_label, goal)` vs `recommend_for_goal(years)`). Write one unified `shared/fund_recommender.py` that:

- Reads from `shared/data_store.load_scored_funds()` (the `@st.cache_data` wrapper described in 2c)
- Exposes both call signatures (or a unified one that covers both cases)
- Fails loudly (shows a yellow banner) rather than silently returning empty results, so data freshness issues are visible rather than hidden

Commit a fresh `data/scored_funds.csv` at the same time.

Effort: **2–3 hours** including running P1's pipeline to generate a fresh seed file.

### Recommendation 3: Thread `monthly_income` and `allocation` forward from PROFILE to GOALS — this is the only meaningful UX improvement the unified app offers over three separate links.

The LinkedIn post says "the handoff between tools is manual today." The portfolio story improves significantly if the unified app eliminates the one most annoying re-entry: the user's monthly income (entered in PROFILE's Step 6) is pre-populated as the default in GOALS' income step. Similarly, the allocation percentages from PROFILE (e.g. 60% equity) should be visible in GOALS' "Fund Picks" tab as context for why those fund categories are shown — the user should not have to remember what PROFILE told them.

This requires: defining `DEFAULT_STATE` as described in 2b, initialising it in `dashboard/app.py`, and adding four lines in `pages/3_Goals.py` to read `st.session_state.monthly_income` as the default for the income input widget.

Effort: **2 hours** once the multipage skeleton is working.

---

**Total MVP effort estimate: 8–12 hours across two sessions. No new dependencies. No new cloud services. No build tools.**

The architecture is ready. The modules are solid. The migration is mechanical, not creative. The biggest leverage is making `scored_funds.csv` a first-class dependency before launch, not after.
