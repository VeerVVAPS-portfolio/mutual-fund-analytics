# Finance Domain Critic — PROFILE → PICK → SIZE Integration

Reviewer lens: financial soundness and internal consistency of the chained logic. Sources read: P2 README + `risk_profiler.py`, `allocation_engine.py`, `prompts.py`, `fund_recommender.py`; P1 README; P6 README + `goal_calculator.py`, `fund_recommender.py`; `linkedin-post/FINAL_POST.md`.

---

## 1) VERDICT

**YES-BUT.** The three tools are individually sound, but as drawn the chain has a paradigm clash (one person-level mix vs. per-goal horizon allocation) and an undefined SIP-precedence rule that, if shipped naively, will produce internally contradictory advice a SEBI-RIA would flag. It is coherent enough to build **only if** you adopt an explicit reconciliation rule that makes goal-level horizon allocation the binding constraint and demotes the PROFILE mix to a default/sanity-check — not a separate allocation that competes with it.

---

## 2) ANALYSIS

### 2a. The paradigm clash is real, not cosmetic
PROFILE collapses age + horizon + goal + loss-reaction + debt into a single 0–100 scalar, then maps it to **one fixed mix** for the whole person (`BASE_ALLOCATIONS`: e.g. Moderate Conservative = 40/40/12/8). Crucially, **horizon is consumed into the scalar and then thrown away** — a 3-year-horizon Conservative and a person with no specific horizon can land on the same mix.

SIZE is the opposite paradigm: it is bottom-up and already takes a **per-goal `annual_return`** (`solve_goal(..., annual_return=...)`) and a per-goal horizon. Implicitly, each goal therefore has its *own* equity/debt posture: a 3-year goal should be debt/short-duration-heavy (you cannot ride out an equity drawdown 18 months before you need the money), a 15-year goal equity-heavy. P6's own `fund_recommender` encodes exactly this with `MIN_EQUITY_HORIZON_YEARS = 7`.

**The contradiction:** an "Aggressive" person (PROFILE says 75% equity) saving for a **2-year car** would, under a naive person-level overlay, get 75% equity on money they need in 24 months. That is the single most common retail mistake in the book — and the integrated product would be *manufacturing* it. Conversely a "Conservative" person (20% equity) saving only for a **20-year retirement** would be told to under-risk a two-decade horizon, guaranteeing real-terms erosion. A single profile-level allocation **cannot** be horizon-correct across a multi-goal plan. One of the two paradigms has to yield.

**Which wins:** horizon (goal-level) wins on the allocation *of each goal's corpus*. Risk profile wins only as (i) the **default glide-path aggressiveness** picked within each horizon band, and (ii) a **behavioural ceiling** — a self-declared panic-seller (REACTION_SCORES = "sell immediately") should have their long-horizon equity capped even if the horizon would justify more, because the worst outcome is capitulating at the bottom. Time horizon sets the *baseline*; risk profile *tilts within* it and *caps* it. It never overrides it upward on a short goal.

### 2b. The equity-only gap (this is the biggest honesty problem)
PROFILE recommends Debt/Gold/Alternatives slices. PICK ranks **equity only**. P2's *own* `fund_recommender.recommend_categories()` already returns `[]` when `equity_pct == 0` and only ever maps the **equity** percentage to Large/Flexi/Mid/ELSS categories. So **today, for a Conservative user, 80% of the recommended portfolio (55 debt + 15 gold + 10 alt) has reasoning text but zero implementable picks.** The integrated product inherits this hole and makes it worse, because SIZE's whole value proposition is "we tell you the *exact* number" — and then for the majority asset class of a short/medium goal, it tells you a number with nothing to put it in.

Three ways to handle it, in honesty order:
- **(Best) Name the slice honestly without faking a ranking.** For debt: "₹X/mo → short-duration / corporate-bond / liquid funds, or a bank RD / PPF for the sub-3-yr portion." For gold: "Sovereign Gold Bonds (SGB) or a gold ETF." State plainly: *"this tool ranks equity funds only; debt/gold are shown as asset-class actions, not ranked picks."* P6 already does exactly this caution pattern — extend it, don't abandon it.
- **(Acceptable) Generic instrument templates** with category-level rationale (no fabricated Sharpe/Alpha/rank for debt — those metrics are computed against NIFTY 50 and are **meaningless for debt funds**; printing them would be a fabrication).
- **(Dishonest — reject) Silently dropping** the non-equity slices so the page only shows equity, leaving the user thinking equity *is* the plan. Equally dishonest: piping debt funds through PICK's equity scorer and showing a Sharpe-vs-NIFTY number for them.

