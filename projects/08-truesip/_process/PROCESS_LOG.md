# PROCESS LOG — Productizing "Profile → Pick → Size" into One Wealth Platform

> **Purpose of this file.** A running, honest record of *how* this product was built — the method, the decisions, the council debate, the model-delegation choices, and the mistakes-and-corrections. It is structured as a **Lean Six Sigma DMAIC** project. At the end it is meant to be distilled into a reusable Claude Code **skill** ("how to productize several standalone tools into one integrated product, agent-orchestrated"). Write the truth here, including dead-ends — a skill built from a sanitized log is useless.

> **Operating principle (Einstein).** *"If I had an hour to solve a problem, I'd spend 55 minutes thinking about the problem and 5 minutes thinking about solutions."* The DEFINE + ANALYZE phases (problem framing + council debate) are deliberately heavy. We do not write product code until the problem and direction are locked.

---

## 0. Project Charter

| Field | Value |
|---|---|
| **Product name** | **TrueSIP** — *"Your SIP — solved, not guessed."* |
| **Working directory** | `projects/08-truesip/` |
| **Start date** | 2026-06-30 |
| **Sponsor / Voice of Customer** | Veer Pratap Singh |
| **Build engine** | Claude Code (Opus 4.8 orchestrator + delegated subagents) |
| **Method** | Lean Six Sigma (DMAIC) + agent council + `/agent-architect` build team |
| **Inputs** | Project 1 (MF Analytics), Project 2 (AI Asset Allocator), Project 6 (Goal-Based Wealth Planner) — all live Streamlit apps |
| **North-star artifact** | `linkedin-post/FINAL_POST.md` — the "PROFILE → PICK → SIZE" narrative this product makes real |

---

## D — DEFINE

### D.1 Problem statement
Veer has **three independently-deployed Streamlit tools** that, narratively, form one journey — *profile the investor → pick the funds → size the SIP*. But today they are three separate apps. In his own LinkedIn post the limitation is stated plainly:

> *"The handoff between tools is manual today, not automated."*

A user must (1) open the AI Asset Allocator, get an Equity/Debt/Gold mix; (2) **manually** open the Mutual Fund Analytics app and look up funds for those categories; (3) **manually** open the Goal-Based Planner and type numbers in again to size a SIP. Three apps, two manual data re-entries, three mental-model resets. It reads as a *portfolio of features*, not a *product*.

### D.2 Goal statement (Six Sigma form)
> Transform three independently-deployed tools (with **2 manual data hand-offs** and **3 separate entry points**) into **one cohesive, deployed product** that carries a user from risk profile → fund selection → exact SIP sizing in a **single continuous flow with 0 manual re-entries**, while preserving the "every number is deterministic; the LLM only explains why" integrity that is the credibility spine of the whole thing.

### D.3 Voice of Customer → CTQs (Critical-to-Quality requirements)
What "good" must mean for this product. Each CTQ is something we can later test against (CONTROL phase).

| # | CTQ | Why it matters | How we'll verify |
|---|---|---|---|
| **CTQ1** | **One flow, zero manual handoffs.** Profile output auto-seeds Pick; Pick + goals auto-seed Size. | This *is* the productization. Without it we've only built a menu. | Walk the flow end-to-end; assert no copy-paste step exists. |
| **CTQ2** | **Determinism preserved & traceable.** LLM explains "why" only; every rupee figure traces to percentile scoring / annuity-due math / live AMFI data. | It's the entire credibility & interview story. Breaking it would be self-sabotage. | Code review: no number originates from an LLM response. |
| **CTQ3** | **Finance composes correctly across stages.** Asset-class allocation → equity fund picks → per-goal SIP sizing must be mutually consistent, no contradictions. | Chaining can create domain bugs that don't exist in the standalone apps (e.g. allocation is multi-asset, but the fund scorer only ranks equity). | Finance-domain critic + worked example on a real profile. |
| **CTQ4** | **First-time user completes it without instructions.** | A product a recruiter clicks must be self-evident in 30 seconds. | `product-critique` + `ux-audit` skills before "done". |
| **CTQ5** | **Strengthens portfolio positioning without destroying the 3 existing deployed apps' value.** | He currently has 3 resume lines / 3 live URLs. A merge could create a flagship OR collapse 3 proofs into 1. Strategic risk. | Recruiter/portfolio critic must rule on keep-vs-replace. |
| **CTQ6** | **Veer can deploy & maintain it** at his current skill level (strong Python; new to web frameworks; uses Streamlit Cloud). | A beautiful React app he can't redeploy or debug is a liability, not an asset. | Stack decision (D-open) weighs maintainability explicitly. |
| **CTQ7** | **Compliant & honest.** Educational framing, "not SEBI-registered advice," limitations stated. | Post-2025 SEBI finfluencer rules; honesty is itself the trust signal. | Disclaimer present at each advice-shaped step; no overclaiming. |

