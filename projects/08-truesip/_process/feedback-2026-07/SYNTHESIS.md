# TrueSIP — Feedback Council Synthesis (2026-07-01)

Veer gave a round of feedback on the deployed-ready TrueSIP after using it: one overall ask (the tool "feels static" — wants modern SaaS motion) plus seven specific per-section complaints. Per Veer's instruction we ran the **same council-then-build process** used to build the product (DMAIC): a critique council debated the feedback and produced findings; this file is the chair's synthesis. Build follows in `PLAN.md`.

**Council roster (model-delegated, mirrors the original `_process/council/` roster):**

| Member | Model | Lane | File |
|---|---|---|---|
| UX & Motion Design | Opus | motion-under-Streamlit, hierarchy/depth, zero-state, ordering | `round1/ux-motion.md` |
| Finance Domain | Opus | per-goal equity category by tenure & importance (the engine change) | `round1/finance-domain.md` |
| Streamlit Technical Feasibility | Sonnet | exact fix mechanisms; what motion is buildable without jank | `round1/streamlit-tech.md` |
| Compliance / SEBI | Sonnet | does small-cap-per-goal / jargon-simplification touch the two-mode design | `round1/compliance.md` |
| Mechanical inventory | Haiku | exhaustive catalog of sliders/charts/jargon/buttons/CSS | `round1/inventory.md` |

The **main session (Opus) is the orchestrator/chair** — it sequenced the council and resolved the tensions; no leaf agent invoked another (same contract as the build).

---

## 1. Feedback → confirmed root cause (all verified in code)

> Numbering note: Veer's "Step 1/2/3/4" = code's `step` 0/1/2/3.

| # | Feedback | Root cause (file:line) | Severity | Verdict |
|---|---|---|---|---|
| 1 | Step-1 shows a shortfall the moment the tool opens; want initial value zero | `view_diagnosis` renders the shortfall reveal whenever `valid` — True on first load (preset ₹1Cr, current_sip 0 → "~100% short"). `views.py:224-226` | **P1 trust** | Confirmed — false first-paint alarm |
| 2 | "Build my full plan" button wraps like a dice | Next button sits in the 1/6-width `col_next` of `st.columns([1,4,1])`; label too long for the column. `app.py:215`, label `app.py:266` | **P1** | Confirmed — container bug, not the label |
| 3 | Step-2 4th question ends "…." / not fully visible | Reaction question label literally ends in "…" by design (`risk_profiler.py:201`); its options are 49 chars → wrap on narrow widths (`inventory.md §5`) | **P2** | Confirmed — content + wrap, not truncation |
| 4 | Step-2 donut hover shows "Equity 75 75%" | `_allocation_donut` `go.Pie` has no `hovertemplate`; Plotly default hover = label+value+percent, and value==percent. `views.py:379-384`. Hits **all** donuts (base-mix + every goal card) | **P2** | Confirmed |
| 5 | Step-3 percent sliders all show 0%, "not working" | `format="%.0f%%"` applied to **decimal** values 0.0–0.20 → `printf(0.08)="0%"`. 5 sliders: `views.py:434,438,447,453,797` | **P0 broken** | Confirmed — real functional bug |
| 6 | Step-4 only suggests one equity scheme; goals of different importance & tenure need different categories | `equity_category_for` is a 3-bucket horizon step function (Large→Large&Mid→Flexi); 8y & 14y both → Large&Mid; 16y & 25y both → Flexi. No importance concept. Uses 3 of 10 seed categories. `planning_engine.py:359-385` | **P1** | Confirmed — engine change |
| 7 | Explore: Sharpe/Jensen's Alpha/Consistency confusing; sliders should sum to 100 | Jargon labels `views.py:960-967`; sliders are independent 0–100 but label falsely claims "must sum to 100% — we normalise for you" `views.py:955-974` | **P1** | Confirmed |
| 8 | Advanced: FOIR unclear; slider broken; graph in Millions | FOIR jargon `views.py:854-857`; loan_rate slider same format bug `views.py:797`; `_cashflow_chart` y-axis auto-formats to "M" (no lakh/cr) `views.py:907-913` | **P0/P1/P1** | Confirmed |
| — | Overall "feels static" | `theme.py` has **zero @keyframes, only 2 transitions** (buttons, step bar). Literally accurate. | **P1** | Confirmed |

