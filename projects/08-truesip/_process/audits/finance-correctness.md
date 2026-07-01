# TrueSIP — Finance Correctness Audit

**Auditor:** finance-correctness-auditor (adversarial verify-only)
**Date:** 2026-06-30
**Scope:** `shared/planning_engine.py`, `shared/explainer.py`, `shared/goal_calculator.py`, `shared/risk_profiler.py`, `dashboard/app.py`, `dashboard/views.py`
**Method:** independent Python recomputation of every formula; line-by-line trace of every rendered figure back to a `shared/` function; both committed self-checks re-run.

---

## 1. DETERMINISM — every displayed number traces to `shared/` — **PASS**

Traced all `_rupees(...)`, `_lakh_cr(...)`, `st.metric(...)`, and inline `%`/`₹` interpolations in `views.py`. Every figure originates from a `shared/` function or from a user input run through one:

| Surface | `views.py` lines | Source (all in `shared/`) |
|---|---|---|
| Diagnosis required SIP / blended % / split % | 226-227, 242-272 | `_required_sip_preliminary` → `reconcile_allocation` + `blended_expected_return` + `goal_calculator.solve_goal` |
| Affordability preview (`total_required`, `disposable`) | 521-554 | `_required_sip_preliminary`; `disposable` = user income arithmetic |
| Results headline `total_monthly_sip` | 594-595 | `planning_engine.build_plan` |
| Per-goal card (FV, SIP, invested, growth, blended %, sip_split ₹) | 660-719 | `build_plan` plan dict keys (`solve_goal` + `split_sip_by_asset`) |
| Advanced check (life/health/emergency gaps, FOIR) | 830-891 | `shared.protection.*` |
| Year-by-year cashflow | 865-882 | `shared.cashflow_projection.project_cashflow` |
| Explore Funds (Sharpe/Alpha/Consistency/AUM/returns) | 983-1038 | `shared.scoring.compute_composite_score` on equity-only `df` |

- **No hardcoded rupee/percent figure is rendered as a computed plan output.** `inflation_rate=0.06` (views.py:140) and the slider defaults are inputs, not displayed results; the `0.12`/0.06/etc. in `_risk_gauge` (lines 360-363) and chart `gridcolor` (910) are RGBA colours, not money.
- **`explain_plan` output never supplies a displayed figure.** `views.py:623-625` calls `explanation = explain_plan(plan)` then `st.markdown(explanation)` — the string is rendered as opaque prose and stored to `session_state['explanation']`; it is **never parsed for a number**, and no metric reads from it. (`app.py:51-53` documents it as prose-only.)
- **LLM is defensively prevented from emitting figures:** system prompt forbids `₹+digit` (explainer.py:88-111); `_build_context_block` sends only qualitative descriptors + integer assumption %s, never raw plan rupees (explainer.py:114-197); a post-generation regex `re.search(r"₹\s*[\d,]+", md)` falls back to the deterministic demo if any ₹-figure slips through (explainer.py:432-435). Self-check `python shared/explainer.py` confirms no ₹-figure leaks on the demo path (re-run, PASS).

## 2. RECONCILIATION — horizon bands + risk tilt/cap — **PASS**

Bands verified exactly against spec `<3y 0–10 · 3–7y 20–40 · 7–15y 50–70 · >15y 70–85` (`risk_profiler.py:85-91`, half-open `[y_min, y_max)`):

```
1–2.99y → (0,10)   3–6.99y → (20,40)   7–14.99y → (50,70)   15y+ → (70,85)
```

Risk tilt within band (`_LABEL_TILT`, risk_profiler.py:95-100) verified at every band — equity always lands inside `[band_low, band_high]`, and `build_plan` asserts membership (planning_engine.py:515-518):

```
20y band 70–85: Conservative=70.0  ModCons=77.5  ModAgg=81.2  Aggressive=85.0
10y band 50–70: Conservative=50.0  ModCons=60.0  ModAgg=65.0  Aggressive=70.0
```