### D.4 Scope
**In scope:** integrating Projects 1, 2, 6 into one product; unified UX & branding; automated stage-to-stage data handoff; a single entry point / landing; a deployment path Veer can run.

**Out of scope (this iteration):** Project 4 (Black-Litterman) and Project 7 (Equity Research) — different journey; new external data sources; user accounts / auth / payments (unless the council makes a strong case); native mobile.

### D.5 Open decisions (to be informed by the council, then confirmed by Veer)
- **D1 — Stack:** unified Streamlit app · vs · real web app (React/Next + Python API) · vs · hybrid (marketing landing + Streamlit tool).
- **D2 — Integration depth:** full automated single-flow · vs · lighter "hub" that links the three with shared state.
- **D3 — Portfolio strategy:** does the unified product *replace* the 3 deployed apps on the resume, or *sit on top of* them (flagship + 3 components)?
- **D4 — MVP definition:** the ONE thing that makes it feel like a product vs. a menu.
- **D5 — Name & positioning.**

### D.6 Success metrics (baseline → target)
| Metric | Baseline (today) | Target (this product) |
|---|---|---|
| Manual data hand-offs in the journey | 2 | **0** |
| Separate entry points | 3 | **1** |
| Numbers sourced from an LLM | 0 (keep it) | **0** |
| "Is this a product or a demo?" (recruiter critic, 1–10) | TBD (council baselines it) | **≥ 8** |
| First-time-user task completion w/o help | TBD | Pass `ux-audit` hard gates |

---

## M / A — MEASURE & ANALYZE  *(the council debate)*
> Full individual critiques in `_process/council/`; consolidated tally + reasoning in `_process/council/SYNTHESIS.md`. Six critics gave independent opening positions (Round 1); a focused Round 2 cross-examined the one decision-relevant disagreement (compliance).