Verdict on the gap: **silently dropping = dishonest; faking metrics = worse.** The fix is to *label* the non-equity slices as un-ranked asset-class actions. Honesty here is also free credibility — it is the "manual handoff, not automated" move that the post already uses well.

### 2c. SIP-sizing coherence — there are TWO SIP numbers and no defined precedence
This is the sharpest internal inconsistency. **PROFILE already emits a SIP** (`monthly_sip_suggestion` = `income × 15%`, nearest ₹500 — a generic savings-rate heuristic, *not* goal-derived). **SIZE emits a different SIP** (sum of per-goal annuity-due solves). These two numbers will almost never match, and nothing in the chain says which governs. Shipping both side by side = the product visibly contradicting itself.

Resolution: **SIZE's goal-solved total is the real required SIP. PROFILE's 15% number must be demoted to a "starting savings-rate sanity check" or removed from the integrated flow.** The correct mental model:
1. SIZE computes the **required** monthly outflow per goal (need-based, deterministic).
2. The **allocation %** then *splits each goal's SIP across asset classes* per that goal's horizon-appropriate mix — **not** the person-level mix (see 2a).
3. Only the **equity rupees per goal** flow to PICK for fund selection.

So "split the total SIP by the profile allocation %, map the equity % to PICK" (the prompt's implied model) is **half right and half wrong**: splitting by allocation is correct; using the *person-level* allocation instead of the *per-goal* allocation is the error. Split at the **goal** level.

**What a real plan needs that the chain is missing:**
- **Lump sum vs SIP.** Everything assumes pure monthly SIP. Existing corpus / windfalls change the required SIP materially (FV of a present lump = `PV·(1+r)^n`, which reduces the annuity portion). P6 solves only the SIP leg.
- **Step-up reality.** P6 supports step-up SIP, but PROFILE's 15%-of-income and PICK don't know about it. A step-up plan needs an income-growth assumption that ties to the affordability projection (P6 has salary growth — wire it through).
- **Tax.** No ELSS lock-in handling beyond a category label; **no LTCG** treatment. Post-2024 India: equity LTCG is **12.5% above ₹1.25 L/yr**; debt funds (post-Apr-2023) are taxed at **slab** with no indexation. A goal's *required corpus* should arguably be grossed up for exit tax, and "expected return" should ideally be after-cost (TER) — none of this is modelled. At minimum, disclose returns are pre-tax/pre-exit-load.
- **Rebalancing.** A glide path implies the equity/debt split **changes as the goal nears** (de-risk in the final 2–3 years). The current tools are static-at-inception. The honest MVP move: state the *target* allocation now and add a one-line "de-risk to debt in the last 3 years" rule, even if not yet automated.
- **Emergency fund / protection precedence.** P6 already checks emergency fund, FOIR, insurance. Good — but the integrated flow must **sequence protection before goal-SIPs** (P6's funding_sequencer does priority ordering; make "6-month emergency fund + adequate term/health cover" a hard gate *before* any goal SIP is shown as affordable). Investing aggressively over an unfunded emergency buffer or with high-interest debt outstanding is the classic advisor red flag — and PROFILE's own DEBT_SCORES already knows high debt matters.
- **Return-assumption consistency.** P6 pre-fills 12% equity (good, it walked back the Excel's 16–17%). PROFILE's LLM reasoning must not narrate a *different* expected return, or the two screens disagree. Pin one assumptions table, shared across all three.

### 2d. Where a SEBI-RIA would wince
- 75% equity on a 2-year goal (the paradigm clash, untreated).
- Showing debt/gold rupee amounts with **no instrument and no caveat** (the equity-only gap).
- A panic-seller routed into a high-equity glide path with no behavioural cap.
- Any **fabricated Sharpe/Alpha for non-equity** funds.
- Return assumptions presented as expectations without "pre-tax, pre-cost, not guaranteed, past performance ≠ future."
- The LLM prompt literally says *"You are a SEBI-registered financial advisor"* (P2 `prompts.py`). That is a **persona instruction**, but if any user-facing string echoes it, it's a misrepresentation under SEBI's 2024–25 finfluencer/RIA rules. **Strip that phrasing from anything renderable;** keep the "educational, not advice, not SEBI-registered" disclaimer the post already uses.
- **Guardrails that keep it correct:** (1) deterministic spine — every number traces to a formula, LLM only explains "why" (already the design intent — enforce it: LLM must never emit a number that isn't echoing an upstream computed value); (2) horizon-binding allocation; (3) protection/emergency-fund/high-interest-debt hard gate before goal SIPs; (4) no fabricated metrics for asset classes PICK doesn't score; (5) one shared, visible assumptions table; (6) prominent pre-tax/not-advice disclosure.

---

## 3) RECONCILIATION RULE (prescriptive)

**Goal-level horizon allocation is authoritative for each goal's corpus. The PROFILE risk mix is demoted to a tilt-and-cap, never a competing allocation, and PROFILE's income-based SIP is dropped in favour of SIZE's goal-solved SIP.**

Concrete algorithm:

1. **SIZE first.** For each goal, solve the required monthly SIP via annuity-due (existing P6 math). This total is *the* required savings number. Discard PROFILE's `income × 15%` figure (or show it only as a labelled "current savings-rate benchmark," never as the plan).

2. **Assign each goal a horizon band → baseline equity range** (industry-standard glide path):
   - **< 3 yr:** 0–10% equity (debt/liquid/RD/PPF-dominant). No equity fund pick.
   - **3–7 yr:** 20–40% equity (hybrid/large-cap tilt).
   - **7–15 yr:** 50–70% equity.
   - **> 15 yr:** 70–85% equity.

3. **PROFILE tilts within the band, and caps the top.** Map the risk label to a position inside each band:
   - Conservative → bottom of band; Aggressive → top of band.
   - **Behavioural cap:** if REACTION = "sell immediately," cap equity at the band's midpoint regardless of horizon. PROFILE never pushes a short goal *above* its band — it only moves within it and can pull it down.

4. **Split each goal's SIP by its own (tilted) allocation.** Equity rupees, debt rupees, gold rupees per goal.

5. **Route only the equity rupees to PICK.** Category by horizon/risk (Large Cap core; Flexi/Mid as risk rises — P2's existing `recommend_categories` logic, but driven by the *goal's* band, not the person's label). Debt/gold rupees → **named asset-class actions, explicitly un-ranked.**

6. **Aggregate up** for a household view (sum across goals) and *then* show the person-level realised mix — and use PROFILE's person-level target only as a **sanity check**: "your blended mix across all goals is 48% equity; your risk profile suggests ~40% — the difference is because your long goals justify more equity." That sentence turns the clash into an *explanation*, which is exactly the product's stated "LLM explains why" value.

7. **Gate before all of the above:** emergency fund (≥6 mo expenses) + adequate term/health cover + no high-interest debt. P6 already computes these; make them blocking, not informational.

One line: **horizon sets the baseline allocation per goal, risk profile tilts and caps within it, SIZE owns the SIP number, PICK only ever sees the equity slice, and the person-level mix is an output to explain — never an input that overrides a goal's horizon.**

---

## 4) POSITIONS ON D1–D5

- **D1 (Stack):** Finance-neutral, but it constrains correctness. Keep the **deterministic Python spine** (P6's solvers, P1's scoring) as the source of every number; the LLM stays a "why" layer only. Whatever stack, **one shared assumptions module** (returns, inflation, tax, risk-free) imported by all three — today P1 uses 7% risk-free, P6 uses 12% equity, P2's LLM can free-narrate a third number. That inconsistency is a *finance* bug, not a stack preference. So: stack choice is the engineers' call; the non-negotiable is a single shared, version-pinned assumptions table.

- **D2 (Integration depth):** Go **deep enough to enforce the reconciliation rule**, no deeper. The *minimum financially honest* integration is: PROFILE → per-goal banding → SIZE solve → equity-slice-to-PICK, with the household sanity-check sentence. A shallow "three tabs that share a CSS theme" integration is *not* coherent — it would show two SIP numbers and a person-level mix that contradicts the goals, which is worse than three honest standalone tools. If you can't build the binding rule yet, **keep them separate and link them** (which the post already, correctly, frames as "manual handoff, not automated").

- **D3 (Portfolio strategy):** **Goal-bucket / glide-path**, explicitly. Reject single-portfolio MPT-at-the-person-level for this audience — it's the root of the paradigm clash. Bucketing is also what NISM V-A / real Indian advisory practice teaches, so it's on-brand for Veer's credibility. Add a static target glide path now; automate de-risking later.

- **D4 (MVP):** The smallest coherent slice = **one goal, end to end, with the binding rule visible:** enter a goal (target + horizon) → horizon band sets baseline equity → risk quiz tilts within band → SIZE solves the SIP → split into equity/debt/gold rupees → equity → PICK's ranked funds; debt/gold → named-but-unranked actions; protection gate up front; one assumptions table; pre-tax/not-advice disclosure. **Defer:** lump-sum handling, step-up, automated rebalancing, tax optimisation, multi-goal sequencing (P6 has it — wire it in v2). Ship the *honest narrow path* before the *broad shallow one*.

- **D5 (Name):** Finance-credibility test only. "PROFILE → PICK → SIZE" describes the *mechanism* and is honest, but as a *product* name it under-sells the integrity spine. Prefer a name that signals **goal-based + evidence-based** without implying regulated advice — avoid "Advisor," "Robo-Advisor," "Wealth Manager," or anything SEBI-RIA-coded (regulatory risk + overpromise). Something like *"Goal Stack"* / *"PlanGrid"* / *"Coherent"* with the tagline carrying "profile → pick → size." Keep the verb-chain as the subtitle; it's a genuinely good explanation of what it does.

---

## 5) BIGGEST DOMAIN RISK

**Horizon-blind allocation: applying one person-level risk mix to goals of different time horizons — putting high equity on near-term money (or under-risking long-term money) — and presenting it with the authority of an "exact, solved" number.** It is the most common real-world retail mistake, it directly contradicts SIZE's own per-goal `annual_return`/7-year-cutoff logic, and the product's "deterministic, exact" framing makes a *wrong* allocation look *more* trustworthy than a hand-wavy one would. This single flaw can turn the integrity spine into a liability. The reconciliation rule in §3 exists specifically to neutralise it.

---

## 6) TOP 3 RECOMMENDATIONS

1. **Make horizon authoritative; demote the profile mix to a tilt-and-cap (§3).** Per-goal horizon band sets baseline equity; risk profile only tilts within and caps the top (panic-sellers capped at band midpoint). Kill PROFILE's `income × 15%` SIP — SIZE's goal-solved number is the only SIP shown. Surface the person-vs-blended-mix difference as an *explanation*, turning the clash into the product's headline "why."

2. **Close the equity-only gap honestly.** Split each goal's SIP into equity/debt/gold rupees; route only equity to PICK; show debt/gold as **named, explicitly un-ranked asset-class actions** (SGB/gold-ETF; short-duration/corporate-bond/PPF/RD). **Never** fabricate Sharpe/Alpha for non-equity funds (those metrics are computed vs NIFTY 50 and are meaningless off-equity). Print the line "this tool ranks equity funds only."

3. **One shared, version-pinned assumptions table + a protection/debt gate + disclosure hygiene.** Unify risk-free (P1=7%), equity return (P6=12%), inflation, and add a tax/cost disclosure (equity LTCG 12.5% > ₹1.25 L; debt at slab; returns pre-tax/pre-TER, not guaranteed). Make P6's emergency-fund / FOIR / insurance checks a **hard gate before any goal SIP is shown as affordable**, and **strip the "You are a SEBI-registered advisor" persona text** from anything user-facing — keep only the "educational, not advice, not SEBI-registered" line.