**Cap rule — note on the task's wording.** The task brief says "Conservative pinned at midpoint." The implementation (and the persona docstring / engine self-check `[C]`) actually pins **Moderate Conservative at the midpoint (tilt 0.5)** and places **Conservative at the band *floor* (tilt 0.0)**. This is **correct and stricter, not a defect**: the mandate is "panic-prone capped *at or below* midpoint," and floor ≤ midpoint satisfies it. Both panic-prone labels are verified `≤ midpoint` at every band (10y: Cons 50 ≤ 60, ModCons 60 = 60; 20y: Cons 70 ≤ 78, ModCons 77.5 ≤ 78). No label ever exceeds its band ceiling. **PASS** — the task's one-line summary slightly misnamed which label sits at the midpoint; the code is internally consistent with its own documented spec.

## 3. SIP MATH — annuity-due solve + P6 regression anchor — **PASS**

**Annuity-due solver (`goal_calculator.required_fixed_sip`, lines 48-65):** independently recomputed `FV = PMT·((1+r)ⁿ−1)·(1+r)/r` with `r = annual_return/12`, `n = round(years·12)`:

```
FV ₹1Cr @12% ×10y:  engine = 43,040.5430   independent = 43,040.5430   → identical
forward-reconstruction of that SIP (start-of-month) → ₹10,000,000.00  ✓ annuity-DUE confirmed
```

Step-up path (`required_stepup_sip` / `_stepup_future_value`, lines 68-101) simulates **month-by-month** (loop over `n_months`, `(m-1)//12` year index), not annual lumps — confirmed correct per mandate.

**P6 Education regression anchor** (P6 README: FV req ₹59,04,327 at PV ₹30,00,000 @7% ×10y; original ₹8,000/mo guess is ~6.6% short; P6 default return 12%):

```
FV required = ₹59,01,454   vs README ₹59,04,327   → 0.05% drift (<1% gate)  PASS
Required SIP @12% = ₹25,400/mo  >  ₹8,000 guess   → under-funding reproduced
```

The engine's committed self-check `[A]` asserts exactly these two facts and passes.

### Ruling on the 12%-vs-16/17% choice — **ACCEPTABLE / HONEST**

- **Disclosure is accurate.** Engine docstring (planning_engine.py:48-50) and P6 README (line 44) both state the *original Excel* used 16–17% and the *P6 rebuild* adopted 12% as a conservative, editable default. The engine's equity assumption (12%) is described as "matches Project 6's conservative default" — **verified true**; it does not claim to match the Excel.
- **It cannot misrepresent the "6.6% short" finding.** The 6.6%-short figure was P6's finding under the *original Excel's* optimistic return. Lowering the assumption to 12% makes any fixed guessed SIP look **more** short, never less — at 12% a flat ₹8,000/mo under-funds the ₹59L target by far more than 6.6%. So 12% is strictly the more conservative direction; it cannot flatter or erase the under-funding story.
- **There is no stale finding to misrepresent.** TrueSIP never displays a "6.6% short" claim tied to 12%. Its whole design solves each goal's SIP from scratch (`build_plan` → `solve_goal`), so the only thing 12% drives is the *required* SIP, which is shown honestly alongside its blended-return assumption on every card. Internally consistent.

## 4. ASSET SPLIT — rupee sum, equity-only category, no off-equity metrics — **PASS**

- **Σ(equity+debt+gold) == SIP exactly.** `split_sip_by_asset` (planning_engine.py:319-342) rounds equity & debt to ₹0.01 and lets **gold absorb the residue**. Verified across {0,5,30,60,85}% × {₹1 … ₹999,999.99}: every split sums to the SIP within ₹0.005. `build_plan` asserts `|sum − monthly_sip| < 0.05` (lines 519-522). Full 3-goal plan: each `splitSum` equals `monthly_sip` to the paisa.
- **Asset split sums to 100%** at every equity level (gold = 25% of remainder capped at 15pp; debt absorbs rounding drift): verified 0→85% all sum to 100.0 (planning_engine.py:244-273).
- **Only equity routes to a fund category.** `equity_category_for` (lines 359-385) returns a CATEGORY STRING for equity by horizon (None <3y · Large Cap 3–7y · Large&Mid 7–15y · Flexi >15y) and `build_plan` only sets it when `equity_pct ≥ 5%` floor. Debt/gold get `_non_equity_notes` (generic instrument *types*: liquid/short-duration debt, PPF, SGB/gold ETF) carrying `{sleeve, instrument, note}` only.
- **NO Sharpe/Alpha/score on debt/gold.** Asserted in self-check `[E]` and re-verified: every `non_equity_notes` entry has no `score`/`sharpe`/`alpha`/`rank`/`composite_score` key. Sharpe/Alpha appear **only** on the Explore Funds equity table (`_render_fund_table`), which never reads the plan. The card UI (views.py:711-721) labels debt/gold "named, but *not ranked* — these metrics are equity-vs-index and don't apply here."

