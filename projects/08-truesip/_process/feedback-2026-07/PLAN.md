# TrueSIP — Feedback Implementation Plan (2026-07-01)

Derived from `SYNTHESIS.md` + the five `round1/` findings. Ordered **correctness → hierarchy/depth → motion**, with the engine ladder first (UI consumes its output). Every item cites file:line and the exact change; guardrails are inline. Owner = the existing build-team persona (`.claude/agents/`) at its model tier.

**Sequencing (avoids two agents editing the same file):**
`integration-logic-architect (Opus)` does the engine (`planning_engine.py`, `risk_profiler.py`) → **then** `streamlit-ux-builder (Sonnet)` does all UI (`views.py`, `theme.py`, `app.py`) → **then** `finance-correctness-auditor (Opus)` ∥ `compliance-guardrail-checker (Sonnet)` gate, + `python shared/planning_engine.py` self-check, + a browser UX pass. If subagents are rate-limited, the orchestrator executes the same spec in-session against these exact snippets and runs the same gates.

---

## PASS 0 — ENGINE: widen the equity-category ladder  ·  owner: integration-logic-architect (Opus)  ·  P1

**File:** `shared/planning_engine.py`. Replace the 3-bucket `equity_category_for` (L359-385) with the 6-band ladder (Finance §2). Add `SMALL_CAP = "Equity Scheme - Small Cap Fund"` to the category constants (L353-356); `MID_CAP`, `FLEXI_CAP`, `LARGE_AND_MID_CAP`, `LARGE_CAP` already exist.

**Ladder (default "Important" column — all strings exist in the seed & `data_store.CATEGORIES`):**

| Horizon | equity % band (UNCHANGED) | category (default) |
|---|---|---|
| < 3y | 0–10% | `None` (sleeve too thin to route) |
| 3–7y | 20–40% | Large Cap |
| 7–12y | 50–70% | Large & Mid Cap |
| 12–15y | 50–70% | Flexi Cap |
| 15–20y | 70–85% | Flexi Cap |
| > 20y | 70–85% | Mid Cap |

New cut points 12/15/20y split the two over-broad buckets so 10y≠14y and 16y≠25y now differ. **Small Cap is gated to >20y AND non-Essential** (only reachable via the Aspirational notch — see Pass 4). Everything still flows through `_resolve_category` (L388-408) for seed-validation + broad-market fallback. Do **not** auto-route ELSS/Focused/Value/Dividend-Yield off horizon (they need a tax/style signal, not "it's in the CSV").

