# Risk & Compliance + Devil's Advocate — Dissent on the Unified "PROFILE → PICK → SIZE" Platform

*Council member: Risk & Compliance Officer / Devil's Advocate. Role: argue the case AGAINST and surface what others will rationalize away. This is intentionally the dissent — read it against the optimists, not instead of them.*

---

## 1. VERDICT

**DON'T build the auto-chained version. BUILD-THIN at most: a single landing/"hub" page that explains the workflow and links out to the three apps that already work — and even that is optional. The honest recommendation is: ship a NEW project that fills a visible skill gap (SQL or RAG) instead.** Reason: chaining a risk profile → *specific named funds* → *exact rupee amount to invest monthly* converts three separately-defensible "educational simulators" into one artifact that reads as personalized investment advice, while the marginal hireability gain over what's already live is near zero and the downside (breaking three working demos for a recruiter who clicks them) is real.

---

## 2. COMPLIANCE ANALYSIS

### 2.1 Does chaining materially increase regulatory / representational risk? YES — unambiguously.

This is not a marginal increase. It is a category change. Here is the mechanism, and why "but each tool already does this" is a rationalization:

- **Project 2 alone** outputs an *asset-class* mix (Equity/Debt/Gold/Alternatives) with reasoning. That is asset-allocation education — generic, no security named. Defensible.
- **Project 1 alone** ranks *named* mutual fund schemes ("ICICI #1") by Sharpe/Alpha/consistency. On its own it is presented as a *screening/ranking methodology demo* — "here's how you'd rank funds," a tool an analyst builds. The named fund is incidental output of a transparent formula, not a recommendation aimed at a person. Borderline, but defensible as methodology.
- **Project 6 alone** computes *how much* an annuity-due SIP must be to hit a target. Pure math. Defensible.

**The moment you chain them, the output is no longer three generic artifacts — it is one personalized prescription addressed to the individual user who just answered the quiz:** *"You (risk 37/100, this income, this horizon) should put ₹X/month into THIS named ICICI fund."* That sentence has all four hallmarks regulators look for in "investment advice": (1) it is **personalized** to the user's stated circumstances, (2) it concerns **specific securities** (named schemes), (3) it includes a **specific quantum** (the rupee amount), and (4) it is **directive** (profile → here is your plan). No single tool has all four. The chained tool has all four in one screen. That is precisely the line.

Under SEBI's framework, "investment advice" given for consideration by anyone not registered as an Investment Adviser is the regulated act; the post-2025 finfluencer tightening specifically went after unregistered persons making **specific-security, personalized recommendations** dressed up as education. Veer is **NISM V-A certified (mutual fund distribution) but NOT a SEBI-registered Investment Adviser.** NISM V-A authorizes *distribution*, not *advice* — and even a distributor is not licensed to give personalized advice; the regulatory regime deliberately separates "advice" (RIA) from "distribution" (ARN). A public, free tool that profiles a stranger and tells them the exact fund and exact amount is the textbook thing the separation exists to prevent.

**The "educational, not advice" disclaimer does NOT cure this.** A disclaimer cannot reclassify conduct. If the *substance* is personalized specific-security guidance, a footer saying "educational" is the exact pattern the finfluencer rules were written to defeat — regulators explicitly discount disclaimers when the product behaves like advice. Worse: the more *credible and personalized* Veer makes the chain (which is the whole selling point — "your mix, your funds, your exact SIP," per the carousel cover), the *weaker* the disclaimer defense becomes. The product's strength is its compliance weakness. **You cannot maximize "this feels like a real personalized plan" and minimize "this looks like advice" at the same time — they are the same axis.**

### 2.2 The specific-fund-naming question — the single highest-leverage decision

**In the integrated/chained flow, do NOT name specific funds.** This is the one change that most reduces risk while preserving ~90% of the demo value. The integrated flow should terminate at the **category** level ("based on your profile, a Large Cap allocation of this size; here is the *methodology* we'd use to screen Large Cap funds") and **stop there**, with the named-fund ranking living *only* in the standalone Project 1 demo, framed explicitly as a screening-methodology showcase, not a buy list.

Why this matters: personalized + quantum + *named security* is the trifecta. Remove the named security from the personalized path and you have "here's a general allocation and how much" — much closer to a calculator/education tool than a recommendation. The named-fund ranking, *decoupled* from the individual's profile, is far more defensible as "an analyst's ranking engine."

