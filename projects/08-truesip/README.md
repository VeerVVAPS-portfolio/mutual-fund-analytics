# TrueSIP — *Your SIP, solved not guessed.*

TrueSIP turns three of my standalone finance tools into **one goal-first product**. It profiles your risk, sizes the *exact* monthly SIP each goal needs (solved backward from the goal's future value — never guessed), and shows the horizon-appropriate asset mix behind it — in a single continuous flow with **zero manual handoffs**.

It is the productization of a workflow I had only ever run as three separate Streamlit apps:
[Mutual Fund Analytics](../01-mutual-fund-analytics-automation) · [AI Asset Allocator](../02-ai-financial-profile-asset-allocation) · [Goal-Based Wealth Planner](../06-goal-based-sip-planner).

> **Educational tool — not SEBI-registered investment advice.** Consult a SEBI-registered investment adviser before investing.

---

## The problem it fixes
A financial plan can *look* complete while quietly under-funding its goals. In the source plan this was built from, two of three goals used round-number SIPs that were **guessed**, not solved — under-funding them by ~6–8%. TrueSIP always solves the SIP **backward** from each goal's inflation-adjusted future value, so "looks complete" and "is complete" are the same thing.

## One product, one flow
1. **Diagnosis (the front door)** — enter a goal + your current SIP → see instantly whether you're on track or short.
2. **Profile** — a 5-question risk quiz → a risk label.
3. **Goals & Income** — refine goals, add income/expenses, choose a SIP step-up.
4. **Your Plan** — per-goal **deterministic SIP**, the horizon-appropriate allocation, the SIP split across equity/debt/gold, and an AI-written *"why."*
5. **Explore Funds** *(opt-in)* — a general, neutral-weighted fund screener.

## What makes it honest (and interview-worthy)
- **Every number is deterministic.** The LLM (Groq, Llama 3.3) only explains the *why* — enforced in **code**: the context sent to the model is stripped of figures, and a regex discards any response that emits a ₹-number, falling back to a deterministic explanation.
- **Horizon-authoritative allocation.** Each goal's *time horizon* sets its equity band (`<3y 0–10% … >15y 70–85%`); the risk profile is only a *tilt + cap within* that band. A 2-year goal gets near-zero equity **even for an aggressive investor**.
- **Per-goal blended return.** A near-term goal assumes a lower expected return than a long-horizon one — fixing the flat-rate-for-every-goal error in the source model.
- **Debt/gold are named but explicitly *unranked*** (their equity-vs-index metrics don't apply) — no fabricated numbers.
- **Two-mode compliance.** The personalized "Your Plan" never pairs a named fund with a personalized amount; specific funds live only in the opt-in, general screener. (Post-2025 SEBI-aware.)

## Architecture
```
projects/08-truesip/
├── dashboard/
│   ├── app.py            # single-entry session_state wizard (routing + nav + disclaimers)
│   └── views.py          # every screen body + Plotly charts
├── shared/               # ONE self-contained package (deploy needs no other project folder)
│   ├── planning_engine.py  # the reconciliation engine — horizon bands, blended return, deterministic SIP, asset split, category hand-off
│   ├── explainer.py        # Groq "explain-why" layer (prose only) + demo fallback
│   ├── data_store.py       # cached seed loader (hard error if data missing — never silent-empty)
│   ├── risk_profiler.py / goal_calculator.py / scoring.py / metrics.py / cashflow_projection.py / protection.py
│   └── theme.py
├── data/scored_funds.csv # committed seed (93 funds / 10 categories) — no live-fetch dependency
└── _process/             # how it was built (see below)
```
Runtime data-flow diagram: [`_process/WORKFLOW_DIAGRAM.md`](_process/WORKFLOW_DIAGRAM.md).

## How it was built — the differentiator
Not vibe-coded. Built with a **Lean Six Sigma (DMAIC)** process, orchestrated across a team of AI agents:
- A **6-member critic council** (product · UX · technical · finance-domain · recruiter · risk/devil's-advocate) debated the idea, surfaced **3 build mandates**, and resolved a real SEBI-compliance question into a cleaner two-mode design.
- A **7-agent build team** (models delegated by task: **Haiku** mechanical · **Sonnet** standard build · **Opus** heavy finance reasoning) built it, with each agent's mandates encoded in its persona file.
- Two **auditor agents** (finance-correctness, compliance) plus a **browser UX audit** gated the result.

The full record — the debate, the decisions, the mistakes, the audits — is in [`_process/`](_process/): [`PROCESS_LOG.md`](_process/PROCESS_LOG.md) · [`council/`](_process/council/) · [`audits/`](_process/audits/) · [`WORKFLOW_DIAGRAM.md`](_process/WORKFLOW_DIAGRAM.md). The build team lives in [`.claude/agents/`](.claude/agents/).

## Run locally
```bash
cd projects/08-truesip
pip install -r requirements.txt
streamlit run dashboard/app.py
```
Runs fully **without an API key** (deterministic demo explanations). For live LLM prose, set `GROQ_API_KEY` in `.env` (see `.env.example`) or Streamlit secrets — free key at https://console.groq.com/keys.

## Deploy (Streamlit Community Cloud)
- **Main file:** `projects/08-truesip/dashboard/app.py`
- Streamlit Cloud installs the **repo-root** `requirements.txt` (the union of all apps) — TrueSIP adds no new dependencies.
- Add `GROQ_API_KEY` to the app's secrets (optional; demo mode works without it).

---
*Methodology, financial parameters, and domain logic by Veer Pratap Singh. Built with Claude Code (AI-assisted, council-driven development).*