The Haiku inventory wrongly concluded the sliders "render correctly" (it believed `"%.0f%%" % 0.08` → "8%"). Overridden and annotated in `round1/inventory.md`; the UX, Tech and Finance critics + orchestrator independently confirmed the bug. (A clean demonstration of why the cheap model is used only for enumeration, and its conclusions are cross-checked.)

---

## 2. Unanimous / strong convergence

- **Ordering — correctness → hierarchy/depth → motion (UX + Tech, unopposed).** Four of the seven complaints are *broken output* (0% sliders, millions axis, donut double-number, question wrap), not missing animation. Polishing broken controls "gilds a bug," and the fixes restructure the very DOM the motion layer targets (the diagnosis reveal moves behind a button; the total-SIP becomes a hero). Motion is layered on a stable, correct UI last.
- **The tasteful motion subset == the rerun-safe subset (UX + Tech converged independently).** Streamlit reruns the whole script on every widget touch and this app re-scores the quiz / re-solves SIPs live, so **any mount/entrance animation re-fires on every interaction**. SHIP: hover microinteractions, resting elevation/depth, `transition` on genuine state change, and exactly **one** shimmer skeleton (the LLM `explain_plan` wait only). REJECT: entrance/`fadeUp`, staggered reveals, number count-up, Plotly chart animations, page/step transitions, ripples. The stuff that would flash is also the stuff that reads as cheap — constraint and taste point the same way.
- **The "only one scheme" fix is the horizon ladder (Finance), and it's compliance-neutral (Compliance).** A category string ("Small Cap Fund") is an AMFI/SEBI category, the same legal object class as "Large Cap Fund" — Mode A safe. The fix is *more* category resolution with *more* volatility caveats, not hiding categories.
- **No new compliance gate failures.** All changes are safe or safe-with-a-guardrail. The two-mode wall (personalized plan never names a fund; Explore is the only namer and reads no profile/goal state) stays intact.

---

## 3. The three BUILD MANDATES the council re-affirmed (must not regress)

1. **Deterministic money only** — every SIP/₹ from `goal_calculator`; the LLM explains, emits no number.
2. **Horizon-authoritative equity %** — a goal's equity *weight* is set by its horizon band; risk label (and now *importance*) is only a tilt/nudge. **Importance may move the equity SUB-CATEGORY ±1 notch, never the equity % or the band.** (Finance Q2b; the sacred line.)
3. **Two-mode compliance** — personalized plan carries asset class + equity **category string** at most; only the opt-in, neutral, profile-blind **Explore Funds** names/ranks funds. `view_explore` must keep reading **zero** plan/profile session keys.

And one new **P0 guardrail** the Finance critic surfaced:
4. **Category choice must NEVER change the return assumption.** Equity stays a flat 12% across caps. Coupling Small Cap → higher return would *shrink* the required SIP on the *riskier* sleeve (backwards) and break self-check `[B]` (`r_near < r_far`). Category = *which funds to browse*; the % and SIP are untouched. Add a code comment at `RETURN_ASSUMPTIONS`/`equity_category_for` so a future editor doesn't "helpfully" couple them.

---

## 4. Tensions resolved by the chair

The council was highly convergent; only two small cross-lane tensions remained, both pure UX-taste calls (Tech confirmed both options are technically feasible). The Round-2 UX pass was rate-limited (subagent 529 → session limit), so the chair resolved them from the members' complete Round-1 positions, as the original council did with its "resolved by chair" items.