**P0 GUARDRAIL (Mandate #4, Finance Q2c):** cap choice must NOT touch `RETURN_ASSUMPTIONS` (equity stays 12%) or `blended_expected_return`. Add a one-line comment at both `RETURN_ASSUMPTIONS` (L161-165) and `equity_category_for` stating "category affects only which funds to browse — never the return assumption or the SIP." This keeps self-check `[B]` (`r_near < r_far`) green.

**Acceptance:** `python shared/planning_engine.py` still prints ALL SELF-CHECKS PASSED; a multi-goal plan with horizons {5, 10, 14, 25}y now yields ≥3 distinct categories; no goal's `equity_pct` leaves its band ([D] invariant).

---

## PASS 1 — CORRECTNESS / TRUST  ·  owner: streamlit-ux-builder (Sonnet)  ·  P0/P1

### 1.1 Percent sliders show "0%"  ·  **P0**  ·  `views.py:434,438,447,453,797`
Root: `format="%.0f%%"` on decimal 0.0–0.20 → printf rounds to "0%". Fix (Tech Approach A): slider in **integer percent units**, divide by 100 on store — downstream keeps receiving decimals, no other change.
```python
# pattern for L434-441 sliders (salary_hike, expense_inflation, inflation_rate, step_up):
_disp = st.slider("Expected annual salary hike", 0, 20,
                  int(round(float(income_prev.get("salary_hike_pct", 0.08)) * 100)), 1,
                  format="%d%%")
salary_hike_pct = _disp / 100.0
# expense_inflation/inflation_rate: max 15.  step_up: max 20, default 0.
```
Loan interest (L797, needs 0.5% granularity): float percent range with a now-correct format:
```python
_disp = st.slider("Loan interest", 0.0, 20.0,
                  round(float(adv_prev.get("_loan_rate", 0.09)) * 100, 1), 0.5, format="%.1f%%")
loan_rate = _disp / 100.0
```
**Acceptance:** every slider shows its true % (8%, 6%, 9.0%…) and stored decimals are unchanged (`round(0.08*100)/100 == 0.08`).

### 1.2 Charts in Millions → lakh/crore  ·  **P1**  ·  `_cashflow_chart` (L894-914) + `_sip_split_bar` (L729-751)
`tickprefix="₹"` lets Plotly auto-scale to "M". Replace with `tickvals`+`ticktext` built from the existing `_lakh_cr()` helper (Tech Fix 3 snippet) and add `customdata` hover in `₹ L/Cr`. **Do all money-axis charts** (UX §5) so cards ("₹1.2 Cr") and the chart beside them tell one unit story. `_sip_split_bar` already hovers in ₹ — just confirm its axis isn't showing "M".
**Acceptance:** y-axis reads `₹40.0 L`, `₹1.20 Cr`; no "M" anywhere; hover matches.

### 1.3 Donut hover "Equity 75 75%"  ·  **P2**  ·  `_allocation_donut` (L379-384)
Add to the `go.Pie(...)`: `hovertemplate="%{label}: %{percent}<extra></extra>"` (values are already percentages; `%{percent}` renders the same number once). One fix → propagates to the base-mix donut (L327) **and every goal-card donut** (L677).
**Acceptance:** hover reads "Equity: 75%".

### 1.4 Diagnosis zero-state — gate the verdict  ·  **P1**  ·  `view_diagnosis` (L224-226)
Ruling (SYNTHESIS §4B): explicit **"Check my SIP →"** button + instructional empty state; no verdict on first paint. Mechanism (Tech Fix 6): `st.session_state["diagnosis_revealed"]` set on button press, **reset when the `preset` chip changes** (`_last_preset` compare). Keep goal presets pre-filled (useful scaffolding). Empty-state copy: *"Enter your current SIP (₹0 is fine) and hit Check my SIP — we'll show whether you're on track."* Keep `has_goal`/Next-gate independent of the reveal.
**Acceptance:** fresh load shows the empty state, no "% short"; button reveals verdict; works with current_sip = 0.

### 1.5 "Build my full plan" wraps  ·  **P1**  ·  `_nav_buttons` (app.py L215-227)
Keep the label (it sells the payoff). Add `use_container_width=True` to the Next button, AND `white-space: nowrap !important;` to the `.stButton > button` block in `theme.py` (belt-and-suspenders; shared across steps — verify "← Back"/"See My Plan →"/"← Revise Goals" still render on one line at 375px).
**Acceptance:** CTA is one line on the diagnosis screen at desktop and 375px; other steps' buttons unaffected.

### 1.6 4th risk question "…." + long options  ·  **P2**  ·  `risk_profiler.py:201`
Reword the reaction label off the trailing ellipsis: `"If your portfolio dropped 20% tomorrow, you would…"` → **"If your portfolio dropped 20% tomorrow, what would you do?"**. Options are content, keep them; the depth/spacing pass (2.x) improves their wrap. (Pure content edit — no scoring change; `REACTION_SCORES` keys are unchanged, so `compute_risk_score` still maps.)
**Acceptance:** no trailing "…"; question reads complete.

---

## PASS 2 — HIERARCHY, DEPTH & PLAIN LANGUAGE  ·  owner: streamlit-ux-builder (Sonnet)  ·  P1/P2

### 2.1 Elevation system + total-SIP hero  ·  `theme.py` + `views.py:593`
Add resting `box-shadow` to `[data-testid="stMetric"]`, bordered containers, expander header (UX §A/§E). Promote the `### Total SIP:` line to a proper **hero** — Space Grotesk, larger, accent-tinted card — it's the product's payoff and renders as a plain h3 today. Elevate results above chrome (disclaimers/captions).
**Guardrail (Compliance §3c + UX defence):** the per-card "Explore ranked … funds →" button **stays `type="secondary"`, un-animated, equal-emphasis** — never primary/branded/highlighted, or the plan→card→fund path visually assembles the forbidden trifecta.

### 2.2 Single, restyled disclaimer  ·  `views.py:606-613, 932-936`
Demote the repeated full-width `st.warning` disclaimers to one smaller consistently-styled callout. **SACRED:** it must still appear **before** any fund/category mention (restyle in place; never move it after the fund content or into an expander). The Explore banner's "**Past performance does not indicate future results**" (L935) is load-bearing — do not shrink/move.

### 2.3 Step bar clarity  ·  `app.py:182-194`
Surface the segment labels (`["Goals","Profile","Income","Your Plan"]`, already in code) + a numbered active pill so the 4-step shape is always legible. No motion (color-transition on step change already exists).

### 2.4 Jargon → plain language (with adjacent caveats)  ·  `views.py:960-967, 989-998, 854-860`
Use Compliance's approved rewrites (Q5) — plain label + the "**Past performance does not indicate future results**" caveat travelling **locally** with each metric (not just the banner):
- **Sharpe** → "Return per unit of risk" — *how much return for each unit of ups-and-downs; higher = smoother ride for the same return.*
- **Jensen's Alpha** → "Manager's track record above expected" — *return added beyond what the market's own movement would produce (after adjusting for beta); positive = added value, historically.*
- **Consistency** → "How often it beat its benchmark" — *share of rolling periods it outperformed; 80% ≈ 4 of 5 periods.*
- **FOIR** → "Debt burden as % of income" — *EMIs + fixed obligations ÷ income; lenders view ~50–55%+ as stretched — a planning benchmark, not loan eligibility.*
Finance §Q2d accuracy traps: don't call Alpha simply "extra return"; don't imply Consistency measures *size* of outperformance; keep equity metrics inside the Explore/equity context (never next to a debt/gold note).

### 2.5 Explore weights reframe (Tension A ruling)  ·  `views.py:955-974`
Keep 3 independent 0–100 sliders (symmetric). Relabel "Scoring weights (must sum to 100%…)" → **"How much should each metric count?"**. Remove the false normalize label. Add a prominent live caption from the existing normalization: **`Your weights → Sharpe 45% · Alpha 30% · Consistency 25% (always totals 100%)`**. No auto-balancing. Keep the `ws/total_w` normalization as the source of the caption %s.

---

## PASS 3 — MOTION (the rerun-safe subset only)  ·  owner: streamlit-ux-builder (Sonnet)  ·  P2

Add to `theme.py` CSS (all `:hover`/`transition`/resting shadow — **none replay on rerun**; Tech + UX converged):
- **Card/metric hover-lift + accent glow** — `transition: transform 150ms, box-shadow 150ms`; `:hover { transform: translateY(-2px); box-shadow: 0 8px 24px rgba(0,0,0,.5), 0 0 0 1px var(--accent-glow); }`. Scope carefully to bordered containers/metrics (the `stVerticalBlock>stVerticalBlock` selector is fragile — don't let it bleed onto every column).
- **State-change transitions** — metric-delta / FOIR-level / affordability callout colors (element persists, only class/color changes → fires on real change, not every rerun).
- **`:focus-visible` ring** on buttons/inputs (2px accent, offset) — accessibility + trust; currently missing.
- **ONE shimmer skeleton** — for the LLM `explain_plan` wait only (`views.py:622`), via `st.empty()` + a `@keyframes shimmer` scoped to the placeholder that's immediately replaced (Tech skeleton snippet). Keep `st.spinner` for `build_plan` (too fast to skeleton). **No** skeleton on the quiz (scores in <1ms).

**REJECT (documented, do not build):** entrance/`fadeUp`, staggered card/row reveals, number count-up/odometer, Plotly chart animations, step/page transitions, button ripple, ambient/looping glows — all re-fire on every widget rerun in this live-recompute app.

**Small "AI-tell" cleanups while in the CSS (UX §5):** swap emoji check-marks (`delta="✓"` L246, `"Covered ✓"` L888) for a Bootstrap Icon/styled span; tighten the `.stButton` primary/secondary cascade so hover states don't leak between button types.

---

## PASS 4 — OPTIONAL: goal "importance" nudge  ·  PENDING VEER  ·  engine (Opus) + UI (Sonnet)  ·  P1/M

Only if Veer chooses "Add now". **Engine** (`planning_engine.py`): add optional `importance` to each goal; `notch = {Essential:-1, Important:0, Aspirational:+1}` moves the category **≤1 step along the ladder, clamped at the ends** — and touches **nothing else** (`equity_pct`, `asset_split`, `blended_return`, band all identical). **UI** (`views.py` `_render_goal_editor` L477-510): a compact per-goal `selectbox`/segmented control (default **"Important"**), so users who ignore it are unaffected. **Card copy (Compliance):** context, never verdict — "This goal (long horizon, high importance) sits in the **Flexi Cap** band — explore those funds below." Never "we recommend". When the ladder shows Small/Mid Cap, add the one-line volatility caveat on the card (Finance §Q2a). Disclaimer stays **above** any importance UI block.
**Acceptance:** self-check green; Essential/Aspirational move only the category (assert `equity_pct` identical across the three importances for a fixed horizon); no named fund anywhere in the plan output ([E]).

---

## GUARDRAILS CHECKLIST (compliance-guardrail-checker re-runs `audits/compliance.md` 1a–2b after build)

- [ ] `view_explore` still reads **zero** plan/profile session keys (only `explore_category`, `explore_reset_weights`, `_explore_weights`). Adding any plan key (risk_label, a goal SIP) breaks Mode B neutrality — effect, not intent, is judged.
- [ ] No named scheme (scheme_name/AMC/ISIN) anywhere in the personalized plan; `views.py:693` stays "…→ **Large/Small Cap** funds", never a fund name.
- [ ] Every renamed metric carries the "Past performance…" caveat adjacent (not only in the banner).
- [ ] The pre-fund SEBI disclaimer stays before any fund/category mention on every screen.
- [ ] No countdown/urgency element; the Explore hand-off button stays secondary + un-animated.
- [ ] **Fix pre-existing (Compliance Issue A):** soften `views.py:632` "Automate the SIPs at the amounts above" → "Review the SIP amounts above with a SEBI-registered adviser/distributor who can set them up" (directive-adjacent copy; do while in here).

## GATES (all must pass before "done")
1. `python shared/planning_engine.py` → ALL SELF-CHECKS PASSED (ladder/importance invariant-safe by construction).
2. finance-correctness-auditor + compliance-guardrail-checker re-run → PASS, and **amend both audits** (`_process/audits/*.md`) to record the 6-band ladder (they document the old 3-bucket mapping).
3. Browser UX pass (the `ux-audit` skill or a manual click-through): sliders show real %, no "M" on charts, no first-paint shortfall, CTA one line, hover-lift present, skeleton on the LLM wait, no console errors.
