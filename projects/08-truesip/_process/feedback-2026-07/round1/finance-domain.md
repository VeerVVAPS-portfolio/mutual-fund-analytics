# Finance-Domain Critic — Round 1 (independent position)

**Feedback item owned:** Step4/Results — *"It is only suggesting one equity scheme — what if there are two or more goals with different importance and tenure? A long-term goal could be in Small Cap (riskier, higher return), but a shorter one can't."*

Voice/lens: financial soundness + internal consistency of the chained logic (mirrors `_process/council/finance-domain-critic.md`). ANALYSIS ONLY.

---

## 1) POSITION SUMMARY

- **The complaint is 100% valid and I reproduced it in code.** `equity_category_for` (`shared/planning_engine.py:359-385`) is a 3-bucket step function over horizon only: `<3y None · 3–7y Large Cap · 7–15y Large & Mid · >15y Flexi`. Empirically an 8y and a 14y goal BOTH return **Large & Mid Cap**; a 16y and a 25y goal BOTH return **Flexi Cap**. Two goals of clearly different tenure look identical → "only one scheme." Verified by running the engine.
- **The seed is being under-used.** `data/scored_funds.csv` (93 funds) carries Small Cap 13, Focused 13, ELSS 13, Mid Cap 11, Large & Mid 10, Flexi 9, Large Cap 9, Value 8, Multi Cap 4, Dividend Yield 3. The current ladder touches **only 3 of 10 categories** and never routes to Mid/Small/Focused/Multi/Value/Div-Yield/ELSS. (Note: the prompt's evidence list omitted **ELSS = 13** — it exists in the seed and matters for Q2b tax goals.)
- **Q2a LADDER: YES — widen the horizon ladder.** This is the correct primary fix and it is finance-defensible: volatility tolerance genuinely rises with horizon, and adding cut points at 15y/20y lets a 25y goal sit in Mid Cap while a 12y goal sits in Flexi/Large&Mid. Distinct tenures then visibly differ **with zero new inputs and zero compliance surface change** (still a category STRING). **P1, effort S.**
- **Q2b IMPORTANCE: YES but NARROW — add an optional 3-level importance input that moves ONLY the equity SUB-CATEGORY (which funds to browse), never the equity %.** Veer's instinct is right, but importance must be quarantined away from the horizon-authoritative % band or it silently re-becomes the person-level override the whole architecture killed. **P1, effort M.**
- **Q2c HONESTY: KEEP RETURN DECOUPLED from cap. Category = which funds to browse; equity % and 12% equity return = unchanged.** Letting Small Cap bump the return assumption would manufacture a smaller SIP off a *riskier* sleeve — exactly backwards for honesty, and it would threaten self-check invariant [B]. **P0 guardrail (do-not-do), effort S to document.**

---

## 2) RECOMMENDED (horizon × importance) → equity-category mapping (seed-valid)

**All strings below exist in the committed seed and in `data_store.CATEGORIES`.** Importance is *optional*; the middle column ("Important", the default) is what a user who never touches the new input gets — and it is a strict superset-safe widening of today's ladder (near-term unchanged; only the long end gains resolution).

| Horizon band | Equity % band (UNCHANGED, horizon-authoritative) | Essential (steer DOWN one notch) | **Important (default)** | Aspirational (steer UP one notch) |
|---|---|---|---|---|
| **< 3y** | 0–10% | None | **None** (sleeve too thin to route) | None |
| **3–7y** | 20–40% | Large Cap | **Large Cap** | Large & Mid Cap |
| **7–12y** | 50–70% | Large Cap | **Large & Mid Cap** | Flexi Cap |
| **12–15y** | 50–70% | Large & Mid Cap | **Flexi Cap** | Flexi Cap |
| **15–20y** | 70–85% | Flexi Cap | **Flexi Cap** | Mid Cap |
| **> 20y** | 70–85% | Flexi Cap | **Mid Cap** | Small Cap |

Notes that make each cut defensible:
- **New cut points added: 12y, 15y, 20y.** They split the two over-broad buckets (today 7–15y and >15y are each one category) so a 10y vs 14y goal and a 16y vs 25y goal now differ. Cut points are round, investor-legible numbers and align to real de-risking runway (a goal >20y away can survive a full small-cap drawdown-and-recovery cycle; a 12–15y goal generally should not sit in the most volatile cap).
- **Small Cap is gated to >20y AND non-Essential.** Small Cap has had 50%+ peak-to-trough drawdowns and multi-year recoveries; it is only defensible when the money genuinely won't be touched for two decades *and* the goal can tolerate a miss. This directly answers Veer: a long-term aspirational goal → Small Cap; a shorter goal → cannot land there.
- **The Important column is a superset of today's 3 buckets, just with finer horizon resolution.** So shipping the ladder alone (defer importance) is a valid P1-only slice.
- **Deliberately NOT auto-routed:** ELSS (tax-motivated, 3y lock-in — belongs behind a "tax saving" goal signal, see Q2b, not behind horizon), Focused (concentration bet — an Explore-only browse choice, not a plan default), Value / Dividend-Yield (style tilts, not horizon-driven). Keeping these Explore-only is the honest call: horizon does not justify them.

---

## 3) ANSWERS TO Q2a–Q2d

### Q2a — LADDER — **RECOMMEND: YES, widen it.  P1 / effort S**
The 3-bucket ladder is the root cause of "only one scheme." Replace the four `if years <` branches in `equity_category_for` (`planning_engine.py:378-385`) with the 6-band "Important (default)" column above. Add `SMALL_CAP = "Equity Scheme - Small Cap Fund"` and `FLEXI_CAP` is already defined; `MID_CAP` already defined (`planning_engine.py:353-356`).

Why the specific cut points (justification per boundary):
- **3y / 7y — keep as-is.** These are the equity-% band edges too; near-term money stays lowest-volatility (Large Cap). No change → no regression risk to the finance-correctness audit's PASS on near-term goals.
- **12y (new).** Splits the old 7–15y bucket so a 10y goal (Large & Mid) reads differently from a 13y goal (Flexi). ~10y is the conventional line where broad-market/flexi exposure becomes comfortable.
- **15y (new).** Boundary between "Flexi is enough" and "you can start adding a dedicated mid-cap tilt." Aligns to the existing equity-% band edge (>15y jumps to 70–85%), so the category step and the % step move together — coherent.
- **20y (new).** The Small-Cap gate. Two full market cycles of runway. Below it, no small cap under any importance.

Compliance/complexity cost: **zero.** Output stays a category STRING; `_resolve_category` (`planning_engine.py:388-408`) still validates against the seed and already has broad-market fallbacks if a category is thin. Mid Cap (11) and Small Cap (13) are well-populated, so fallbacks won't even fire.

One honesty caveat to surface in the UI (owned by UX, flagged here): when the ladder now shows **Small Cap** for a >20y aspirational goal, the card must keep the existing "we don't pick a fund for you; compare ranked options yourself" line AND ideally a one-liner that small/mid caps are *more volatile* — otherwise the finer ladder reads as a stronger recommendation than it is. The `_render_goal_card` equity-slice block (`views.py:686-709`) is the place.

### Q2b — IMPORTANCE — **RECOMMEND: YES, but strictly quarantined.  P1 / effort M**

Veer explicitly raised "importance," and it *is* a real dimension advisors use (essential goals get de-risked; aspirational goals can take more swing). But it is also the single most dangerous place to reintroduce the person-level override the architecture deliberately killed. So the rule must be surgical:

**What importance is ALLOWED to move:**
1. **(YES) The equity SUB-CATEGORY** — i.e. shift one notch along the ladder (the Essential/Aspirational columns in §2). An Essential 18y goal steers **down** to Flexi (away from Mid/Small); an Aspirational 18y goal steers **up** toward Mid/Small. This changes *which funds you browse*, not how much equity you hold.
2. **(NO) The equity WEIGHT / horizon band** — importance must **never** move `equity_pct`, `band_low`, or `band_high`. A 2y Essential goal and a 2y Aspirational goal both stay 0–10% equity. This is the sacred constraint; the whole "horizon-authoritative" story dies if importance can nudge the %.

**The exact interaction rule** (deterministic, no LLM):
```
notch = {Essential: -1, Important: 0, Aspirational: +1}[importance]   # default Important = 0
category = ladder[horizon_band]                                       # the middle column
category = clamp_along_ladder(category, notch)                        # move ≤1 step, clamp at ends
# equity_pct, asset_split, blended_return are computed EXACTLY as today — untouched by importance
```
Clamp at the ladder ends (an Aspirational <3y goal is still `None`; an Essential 3–7y goal can't go below Large Cap). One notch max — importance is a nudge, not a lever.

**Why this is honest:** it maps importance to the only thing importance legitimately governs at the *fund-selection* layer — style/concentration risk within an already-fixed equity budget. It cannot be used to justify putting a "very important" near-term goal into equity (the % is horizon-locked), which is exactly the retail mistake the product exists to prevent.

**Bonus it unlocks (optional, P2):** the "goal" question already in the quiz has a **"Tax saving (ELSS)"** option (`risk_profiler.py:41`, `GOAL_SCORES`). A *per-goal* "tax-saving" importance/type flag is the honest, non-horizon reason to route to **ELSS (13 in seed)** — which today is orphaned. If importance is added, consider a 4th type "Tax-saving" that routes the equity sleeve to ELSS for 3y+ goals (respecting the 3y lock-in). Keep it P2; the 3-level Essential/Important/Aspirational is the core ask.

**If you (other councilmembers) think importance adds more confusion than value:** the fallback is **ship Q2a alone.** The widened ladder *by itself* fully resolves Veer's literal complaint ("two goals of different tenure now show different schemes") with zero new input. Importance is the *nice-to-have* that also answers the "different importance" half of his sentence. My recommendation: ship the ladder now (P1/S), add importance next (P1/M) — do not block the ladder on the importance UX.

### Q2c — HONESTY (does mapping to Small/Mid overstate return?) — **RECOMMEND: KEEP RETURN DECOUPLED.  P0 guardrail / effort S**

**Cap choice must NOT change the return assumption.** `blended_expected_return` (`planning_engine.py:280-312`) uses a flat equity **12%** regardless of cap, and it must stay that way. Reasoning:

- If Small Cap bumped the equity leg to, say, 14%, the blended return rises → the annuity solver returns a **smaller** required SIP (`solve_goal`, `goal_calculator.py:143`). You would be telling the investor to save **less** because they picked a **riskier** sleeve. That is precisely backwards and is the kind of thing a SEBI-RIA would flag: higher expected return on small caps is compensation for higher risk / higher dispersion, not a free reduction in required contributions. Planning should if anything be *conservative* on the volatile sleeve, never optimistic.
- The product's honesty spine is "the % and the SIP are deterministic; category is only *which funds to browse*." Coupling return to cap breaks that clean separation and invites the "we juiced the return to make the SIP look affordable" critique.
- 12% is already the deliberately conservative figure P6 adopted (source Excel used 16–17%; documented at `planning_engine.py:48-50`). Holding one equity number across caps is the defensible, auditable choice.

**Invariant this protects (must stay green):** `_selfcheck()` block **[B]** (`planning_engine.py:610-621`) asserts `r_near < r_far` — a near-term debt-heavy goal must assume a LOWER blended return than a long equity-heavy goal. That invariant depends on equity return being a **single constant** blended by the horizon-set weights. If you made equity return cap-dependent, a long Small-Cap goal at a higher equity rate would still pass [B] (it's already highest), but you would have quietly coupled two things the audit treats as independent, and you'd need a *new* invariant to prove "cap never lowers the SIP." Cleaner to not open that door. **Recommendation: add a one-line code comment at `RETURN_ASSUMPTIONS` and at `equity_category_for` stating "cap choice affects only fund browsing, never the return assumption or the SIP," so a future editor doesn't 'helpfully' couple them.**

No other `_selfcheck` block is affected by Q2a/Q2b: [A] regression anchor (return math) untouched; [C] risk cap (%-band) untouched — importance doesn't touch the band; [D] invariants (band membership + rupee sum) untouched — category string doesn't enter either assertion; [E] compliance (no named fund) untouched — still a category string. **A ladder/importance change is invariant-safe by construction.** (I re-ran `python shared/planning_engine.py` on the current code: all pass — that's the baseline to keep green.)

### Q2d — JARGON SANITY CHECK (Sharpe / Alpha / Consistency / FOIR) — **P2 / effort S**

The Explore-screen tooltips (`views.py:960-967`, `989-998`) and the FOIR caption (`views.py:858-860`) are **already accurate** — any "simplification" must not trade correctness for warmth. Trustworthy one-line laymen definitions the build team can use verbatim:

- **Sharpe Ratio** — "Return earned for the amount of ups-and-downs (risk) taken; higher means a smoother ride for the same return." *(Accurate. Do NOT simplify to "risk-adjusted return is higher = better fund" without the volatility idea — that loses the whole point. The current tooltip "return per unit of volatility" is correct; keep it, just add the plain gloss.)*
- **Jensen's Alpha** — "How much the fund beat (or lagged) what its market risk alone would predict — a rough read on manager skill." *(Accurate. The trap to avoid: don't call alpha simply "extra return" — extra return could just be extra risk; alpha is extra return **after** adjusting for beta. The current tooltip already says this correctly.)*
- **Consistency** — "How often the fund beat its benchmark across periods, not just once." *(Accurate and already plain. Fine as-is. Minor honesty note: it's the share of rolling periods it out-performed — "how reliably, not how much" — don't let a rewrite imply it measures *size* of outperformance.)*
- **FOIR** (Fixed Obligations to Income Ratio) — "The share of your income already committed to EMIs and rent; the higher it is, the less room a new SIP has." *(Accurate. The `>~55% = stretched` line at `views.py:858-860` is a reasonable lender rule-of-thumb — keep the "rule of thumb," don't present 55% as a hard/official threshold, because lenders vary.)*

**One misstatement risk to watch:** any rewrite that describes these three equity metrics generically enough that they sound applicable to the **debt/gold** sleeves. They are computed vs **NIFTY 50** and are meaningless off-equity (already correctly firewalled — `planning_engine.py:116-119`, `_non_equity_notes`). If UX shortens the tooltip, it must stay inside the Explore/equity context and never leak next to a debt note. No change to the firewall.

---

## 4) WHAT THE OTHERS MIGHT GET WRONG (where UX/compliance may push something finance-unsound)

- **UX will want importance to also move the equity % ("this goal is critical, put more in equity!").** REJECT. That is the person-level override the architecture killed, wearing a new hat. Importance moves the *sub-category* only; the % is horizon-locked. Hold this line hard — it is the sacred constraint.
- **UX/compliance may resist showing "Small Cap" at all as too risky/too advice-like.** The honest answer isn't to hide it — it's to (a) gate it correctly (>20y, non-Essential, §2) and (b) label its volatility. Hiding the fuller category set is what *created* the "only one scheme" complaint. The fix is *more* resolution with *more* caveats, not less.
- **Someone may propose coupling return to cap to "reward" long aggressive goals with a lower SIP.** REJECT — see Q2c. It reduces the required SIP on the *riskiest* sleeve. Backwards and audit-fragile.
- **Someone may propose auto-routing ELSS / Focused / Value / Dividend-Yield off horizon** just to "use the whole seed." REJECT for horizon-driven routing — those are tax-motivated (ELSS lock-in) or style/concentration bets that horizon alone doesn't justify. ELSS belongs behind a tax-goal signal (Q2b bonus); the rest belong Explore-only. Using a category *because it exists in the CSV* is not a financial reason.
- **Compliance angle to double-check (flag for compliance critic):** the widened ladder still emits only a category STRING and still hands off to the neutral, weight-reset screener (`views.py:698-704`), so it should stay PASS — but the finance-correctness audit (`_process/audits/finance-correctness.md:75`) and compliance audit explicitly *documented the current 3-bucket mapping as the reviewed behavior*. Both audits will need a re-run/amendment noting the ladder now spans 6 bands incl. Mid/Small Cap. It's still category-only; just make sure the audit trail reflects the new mapping so it isn't later read as scope creep.

---

## 5) ANYTHING ELSE FINANCE-UNSOUND I NOTICED WHILE READING

1. **The `_EQUITY_ROUTING_FLOOR_PCT = 5.0` vs the 3–7y band interaction is fine but worth a sanity note.** At 3–7y the band is 20–40%, so equity always clears the 5% floor and a category always shows. Good. But note a 3y goal for a **Conservative** investor gets tilt 0.0 → equity = band_low = **20%** (not below floor), so it *will* now route to Large Cap. That's correct and desirable — I only flag it so no one "optimizes" the floor upward and accidentally suppresses legitimate equity sleeves on medium-term goals.
2. **The diagnosis screen hard-codes a "Moderate Aggressive" stand-in mix** (`views.py:135`, `_required_sip_preliminary`). It's clearly labeled preliminary and re-solved later, so it's honest — but if the ladder/importance changes land, the *preliminary* number won't reflect importance (importance isn't collected yet at step 0). That's fine (importance only affects category, not the SIP number the diagnosis shows), which is another reason to keep importance decoupled from the % — it keeps the step-0 preliminary SIP identical to the final SIP for a given horizon, so the "shortfall reveal" doesn't shift after the quiz. **A hidden bonus of the Q2c decoupling: it preserves diagnosis→results SIP consistency.**
3. **`blended_expected_return` normalises defensively and floors at the debt rate on degenerate input** (`planning_engine.py:302-305`). Sound. No issue — just confirming the return path is robust to a zero-weight edge case, so nothing in the ladder change can make it explode.
4. **Gold as residue-bearer in both the %-split and the ₹-split** (`_derive_asset_split` and `split_sip_by_asset`). Consistent and correct (rounding lands on the least structurally-significant sleeve). Not in scope for this feedback item; noting it's clean so it's not disturbed by ladder work.
5. **Minor, not blocking:** the >15y equity band tops out at 85% and Small Cap is proposed for >20y. A goal placed in Small Cap will still hold ~11–15% debt/gold ballast (from `_derive_asset_split`). That's *good* — it means even the most aggressive long goal isn't 100% small-cap. Worth keeping as an explicit honesty point in the explainer prose ("even your longest, most aggressive goal keeps a debt/gold ballast").

---

**Bottom line for the debate:** Ship the **widened ladder (Q2a, P1/S)** — it alone fixes the literal complaint, uses the seed's Mid/Small/Flexi properly, and is invariant-safe. Add **quarantined importance (Q2b, P1/M)** that moves the sub-category ±1 notch and **nothing else**. **Do not** couple return to cap (Q2c, P0 guardrail) — it would shrink the SIP on the riskiest sleeve and threaten self-check [B]. Jargon rewrites are fine as long as they keep the definitions in §Q2d and never leak equity metrics onto debt/gold.