### Tension A — Explore weight sliders ("should sum to 100")
- **UX:** keep 3 symmetric independent sliders; relabel "How much should each metric count?"; show a live normalized caption; reject auto-balancing.
- **Tech:** "2 sliders + computed third" (Consistency = `max(0, 100−Sharpe−Alpha)`), which literally sums to 100 but is asymmetric (one metric can't be set directly; a dead zone when the two exceed 100).
- **Both reject auto-balancing sliders** (in Streamlit they require writing other widgets' state + a second rerun → a visible two-step "jump" that *feels broken* — the opposite of the goal, and exactly the "sliders auto-adjust" reading of Veer's words).

**RULING → UX's symmetric reframe, hardened with Tech's explicit-100 instinct.** Ship **3 independent 0–100 sliders** (symmetric — any metric can be emphasized directly, no derived-metric dead zone) + a **prominent live caption that always sums to exactly 100%**: `Your weights → Sharpe 45% · Alpha 30% · Consistency 25% (always totals 100%)`, computed from the normalization the code already does (`ws/total_w`). Remove the false "must sum to 100% — we normalise for you" label. This gives Veer exactly what he asked for — *he never calculates the sum; the displayed weights always total 100* — while staying symmetric and honest. We deliberately do **not** make the raw slider tracks physically rebalance (that is the janky auto-balance path both critics rejected); the reasoning is documented so it can be revisited if Veer specifically wants moving tracks.

### Tension B — Diagnosis reveal (kill the instant "100% short")
- **UX:** explicit **"Check my SIP →"** button + instructional empty state; argues it's also the one *safe* user-triggered entrance animation.
- **Tech:** auto-reveal the moment any field is edited (no button, "one fewer click").

**RULING → UX's explicit button + empty state.** It (a) serves the ₹0 "haven't started yet" user — the exact person the tool targets — who presses the button with 0 and still gets "here's what it'd take"; (b) avoids Tech's failure mode where the reveal (and its entrance animation) re-fires *mid-edit* on every subsequent rerun; (c) turns the reveal into an *earned* moment — the single place a gentle fade-in is legitimate because it fires on a click, not on mount/rerun. Implement with Tech's session-state mechanism: a `diagnosis_revealed` flag, set on button press, **reset when the preset chip changes**. Keep the `has_goal` Next-gate independent so advancing still works whether or not they checked.

---

## 5. The one decision for Veer — goal "importance" input

Finance and Compliance both cleared an optional per-goal **importance** level (Essential / Important / Aspirational) that nudges the equity **sub-category ±1 notch** and nothing else (never the %, never a named fund; framed as context, never "we recommend"). It directly answers the "different importance" half of Veer's feedback.

But Finance is explicit: **the widened 6-band ladder alone already fixes the literal "only one scheme" complaint with zero new input** — so importance must **not block** the ladder. Hence the decision is *scope*, not soundness:
- **Add now** — ship the ladder + the importance selector together (fullest answer to the feedback; +one small UI control + a ±1-notch clamp rule + caveat copy).
- **Defer** — ship the ladder now (different-tenure goals immediately show different categories); add importance as a fast P1/M follow-on.
- **Skip** — ladder only.

→ Taken to Veer before the build starts.

---

## 6. Direction (locked)

Fix in three passes — **(1) correctness/trust** (the 5-slider format bug, millions→lakh/cr on *all* charts, donut hover on the helper, the diagnosis action-gate, the button-wrap container fix, the question wording/wrap), **(2) hierarchy & depth** (elevation system, total-SIP hero, single restyled disclaimer, clearer step bar, jargon→plain-language captions with adjacent "past performance" caveats, the explore weights reframe), **(3) motion** (hover-lift/glow, state transitions, the one LLM skeleton, focus-visible ring) — plus the **engine ladder** (6 bands, Small Cap gated >20y) and, pending Veer, the **quarantined importance nudge**. Guardrails from §3 baked in. Gates: engine `_selfcheck` stays green, finance-correctness + compliance auditors re-run (both audits currently document the old 3-bucket mapping and must be amended), and a browser UX pass. Full spec in `PLAN.md`.