### Round 1 result
- **Verdicts:** 3× YES-BUT, 1× YES (UX), 1× YES (Technical), **1× DON'T/BUILD-THIN** (Risk/Devil's Advocate).
- **Unanimous (6/6):** D1 = unified **Streamlit** (no React — adds zero domain signal, breaks CTQ6); D3 = **flagship on top** (keep all 3 apps live + 3 resume lines; don't collapse 3 proofs into 1); integrity spine sacred.
- **Majority (5/6):** D2 = **full automated single-flow** (lone dissent on compliance/opportunity-cost, not feasibility).
- **3 build mandates surfaced** (latent bugs the standalone apps hid):
  1. **Kill the LLM-suggested SIP** (P2 `monthly_sip_suggestion`) — only SIZE's deterministic solver may output a SIP, or the product contradicts its own integrity spine on screen.
  2. **Horizon-authoritative allocation** — each goal's horizon sets its equity band (`<3y:0–10% · 3–7y:20–40% · 7–15y:50–70% · >15y:70–85%`); the risk-profile mix is a *tilt + cap within band*, not a competing person-level allocation.
  3. **Show the equity-only gap honestly** — split each goal's SIP by asset class; only equity rupees reach the screener; Debt/Gold/Alts are *named but un-ranked*; never fabricate Sharpe/Alpha off-equity.
- **Chair-resolved:** enforced linear wizard via `st.session_state` (hide native page switcher), not jump-anywhere `pages/`.

### Tensions carried forward
- **A — Compliance (→ Round 2):** does chaining profile + named fund + rupee amount cross into SEBI "investment advice" by a non-RIA? Devil's Advocate says yes (category change). Round 2 tests whether a bounded, opt-in, methodology-framed screener satisfies the guardrail.
- **B — Opportunity cost (→ Veer):** RAG/SQL gap-filler first? Surfaced honestly; the 8–12h estimate reframes it as a small bet. Veer already directed building this; queue RAG next.

### Round 2 result — compliance RESOLVED (consensus)
Cross-examined the Devil's Advocate and the Finance Domain critic directly (resumed their sessions). They converged:
- **The objection was to PAIRING, not naming.** No single screen / continuous path may combine a *personalized output* + a *specific named security* + an *amount/buy-directive*. Decoupled, an objective universe-wide ranking is fine.
- **Resolution → two clean modes.** **"Your Plan"** (personalized, deterministic: horizon-banded allocation + solved SIP + the *methodology* of fund scoring) and **"Explore Funds"** (opt-in, general, neutral-weighted, category-filtered screener). The personalized flow hands the screener only a *category* — never a pre-ranked "#1 for you."
- **Finance verdict:** keeps ~90% of decision value (fund *selection* is the lowest-alpha, most-commoditized step) and is *more* educational — teaches the screening rule, not a decaying answer. Separating planning ("how much / where") from selection ("which instrument") mirrors how advisors actually think.
- **Acceptance criterion (verbatim to build team):** *"No screen and no continuous user path may combine a personalized output with a specific named security AND an amount/buy-directive — the moment all three co-occur, it's advice, not education."*
- Conduct-not-context: free/demo status lowers enforcement odds, not classification — guardrails stay on.

### Council outcome → the locked product shape
Goal-first, single-flow Streamlit product, flagship-on-top, with the 3 build mandates + the two-mode compliance architecture baked in. Remaining open items are Veer's taste/scope calls (front door, scope depth, name) — taken to him now.

---

## I — IMPROVE  *(agent roster + build)*
> 7-agent roster recruited via `/agent-architect` (files in `projects/08-truesip/.claude/agents/`, summary in `WORKFLOW.md`). The MAIN session orchestrates; no separate orchestrator subagent (the skill's default for sequence-able leaf agents). For this session the personas are executed by spawning general-purpose agents that READ their own persona file and run at the assigned model (manual agent files need a restart to auto-load).

### Model-delegation map (task complexity → model)
| Phase | Agent | Model | Why this tier |
|---|---|---|---|
| 1 | data-pipeline-runner | **Haiku** | Mechanical copy/validate of an existing CSV — no reasoning |
| 2 | shared-core-engineer | **Sonnet** | Standard refactor/scaffolding against known patterns |
| 3 | integration-logic-architect | **Opus** | The reconciliation finance reasoning — the crown jewel; gets the bug-prone judgment calls |
| 4 | llm-reasoning-engineer | **Sonnet** | Standard Groq/structured-output adaptation of an existing pattern |
| 5 | streamlit-ux-builder | **Sonnet** | Multi-screen UI assembly against well-defined interfaces |
| 6 | finance-correctness-auditor | **Opus** | Verifying "wrong-but-confident" numbers needs judgment |
| 7 | compliance-guardrail-checker | **Sonnet** | Mechanical scan against a fixed acceptance criterion |

### Build narrative
- **Phase 1 (Haiku) — data seed.** Copied Project 1's `scored_funds.csv` (93 funds / 10 categories / 22 cols) into TrueSIP's committed `data/`. The deploy now never depends on a live AMFI fetch succeeding on Streamlit Cloud.
- **Phase 2 (Sonnet) — shared core + scaffold.** `shared/` package of adapted pure-function modules; `data_store.load_scored_funds()` raises a hard `RuntimeError` on a missing file (the #1 council-flagged silent-empty trap, closed in code); `theme.py` + `.streamlit/config.toml`; `dashboard/app.py` wizard scaffold with a documented `session_state` contract + per-step fill contract. Verified: pure imports + horizon-band function reproduce Mandate #2 (2y→0% equity even for an aggressive investor; horizon wins).
- **Phase 3 (Opus) — reconciliation engine** (`shared/planning_engine.py`). `build_plan()` + horizon-banded allocation + **per-goal blended return** (the honest fix: near-term goals assume a lower return than long-horizon ones, replacing P6's flat 12%/goal) + deterministic SIP solving + asset split + a compliance-safe **category-only** handoff. Self-check reproduces P6's goal FV within <1% and asserts (a) no goal's equity% escapes its band, (b) asset rupees sum to the SIP, (c) **no scheme name ever leaks into a plan output**.
- **Phase 4 (Sonnet) — explainer** (`shared/explainer.py`). `explain_plan()` (Groq llama-3.3-70b, structured output) + a plan-aware demo fallback for the no-key majority. **Two-layer no-number guarantee:** strips rupee figures from the LLM context, then regex-discards any response containing a `₹`-figure back to the demo path. The LLM cannot put a number on screen.
- **Phase 5 (Sonnet) — UI.** *(in progress)* Goal-first diagnosis front door (the chosen wedge), the wizard, "Your Plan" results, the decoupled "Explore Funds" screener, and the Advanced wealth check.

### Notable findings (for the eventual skill)
- **Productizing ≠ novel engineering; it's resolving the contradictions a merge exposes.** The data seam was already half-built; the real value was the reconciliation engine + showing the gaps honestly (the council's Product Strategist called this exactly).
- **Determinism enforced in CODE, not by convention** — `build_plan` asserts no scheme-name leak; the explainer regex-discards LLM numbers. A "the LLM only explains why" claim is only credible if the code makes it impossible to violate.
- **A late product decision can desync the scaffold.** D4 (goal-first *diagnosis*) was locked with Veer *after* the scaffold was specced, so the scaffold only stubbed goal-collection, not the under-funding hook. Caught at the Phase-5 handoff and re-specified. Lesson: when a product fork is decided after scaffolding, re-verify the scaffold encodes it before the UI agent runs.

---

## C — CONTROL  *(QA gates + verification + handoff)*

### Code-level QA gates — both PASS (independent auditor agents)
- **finance-correctness-auditor (Opus) → `GATE: PASS`** (0 FAILs). Every UI number traces to a `shared/` function; `explain_plan` is opaque prose (LLM triple-guarded: prompt rule + qualitative-only context + post-gen `₹`-regex fallback). Bands match spec; risk tilt asserted in-band (Conservative pinned at floor, Moderate-Conservative at midpoint — stricter than required). `required_fixed_sip` matches an independent annuity-due solve to **1e-6**; Project 6 Education FV anchor reproduced to **0.05%**. Asset rupees sum to the SIP to the paisa; only equity carries a category; no Sharpe/Alpha on debt/gold. **12%-vs-16/17% ruling: HONEST** — a lower return makes any fixed guess look *more* under-funded, so it deepens (never hides) the finding; and TrueSIP re-solves every SIP, so there's no stale figure to distort.
- **compliance-guardrail-checker (Sonnet) → `GATE: PASS`.** `scheme_name` renders on exactly one surface (Explore Funds), which reads no profile/goal state; goal cards hand off by category + forced neutral weights ("We don't pick a fund *for you*"); `build_plan` emits only category strings. SEBI disclaimer at all 5 advice-shaped surfaces. No file/DB writes — stateless, no PII at rest.
- Full reports: `_process/audits/finance-correctness.md`, `_process/audits/compliance.md`.

### Non-blocking follow-up (folded into the UX polish)
- Per-asset return assumptions (equity 12% / debt 7% / gold 6%) are disclosed (blended figure per card + `plan['return_assumptions']`) but not individually user-editable (inflation + step-up are). → annotate clearly as fixed planning constants in the UI.

### Browser-level UX gate — PASS (after fixes)
Ran the `ux-audit` skill via a Playwright walk of the live app (report: `_process/audits/ux-audit.md`). Both hard gates pass (navigation orientation; no mobile horizontal scroll at 375/390px). The gate caught **3 visual defects the code auditors structurally could not**: metric-value truncation (the key ₹ figure showed as "…"), a shortfall delta rendered green (misleading), and duplicated subheading copy — all fixed in `views.py` and re-verified live. Also annotated the fixed 12/7/6 return assumptions (auditor's non-blocking note). One minor open item (raw `number_input` display, a Streamlit limitation) is backlogged. **GATE: PASS.**

### QA outcome
All three gates PASS: finance-correctness (Opus) · compliance (Sonnet) · UX (ux-audit + fixes). The product is correct, compliant, and usable end-to-end.

### Deployment & handoff
- Streamlit Community Cloud main file: `projects/08-truesip/dashboard/app.py`. The repo-ROOT `requirements.txt` (union) is what deploys — TrueSIP adds **no** new dependency.
- `GROQ_API_KEY` is optional (Streamlit secrets or `.env`); the app runs fully in demo mode without it.
- The committed seed `data/scored_funds.csv` means the deploy never depends on a live AMFI fetch.
- Deliverables shipped: `README.md`, `.env.example`, per-project `requirements.txt`, the 7 agent personas in `.claude/agents/`, the two audit reports in `_process/audits/`, and the diagrams in `_process/WORKFLOW_DIAGRAM.md`.

---

## Skill extraction — the point of this log
This log is meant to distill into a reusable skill (working name **`productize-standalone-tools`**). The transferable pattern:
1. **Reframe** N standalone tools as *one journey*; count the manual seams — those seams *are* the product.
2. **Council before build (Analyze before Improve).** Spin up a small multi-lens critic council (product · UX · technical · domain · recruiter · risk/devil's-advocate), then one focused cross-examination round on the single most contested decision. The council's real value is surfacing the **contradictions a merge exposes** — invisible until you integrate (here: the double-SIP, the person-vs-goal allocation paradigm clash, the equity-only gap, and the compliance *category change*).
3. **Lock the few genuinely-human decisions** (stack, scope, name, portfolio strategy) with a quick guided choice — don't let the agents decide these.
4. **Recruit a model-delegated agent team** via `/agent-architect`: Haiku = mechanical · Sonnet = standard build / fixed-criteria checks · Opus = heavy reasoning + correctness judgment. **Encode the council's mandates into the persona files** so agents build them by construction.
5. **Sequence the critical path; parallelize only non-conflicting phases.** The orchestrator (main session) sequences leaf agents — no separate orchestrator agent for a sequence-able build.
6. **Gate with auditors + a browser UX audit.** Code auditors can't see truncation or colour-semantics; the UX gate caught three such defects here that PASSed every static check.
7. **Enforce invariants in code, not convention** (no LLM-sourced numbers; never pair a named security with a personalized amount) — assertions + regex guards, so the guarantee can't silently rot.
8. **Log honestly, including the stalls and wrong guesses** — a skill built from a sanitized log is useless (see the Mistakes table: the mid-stream agent stall and the mid-load screenshot were the most instructive moments).

Portable artifacts produced here: the 7 build-agent personas, the two auditor personas (reusable on any finance-tool project), and the **education-vs-advice acceptance criterion** (*"no continuous path may combine a personalized output + a specific named security + an amount/directive"*).

**Status: COMPLETE.** TrueSIP is built, QA-gated (3/3), and ready to deploy.

---

## Decision Log
| ID | Decision | Rationale | Date | Status |
|---|---|---|---|---|
| — | Treat this as a DMAIC project, council-first, before any code | User's explicit ask + Einstein operating principle; de-risks building the wrong thing | 2026-06-30 | adopted |
| — | Provisional working dir `projects/08-unified-wealth-platform/` | Follows repo's `projects/NN-*` convention; name is provisional pending D5 | 2026-06-30 | provisional |
| D1 | **Unified Streamlit** (single entry-point, `session_state` wizard; no React) | Council 6/6; preserves CTQ6 (Veer can deploy/maintain); apps share one CSS system already | 2026-06-30 | locked (Veer proceeded) |
| D2 | **Full automated single-flow**, goal-first | Council 5/6; it *is* the productization (0 handoffs) | 2026-06-30 | locked (Veer proceeded) |
| D3 | **Flagship on top** — keep all 3 apps live + 3 resume lines | Council 6/6; don't collapse 3 independent proofs into 1 | 2026-06-30 | locked (Veer proceeded) |
| MANDATE-1 | Kill the LLM SIP; only the deterministic solver outputs a SIP | Integrity spine must hold on screen | 2026-06-30 | adopted |
| MANDATE-2 | Horizon-authoritative allocation (risk mix = tilt+cap within horizon band) | Resolves the person-level vs goal-level paradigm clash | 2026-06-30 | adopted |
| MANDATE-3 | Equity-only gap shown honestly (equity→screener; debt/gold named-unranked) | Honesty > fabricated metrics; matches existing P6 caution pattern | 2026-06-30 | adopted |
| D4 | **Front door = goal-first under-funding diagnosis** | Veer's pick; strongest hook, matches the working LinkedIn post | 2026-06-30 | locked |
| D5 | **Name = TrueSIP** ("Your SIP — solved, not guessed") | Veer's pick; goal/integrity-forward; drops "wealth platform" framing | 2026-06-30 | locked |
| SCOPE | **Lean core + optional Advanced** (protection/FOIR collapse into an expander) | Veer's pick; ships within the 8–12h estimate | 2026-06-30 | locked |
| SEQ | Proceed now; queue a RAG/SQL gap-filler next | Veer directed this build; opportunity-cost dissent acknowledged | 2026-06-30 | locked |
| TEAM | 7-agent build roster (Haiku/Sonnet/Opus) recruited via `/agent-architect`, saved to `projects/08-truesip/.claude/agents/` | Veer confirmed full roster + project-level location | 2026-06-30 | done |
| A | **Compliance RESOLVED** — two modes: personalized "Your Plan" ends at allocation+SIP+methodology; named ranking only in opt-in general "Explore Funds" screener | DA + Finance consensus; keeps ~90% value, more educational, satisfies the acceptance criterion | 2026-06-30 | resolved |

## Mistakes & Corrections Log
> The most valuable part of this file for the eventual skill. Every wrong turn, why it happened, and the fix. Honesty over polish.

| # | What went wrong | Why | Correction | Lesson for the skill |
|---|---|---|---|---|
| 1 | After renaming the project folder, 3 `Edit` calls on `PROCESS_LOG.md` failed with *"File has not been read yet"* | Moving the folder invalidated the harness's tracked file state for files inside it | Re-`Read` the file at its new path, then re-applied the edits | **Rename/move a project folder BEFORE writing files into it** (or expect to re-Read after a move). Sequence the rename earliest. |
| 2 | `AskUserQuestion` rejected the call with a `preview` type error | Passed `preview: null` for options that had no preview | Omit the `preview` field entirely (don't pass null) for options without one | Optional structured fields: omit, don't null. |
| 3 | Scaffold (Phase 2) only stubbed goal-collection, not the goal-first *diagnosis* front door Veer chose | The front-door decision (D4) was locked *after* the scaffold was specced | Re-specified the actual under-funding-diagnosis hook in the Phase-5 UI brief | When a product fork is decided after scaffolding, re-verify the scaffold encodes it before the dependent agent runs. |
| 4 | The Phase-5 UI agent **stalled mid-stream** after ~9 min; NONE of its writes persisted (`app.py` was still the scaffold) | A single large agent response streaming a big UI build is a single point of failure | Resumed the agent (context intact) with a stall-safe strategy: heavy logic in a separate module, small incremental edits, parse-check after each, stop-and-report if the response runs long | For large single-agent build tasks, mandate incremental writes + verification checkpoints so one stall can't wipe the work. **The orchestrator must verify persisted state after any agent error — never trust the summary.** |
| 5 | First UX screenshots captured Streamlit **mid-load** (skeleton), and clicks failed on guessed button labels | Used a fixed 4s sleep instead of waiting for rendered content; assumed scaffold button labels but the UI agent used the specced CTA copy | Waited on the real next-screen button to be *visible* before each shot/click; grepped `app.py` for the actual labels | For Streamlit/SPA capture, wait on a concrete rendered element (never a fixed sleep); read the real control text before automating clicks. |