## 5. ASSUMPTIONS — disclosed + editable — **PASS (with one noted limitation)**

- **Goal inflation:** editable slider, default 6%, disclosed (views.py:449-453). ✓
- **SIP step-up:** editable slider, default 0%, disclosed (views.py:455-460). ✓
- **Per-asset returns (equity 12% / debt 7% / gold 6%):** **disclosed** — surfaced as the blended-return figure on every goal card (views.py:662) and on the diagnosis caption (views.py:268), exposed in `plan['return_assumptions']` (planning_engine.py:568), and documented in the module header + README. The `_DISCLAIMER` everywhere states "documented planning assumptions (not forecasts)." **Limitation:** the equity/debt/gold return rates themselves are **not individually user-editable** in the UI (no per-asset return slider) — unlike P6, which exposed a per-goal return field. This is an honest, disclosed fixed assumption (nothing is misrepresented), and the primary lever (inflation) *is* editable, so it does not rise to a correctness FAIL — but it is a real divergence from P6's editability and from the literal "editable" wording of the checklist. **Recommendation (non-blocking):** expose the equity-return assumption as an advanced override, or add one line to the Plan-assumptions section stating the 12/7/6 rates are fixed conservative planning constants.

---

## Verification log
- `python shared/planning_engine.py` → ALL SELF-CHECKS PASSED (re-run).
- `python shared/explainer.py` → ALL SELF-CHECKS PASSED; no ₹-figure leaked on demo path (re-run).
- Independent annuity-due recompute matches `required_fixed_sip` to 1e-6.
- P6 Education FV anchor reproduced to 0.05% (<1% gate).
- Rupee-split exact-sum verified across SIP × equity grid.
- All `build_plan` invariants (band membership, rupee sum, no named fund, no off-equity metric) pass on a 3-goal plan.

## Findings summary
- **0 FAILs.**
- 1 documentation nuance (item 2): task brief says "Conservative pinned at midpoint"; code correctly pins **Moderate Conservative** at midpoint and Conservative at the (stricter) floor. No code change needed.
- 1 non-blocking limitation (item 5): per-asset return rates are disclosed but not user-editable; inflation and step-up are both editable. Recommend exposing/annotating the fixed 12/7/6 rates.

GATE: PASS

---

## Amendment 2026-07-01 — 6-band ladder + importance nudge

**Auditor:** finance-correctness-auditor (adversarial verify-only, re-run)
**Scope of this amendment:** `shared/planning_engine.py` (the only engine file changed by the 2026-07 feedback build; `shared/risk_profiler.py` had a one-line question-label reword only — `risk_profiler.py:201`, sourced from `REACTION_SCORES.keys()`, so `compute_risk_score` is unaffected).
**Method:** re-ran `python shared/planning_engine.py` (all 8 self-checks [A]–[H] pass); ran independent cross-horizon recomputation of the real `build_plan` path (not just the isolated `equity_category_for`).

### What changed
The equity-category hand-off widened from a 3-bucket step function to a **6-band × 3-importance ladder** (`_CATEGORY_LADDER`, `planning_engine.py:394-403`) plus an optional per-goal `importance` key read in `equity_category_for` (`planning_engine.py:439-445`) and echoed by `build_plan` (`planning_engine.py:592`). This **supersedes** the old 3-bucket mapping documented in §4 above (`None <3y · Large Cap 3–7y · Large&Mid 7–15y · Flexi >15y`).

### New mapping (horizon × importance → equity CATEGORY string, default column = "Important")

| Horizon | equity % band (UNCHANGED) | Essential | **Important (default)** | Aspirational |
|---|---|---|---|---|
| < 3y | 0–10% | None | **None** | None |
| 3–7y | 20–40% | Large Cap | **Large Cap** | Large & Mid Cap |
| 7–12y | 50–70% | Large Cap | **Large & Mid Cap** | Flexi Cap |
| 12–15y | 50–70% | Large & Mid Cap | **Flexi Cap** | Flexi Cap |
| 15–20y | 70–85% | Flexi Cap | **Flexi Cap** | Mid Cap |
| > 20y | 70–85% | Flexi Cap | **Mid Cap** | Small Cap |