If Veer insists on showing funds in the chain, the absolute minimum is: show **3–5 funds as illustrative examples of the category, never a single "#1," never a "buy this"**, with the ranking visible as a transparent, user-adjustable formula (which Project 1 already is) so it reads as "here is a tool that ranks; you decide" rather than "here is your pick."

### 2.3 Mandatory guardrails (non-negotiable if it ships at all)

1. **No persistence of user inputs. Zero PII at rest.** The risk quiz, income, expenses, goals, dependents, existing-insurance, and loan figures (Project 6 collects financial *and* quasi-health-adjacent data) must live in session state only — never written to disk, DB, logs, or analytics, never sent anywhere except the in-memory LLM call. **Do not add accounts, "save my plan," email capture, or any login.** The instant you store a stranger's financial profile you have created a data-protection obligation (India's DPDP Act) on top of the SEBI question, for a portfolio toy. Keep it stateless.
2. **The LLM must never name or rank a security.** Per the existing architecture the LLM explains the "why" and outputs an *asset-class* JSON only; fund selection is deterministic Python. **Preserve that wall absolutely** — if the integrated prompt is ever loosened to let the model say "buy ICICI," you've put unregistered, hallucination-capable specific-security advice into production. The deterministic-only-for-fund-selection rule is itself a compliance control, not just an engineering one.
3. **Disclaimer must be unavoidable and pre-result, not a footer.** Interstitial before the plan renders: "This is an educational simulation of a financial-planning *methodology*. It is not investment advice and not personalized to you. Veer is not a SEBI-registered Investment Adviser. Consult a registered adviser before investing." Require acknowledgment to proceed. Footer-only is insufficient for a chained flow.
4. **Frame the output as "methodology / worked example," never "your plan."** Kill carousel/UI copy like "your mix, your funds, your exact SIP." Replace with "how a planner would size and screen for a profile like this." The framing *is* a control.
5. **Use synthetic/sample inputs in the demo, not real-user solicitation.** Default the demo to a pre-filled fictional persona (the existing "Mr. Peter" pattern). A recruiter should be able to see the whole flow without ever typing their own salary. This sidesteps both the advice and the PII problem in one move.
6. **No "expected return" presented as achievable.** Project 6's README already flags 16–17% as optimistic and defaults to 12% — keep that honesty and label every projection a planning estimate, never a forecast.

---

## 3. DEVIL'S ADVOCATE CASE

### 3.1 The strongest single argument against building

**Three clean, live, independently-deployed tools demonstrate MORE engineering maturity than one ambitious app that's half-integrated and occasionally broken — and a recruiter's click is a pass/fail test you only get once.** Right now Veer has three green-checkmark demos. A recruiter clicks, each loads, each does one thing well: that reads as "ships and maintains production software." The integrated build's realistic failure mode is a fourth app that is buggier than the three it subsumes, *plus* the non-trivial risk of breaking the three originals in the process of refactoring shared code (Project 2 already depends on Project 1's `scored_funds.csv` at a relative path; the root `requirements.txt` is already a known fragility per CLAUDE.md — one shared-dependency bump to deploy app #4 and apps #1/#2/#4 can silently fall into demo mode without any visible error). **You would be risking three working assets to build one uncertain asset whose main new property is higher regulatory exposure.** That is a bad trade on its face.

### 3.2 Where it eats 3× the estimated time (the integration tax nobody budgets)

The build is being mentally priced as "I already have the three pieces, just wire them together." That is the classic integration underestimate. The real cost lives in the *seams*, not the parts:

- **State threading across three originally-independent wizards.** Each app owns its own session-state model, its own input schema, its own page flow. Merging them means one coherent flow where the quiz output *feeds* the fund screen *feeds* the SIP sizer — that's a new orchestration layer and a new shared data contract, not glue.
- **Reconciling three different data assumptions.** Project 1 assumes a 7% risk-free rate and a 3-year lookback; Project 6 defaults to 12% expected return; Project 2's allocation has its own logic. Chained, these must be made *mutually consistent* or the integrated plan contradicts itself (allocation implies one return, sizer assumes another). Surfacing and resolving those contradictions is real analytical work.
- **The cross-asset handoff that the post itself admits is manual.** FINAL_POST.md line 39: *"The handoff between tools is manual today, not automated."* The entire *new* value of the integrated product is automating exactly that handoff — which means the hard part is 100% unbuilt, and the easy parts (the three tools) are 100% done. You are signing up to build only the expensive half.
- **Deployment + dependency union.** A fourth Streamlit app on the shared root `requirements.txt`, with the known "Streamlit Cloud installs root requirements, not per-project" gotcha. Every new transitive dependency is a chance to break a live demo.
- **The mandatory product-critique + compliance pass** (Veer's own workflow requires a `product-critique` pass on any UI before "done"). For a flow with this much regulatory surface, that pass is not a formality — it's another full iteration cycle.

Net: the parts are done; the product is mostly the seams; the seams are where the 3× hides.

### 3.3 Opportunity cost — the comparison that actually matters

Veer is targeting **Finance Analyst / GenAI roles**, time is scarce, and he has **unbuilt ideas that fill *visible, named* skill gaps**:

- **SQL is a known gap** (ABOUT_VEER: "SQL: conceptual only, not yet hands-on"). A hands-on SQL project (e.g. the SQL-backed portfolio tracker + Power BI idea in PROJECTS.md) converts a resume *weakness a recruiter can probe in an interview* into a demonstrated strength. The unified platform converts a strength (three finance+AI tools) into… a slightly more impressive version of the same strength, with a compliance asterisk.
- **RAG financial-document Q&A** is the single highest-signal "GenAI + finance" piece he doesn't have — it teaches embeddings/vector DBs, which is *exactly* what "GenAI-automation" job descriptions list, and which none of his current projects demonstrate. The unified platform demonstrates orchestration he can *already* claim by describing the manual chain.

**Marginal hireability of the unified build is low because the underlying capabilities are already visible in the three live tools.** "I built and deployed three finance+AI tools, and here's how they form a workflow" is a *sentence in an interview* — he gets ~80% of the narrative credit for the integration *without building it*, just by describing the PROFILE→PICK→SIZE flow (which the LinkedIn post already does). Building a NEW project adds a *new* capability to the portfolio. Integrating adds polish to existing capability. For a job search, breadth that closes a named gap beats depth that re-showcases an existing strength.

### 3.4 The "worse than three clean tools" failure mode, concretely

1. Veer refactors shared scoring/recommender code to feed the unified flow.
2. The root `requirements.txt` shifts to satisfy app #4.
3. One of the three live demos silently drops into demo/fallback mode (the `try/except`-guarded import pattern CLAUDE.md explicitly warns about) — no error, just degraded output a recruiter sees as "this is fake."
4. The unified app, being newest and most complex, has the most rough edges and the longest critique backlog.
5. Time runs out. He ships a half-integrated app, the three clean demos are now subtly broken, and the SQL/RAG gap is still open.

End state: **strictly worse than where he started.** This is not a tail risk; it is the *default* outcome of an ambitious integration under time pressure by someone who (his own notes say) "tends toward ambitious builds."

---

## 4. POSITIONS ON D1–D5

**D1 — Stack.** *Stay on Streamlit; do NOT migrate.* The three tools are Streamlit; rewriting into a "real" web stack (Next.js/React) to make the unified product feel premium is a second, hidden mega-project and a fresh source of bugs/deploy risk for zero hireability gain over a working Streamlit app. If a hub is built at all, a single extra Streamlit page (or a static landing page linking the three apps) is the ceiling. **Position: Streamlit, thin.**

**D2 — Depth.** *Thinnest viable: a hub/landing that explains the workflow and links the three existing live apps — orchestration by hyperlink, not by code.* Do NOT auto-pipe quiz output into the fund screener into the SIP sizer as one personalized engine — that auto-pipe is *both* the compliance trigger (§2.1) *and* the 3× time sink (§3.2). A "linked, not chained" hub captures the narrative ("here's the workflow") while keeping each tool legally standalone and each demo independently working. **Position: linked hub, not an integrated engine.**

**D3 — Portfolio.** *Build a NEW project instead — SQL-backed tracker first (closes the only named hard skill gap), RAG financial-doc Q&A second (highest GenAI signal).* The unified platform should lose the prioritization contest to either. If Veer wants *one* low-effort win from the existing tools, the linked hub (D2-thin) plus the already-written LinkedIn post is enough to harvest the "I chained three tools" story without a build. **Position: new gap-filling project > integration.**

**D4 — MVP.** If he overrides the dissent and builds: the MVP is **PROFILE → SIZE at the asset-class level only, with NO named funds in the chained path, stateless, fictional default persona, interstitial disclaimer.** Named-fund ranking stays quarantined in the standalone Project 1 demo. That MVP is defensible *and* small. Anything broader fails §2 or §3. **Position: asset-class-only, fund-naming quarantined, stateless.**

**D5 — Name.** Avoid anything implying a service or advice relationship: not "Wealth Platform," not "Advisor," not "Planner-as-a-service." Those names *assert* the exact regulated posture we're trying to avoid. Prefer a name that screams *educational/methodology/portfolio demo*: e.g. **"Finance Workflow Lab,"** **"Profile→Pick→Size: a methodology demo,"** or keep it under the portfolio umbrella as a labeled *case study*, not a product brand. The folder name `unified-wealth-platform` is itself a mild liability if it ever becomes public-facing copy. **Position: educational/methodology framing in the name; no "advisor/wealth-management" service language.**

---

## 5. THE BIGGEST RISK OVERALL

**That the project's single most attractive feature — "it feels like a real, personalized, end-to-end financial plan" — is simultaneously its single largest liability, and the two cannot be separated.** Every increment that makes the unified product more impressive to a recruiter (more personalized, names the actual fund, gives the exact rupee figure, feels like a finished plan) moves it further across the line from "educational simulator" into "unregistered personalized investment advice," and weakens the disclaimer defense. There is no version that is *both* maximally impressive *and* maximally safe — they trade off along the same axis. A portfolio piece is not worth even a small chance of a SEBI-finfluencer problem attached to Veer's real name during an active job search, especially when the *same career narrative* is already obtainable from three tools that are each individually clean. **The optimists will argue "it's just a portfolio demo, no one will care" — that is exactly the rationalization the 2025 rules were written to strip away, and it's a bet placed with Veer's professional reputation as the stake.**

---

## 6. IF YOU BUILD — THE NON-NEGOTIABLE GUARDRAILS

Ship none of these as "nice to have." All are gating.

1. **No named/ranked securities in the chained, personalized path.** Chain terminates at asset-class + methodology. Named-fund ranking lives only in the standalone Project 1 demo, framed as a screening engine. *(§2.2 — the single highest-leverage control.)*
2. **Stateless. Zero PII at rest. No accounts, no save, no email capture, no analytics on inputs.** Session-memory only; nothing written or transmitted except the in-memory LLM call. *(DPDP + SEBI.)*
3. **LLM is asset-class-only and never selects/ranks a security.** Preserve the existing deterministic-Python-only fund-selection wall as a compliance control. No prompt change that lets the model say "buy X."
4. **Pre-result interstitial disclaimer requiring acknowledgment:** educational *methodology* simulation, not advice, not personalized, Veer not a SEBI-registered IA, consult a registered adviser. Footer alone is non-compliant for a chained flow.
5. **Default to a fictional persona; never solicit the visitor's real financial data to see the demo.** Real-input entry is opt-in and still stateless.
6. **Framing throughout = "methodology / worked example," not "your plan."** Remove "your mix, your funds, your exact SIP" copy. Name the product educationally (no "advisor/wealth-management" service language).
7. **No expected-return figure presented as a forecast.** Keep the conservative 12% default and the explicit "planning estimate, not a guarantee" labeling.
8. **Do not refactor the three live apps' shared code until the unified app is proven in isolation.** Protect the working demos; verify all three originals still load (not in silent fallback mode) after every dependency change. If you can't guarantee that, build the hub as a *separate* app that only *links* to the three — never one that imports and re-deploys their internals.
9. **Run the full `product-critique` + a dedicated compliance review before calling it done** — treat the regulatory surface as a first-class review gate, not a footer.

---

*Dissent on record. If the council still votes BUILD over BUILD-THIN/DON'T, it should do so having priced in the category-change in regulatory posture (§2.1), the integration tax (§3.2), and the opportunity cost of a closed SQL/RAG gap (§3.3) — not by waving them away as "it's only a portfolio project."*