Bands are half-open `[y_min, y_max)`. The ±1 importance "notch" is **baked into the columns** (not a uniform programmatic shift), so 12–15y Aspirational stays Flexi and 15–20y Essential stays Flexi by design. All six category strings exist in `data/scored_funds.csv` (verified: Large Cap, Large & Mid Cap, Flexi Cap, Mid Cap, Small Cap all present); `_resolve_category` (`planning_engine.py:448-468`) still validates each against the seed with broad-market fallbacks for absent categories.

### Verified invariant-safe (the change is safe BY CONSTRUCTION)

- **[A] regression anchor** — P6 Education FV ₹59,01,454 (0.05% drift), required SIP ₹25,400 > ₹8,000 guess. Untouched by the ladder. **PASS.**
- **[B] `r_near < r_far`** — independently reconfirmed: `r_near(2y)=0.0735 < r_far(20y)=0.1121`. **PASS.**
- **[C] risk cap** — Moderate Conservative pinned at band midpoint, Aggressive at band top; importance does not touch the band. **PASS.**
- **[D] band-membership + rupee-sum** — every goal's `equity_pct` in `[band_low, band_high]`; `Σ sip_split == monthly_sip` to the paisa. **PASS.**
- **[E] no named security** — `equity_category` is a CATEGORY string only; no scheme name leaks; non-equity notes carry no ranking metric. **PASS.**
- **[F] ladder resolution** — 5/10/14/25y (Important) → 4 distinct categories (Large / Large&Mid / Flexi / Mid) via both the function and the full `build_plan` path. Fixes the "only one scheme" complaint. **PASS.**
- **[G] importance invariance (the sacred quarantine)** — verified on the REAL `build_plan` path, and independently re-verified across **five** horizons (5/10/14/18/25y), not just the self-check's 22y case: across Essential/Important/Aspirational, `equity_category` differs while `equity_pct`, `asset_split`, `blended_return`, `band`, `sip_split`, and `monthly_sip` are **byte-identical**. Importance moves ONLY which funds to browse — never the money. **PASS.**
- **[H] Small Cap gate** — boundary sweep confirms no goal with years ≤ 20 reaches Small Cap under any importance; a >20y Aspirational goal does. Gate opens at `20 + 1e-9` (`_SMALL_CAP_GATE_YEARS`, `planning_engine.py:393,400,402`), so a goal must be **strictly beyond** 20y (a hair above, not exactly 20) to land in Small Cap — the conservative direction, matching the critic's strict ">two decades" intent. **PASS.**

### Determinism / return-decoupling guardrail (Mandate #1 + P0 guardrail)

- **Mandate #1 (deterministic SIP):** `planning_engine.py` imports no `random`/`numpy`, makes no LLM call, and every `monthly_sip` still comes solely from `goal_calculator.solve_goal` (`planning_engine.py:555`; `solve_goal` computes the SIP analytically at `goal_calculator.py:186`). The ladder is a static lookup table + dict indexing — **it added no stochastic or LLM-sourced number.** **PASS.**
- **Return-decoupling (P0 guardrail):** cap/category selection NEVER feeds `RETURN_ASSUMPTIONS` (equity stays `0.12`) or `blended_expected_return`. In `build_plan`, `blended_return` is computed from `asset_split` (`planning_engine.py:552`) strictly **before and independently of** `equity_category` (`planning_engine.py:568`); `equity_category_for` returns only a string and reads none of the return machinery. Independently confirmed: an identical asset split yields an identical blended return regardless of which cap label is attached. A riskier cap therefore can never shrink the SIP. The guardrail comment is present at both `RETURN_ASSUMPTIONS` (`planning_engine.py:165-169`) and `equity_category_for` (`planning_engine.py:363-368`, `416-419`). **PASS.**

**Amendment verdict — GATE: PASS.** The 6-band ladder + importance nudge is invariant-safe by construction; all 8 self-checks pass; determinism and return-decoupling hold. No engine change required. (The one non-blocking limitation from §5 above — per-asset return rates disclosed but not individually user-editable — is unchanged by this build and remains non-blocking.)
