# Compliance / SEBI-Guardrail Review — Round 1
**Reviewer:** compliance-guardrail-checker (council voice: Risk & Compliance / Devil's Advocate)  
**Date:** 2026-07-01  
**Files read:**
- `dashboard/views.py` (full — esp. L52–58 `_DISCLAIMER`, L147–229 `view_diagnosis`, L559–721 `view_results`/`_render_goal_card`, L756–882 `view_advanced`, L922–1000 `view_explore`)
- `shared/planning_engine.py` (full — esp. L102–131 compliance docstring, L359–385 `equity_category_for`, L411–438 `_non_equity_notes`, L671–687 `_selfcheck [E]`)
- `_process/audits/compliance.md` (original PASS gate, 2026-06-30)

---

## 1. Position Summary

- **The sacred two-mode separation is structurally intact.** Planning engine never calls `get_top_funds`, never emits a `scheme_name`. Explore Funds pops the `explore_category` key immediately (`views.py:944`) and reads zero profile/plan keys. The wall is real, not decorative.
- **All four proposed changes are safe or safe-with-guardrail** — none of them cross the personalized + named security + amount/directive trifecta. The biggest risks are framing risks (tone drift toward inducement), not structural compliance breaks.
- **One existing issue warrants a flag:** the "What to do next" block at `views.py:632–639` uses directive-adjacent language ("Automate the SIPs at the amounts above") that sits at the edge of the buy-directive line. Not a GATE FAIL but it needs tightened copy.
- **Jargon simplification carries the highest secondary risk** of the four changes: a layperson rewrite that overclaims a metric's predictive power ("tells you which fund is best") is a compliance error even on the neutral Explore screen. The exact copy matters.
- **Motion / emphasis is the most misread category by UX colleagues.** Animating a shortfall alarm or flashing fund rows on a neutral screener is a UX call until the animation triggers on a personalized surface with a buy-directive nearby — then it becomes an inducement. The rule is: persuasive motion is only clean when it is paired with neutral content.

---

## 2. Verdict on Each Proposed Change

### Change 1 — Per-goal equity category by tenure & importance (Step 4 / `_render_goal_card`)

**Verdict: SAFE-WITH-GUARDRAIL**

**What the code actually does today:** `equity_category_for(goal)` at `planning_engine.py:359–385` maps horizon → category string (Large Cap / Large & Mid Cap / Flexi Cap). No user attribute other than `years` touches this function. The category is handed to `view_explore` as a string, with weights reset to equal thirds (`explore_reset_weights=True`, `views.py:702`). The card text reads "We don't pick a fund *for you*" (`views.py:695`). Clean.

**The proposed addition — routing to Small Cap / Mid Cap by tenure AND a new "importance" input:**

*Is naming Small Cap Fund as a per-goal category any riskier than Large Cap?* No. "Small Cap Fund" is an AMFI/SEBI-defined equity scheme category, the same legal class of object as "Large Cap Fund." Both are category strings under the SEBI (Mutual Funds) Regulations 1996 categorisation circular. The compliance bright line is: **category string = safe; named scheme (ISIN / scheme name / AMC) = Mode A forbidden.** Small Cap is a category, not a fund. The riskier volatility profile of small caps is a finance concern (the finance critic should flag this), not a compliance category-change.

*Does adding an "importance" dimension (Essential / Aspirational) that influences which category a goal is steered to cross a line?* **No, as long as:**
1. The importance input changes the category string only — it must NOT unlock named funds in the personalized plan card.
2. The card framing does not read "Because this goal is Essential, we recommend…" — that phrasing is directive. The framing must stay descriptive: "Based on this goal's horizon and importance level, a [Category] allocation fits the profile."
3. The disclaimer at `views.py:606–613` (the pre-card SEBI warning) remains in position and is not pushed below the goal cards by the new input widget.

**Required guardrails if adopted:**
- Keep `equity_category_for` the sole source of the category string; do not let an importance-derived override name a scheme.
- Copy constraint: frame importance as context, not verdict. "Your retirement goal (long horizon, high importance) sits in the Flexi Cap band — explore those funds below" is safe. "This is Essential, so you must allocate to Mid Cap" is not.
- If "importance" affects the `reconcile_allocation` equity band (e.g., widening the risk tilt), that must stay within the horizon band's hard floor/ceiling. The `assert` at `planning_engine.py:515–518` already enforces this — any importance-driven logic must feed through that same assertion path.
- Place the disclaimer ABOVE any new importance-derived UI block, not below it.

---

### Change 2 — Jargon simplification (Explore + Advanced)

**Verdict: SAFE-WITH-GUARDRAIL (exact copy matters)**

**Affected locations:**
- `view_explore:960–967` — Sharpe/Jensen's Alpha/Consistency slider help text and `Why these metrics?` expander (`views.py:989–998`)
- `view_advanced:854–857` — FOIR label and caption
- `view_explore:932–936` — the SEBI warning banner (must not be weakened)

**The risk:** simplifying does NOT create a compliance problem on its own — it only does so if the simplified copy (a) drops the "past performance" caveat, (b) implies a metric is predictive rather than historical, or (c) implies a high-scoring fund is a good buy rather than a historically-better-scoring fund by this methodology.

See Section 4 (Q5) for exact approved copy. The caveat text must travel with every metric rename. The "Past performance does not indicate future results" line at `views.py:935` is load-bearing — it cannot be shortened or moved to a footer when the metric labels are visible.

**The SEBI warning at `views.py:932–936` is the one thing that must not be touched** during this change. If UX proposes removing it, shrinking it, or moving it below the category dropdown or sliders, that is a block.

---

### Change 3 — Motion / visual emphasis (shortfall alarm, fund row hover, entrance emphasis)

**Verdict: SAFE-WITH-GUARDRAIL — with surface-specific rules**

This change has three sub-cases with different risk profiles:

**3a. Animating the shortfall alarm on `view_diagnosis`:** SAFE. The shortfall alarm at `views.py:257–263` pairs a personalized SIP gap with zero named funds. The trifecta (personalized + named + directive) is not assembled on this screen. An animated urgency cue here is a UX choice, not a compliance one. The caption at `views.py:265–270` ("Preliminary estimate only…") must remain visible and not be scrolled past by any entrance animation before the user can read it.

**3b. Hover-highlighting fund rows in `view_explore`:** SAFE. The Explore screen is the neutral, non-personalized surface. Hover effects on a ranked table where the ranking is user-weight-adjustable do not create inducement — the user is in control of the rank. The condition that must hold: if any hover tooltip is added, it cannot display a personalized SIP amount (i.e., no data from `st.session_state["plan"]` may be read into the hover text). `view_explore` currently reads zero plan/profile keys (`audits/compliance.md:1b`) — that must remain true after any hover implementation.

**3c. Entrance emphasis on the personalized plan (`view_results`):** SAFE-WITH-GUARDRAIL. Animating the total SIP number or the goal card is fine as long as no animation sequence creates a "plan → named fund → act now" visual flow. The compliance problem would be: (1) plan card enters, (2) animation or visual arrow draws the eye to the Explore button, (3) Explore pre-populates with a fund already highlighted "#1 for you." That sequence, even if each element is individually clean, reads as a designed conversion funnel from personalized plan to specific fund. The guardrail: the Explore button on the card must remain secondary styling and must not be animated or highlighted differently when reached from the plan card vs. from the nav. Equal-emphasis, opt-in.

**Hard no:** do NOT add a timer, countdown, or "act before markets open" element anywhere. That is an inducement regardless of surface.

---

### Change 4 — Diagnosis zero-state (first-run shows neutral, not instantly "100% short")

**Verdict: SAFE — this is a compliance improvement, not a risk**

The current `view_diagnosis` at `views.py:232–269` shows a shortfall metric and a warning banner on first render, before the user enters any meaningful data (because the presets seed an amount/years at `views.py:117–122`). If the zero-state is changed so no shortfall alarm fires until the user has entered real numbers, that removes a false alarm that could read as "you are definitely under-funded" before any personalized calculation is grounded. This is strictly better from a truthfulness standpoint.

No compliance concern. The `_disclaimer()` call at `views.py:229` must remain regardless of what the zero-state renders.

---

## 3. Answers to Q2-compliance and Q5

### Q2-compliance: The bright line for category strings in Mode A

**The bright line is: AMFI/SEBI scheme category name = safe; ISIN, scheme name, or AMC name = forbidden in Mode A.** This line exists because SEBI's categorisation circular (`SEBI/HO/IMD/IMD-I DOF3/P/CIR/2020/198`) defines fund categories as regulatory classifications, not specific securities. Recommending a person allocate to "Large Cap Fund" is equivalent to recommending an asset class subtype — it is not recommending a security, the same way "short-duration debt" is not recommending a specific bond. The test is: can the user execute the recommendation by buying exactly one instrument? For a category string, the answer is no — they must still choose a fund from many. For a scheme name, the answer is yes. "Small Cap Fund" passes the test; "ICICI Prudential Smallcap Fund" fails it.

**Does importance (Essential/Aspirational) increase advice-likeness?** Slightly, but not enough to cross the line if it stays category-level. The analogy: a doctor saying "for a high-priority health goal, choose an aggressive treatment category" is education; "for a high-priority health goal, take this specific drug at this dose" is a prescription. Importance can widen or narrow the category routing (e.g., Essential goals stay in more conservative categories regardless of horizon), as long as the output remains a category string. What it must NOT do is function as a severity dial that unlocks named funds for "most important" goals.

**Recommended framing copy for importance-aware cards:**
> "This goal is marked **Essential** — your allocation stays in [Category], a lower-volatility equity type for goals where capital protection matters more than maximum growth. Adjust the horizon or step-up to see how that changes the SIP."

Not: "Because this is Essential, we recommend Large Cap." (The word "recommend" is load-bearing — avoid it in Mode A copy entirely.)

---

### Q5: Safe layperson rewrites for Sharpe / Jensen's Alpha / Consistency / FOIR

The following are the approved rewrites, with the exact caveat text that must appear adjacent (within the same tooltip, help text block, or expander section — not in a separate footer).

**Sharpe Ratio → "Return per unit of risk"**
> **How it works:** Measures how much return this fund has historically delivered for each unit of price swings it took on. A higher number means more return for the same ups and downs — historically.  
> **Caveat (required, adjacent):** Based on past performance only. Past performance does not indicate future results.

**Jensen's Alpha → "Manager's track record above expected"**
> **How it works:** Estimates how much return the fund's managers added beyond what the market's own movement would have produced — historically. A positive number suggests managers added value; a negative one suggests they did not, compared to this period's benchmark.  
> **Caveat (required, adjacent):** Calculated from historical data. Manager performance, market conditions, and fund composition change. Past performance does not indicate future results.

**Consistency → "How often it beat its benchmark"**
> **How it works:** The share of rolling periods in which this fund outperformed its category benchmark. 80% means it beat the benchmark in roughly 4 out of every 5 periods measured — historically.  
> **Caveat (required, adjacent):** Measured over past periods. A fund that was consistent in the past may not be in the future. Past performance does not indicate future results.

**FOIR (Fixed Obligations-to-Income Ratio) → "Debt burden as % of income"**
> **What it shows:** Total fixed monthly payments (EMIs + fixed obligations) as a percentage of monthly income. Lenders typically view above ~50–55% as stretched.  
> **Note:** This is a planning benchmark, not a guarantee of loan eligibility. Lender criteria vary.

**Critical rule for all four:** The caveat text is not optional decoration — it must appear in the same visible unit as the simplified label. If UX moves it to a collapsed tooltip, that is acceptable. If it moves to a page footer separated from the metric labels, it is not. The "Past performance does not indicate future results" line at `views.py:935` already discharges this for the Explore screen banner; the per-metric rewrites must repeat it locally to each metric (so a user reading only the slider help text gets the caveat, not just someone who reads the banner).

---

## 4. What the Others Might Get Wrong

**UX:** The most likely UX drift is adding visual hierarchy that creates a de facto recommendation path: e.g., making the "Explore Large Cap Funds →" button on a goal card visually primary (filled, branded color, larger) rather than secondary. At that point the card reads as "here is your plan → here is your fund." The button must stay secondary styling. Similarly, if UX adds a "Top Pick" badge, a "Best Match" highlight, or any rank-surfacing element on the Explore screen that is pre-filtered to one fund (not a category), that fund has been effectively pre-selected for the user on a personalized surface — even if the Explore screen itself is neutral, the navigation path from the personalized plan to a single pre-highlighted fund is the combined path that assembles the trifecta.

**Finance critic:** The finance critic may recommend expanding `equity_category_for` to include Mid Cap for 7–10 year goals and Small Cap for 15+ year goals on the grounds that the current Large & Mid Cap / Flexi Cap routing is overly conservative for aggressive investors. That is a legitimate finance argument. The compliance position is: the category routing can be changed, but it must remain category-level and the resulting category string must pass through the existing `_resolve_category` fallback at `planning_engine.py:388–408`. The compliance concern with aggressive-category routing is not legality but truthfulness — a 15-year Aggressive investor steered to Small Cap must see the explicit note that small cap carries higher volatility and the historical data period matters. A one-line caveat on the card is sufficient; suppressing it is not.

**Build team:** The most likely accidental compliance break during implementation is passing additional session_state keys into `view_explore`. The current audit (`_process/audits/compliance.md:1b`) verifies that `view_explore` reads exactly these keys: `explore_category` (popped immediately), `explore_reset_weights` (popped immediately), `_explore_weights` (the user's own slider state from the same screen). Adding ANY key from the plan (e.g., passing the user's risk_label to pre-sort results, or passing `goal['monthly_sip']` to display "this is your allocation" on the Explore screen) would breach Mode B neutrality. The compliance-guardrail agent's acceptance criterion does not distinguish intent from effect — if the key is read, the surface is no longer neutral, regardless of what it is used for.

---

## 5. Existing Compliance Issues Spotted During Review

### Issue A — "What to do next" directive-adjacent copy (`views.py:632`)

**File:line:** `views.py:632–639`

```
"1. **Automate the SIPs** at the amounts above (start small, use the step-up to grow them).\n"
```

"Automate the SIPs at the amounts above" is the closest thing to a buy-directive in the current codebase. It is on the personalized plan screen, immediately following the solved SIP amounts. There are no named funds here, so the trifecta is not assembled — this is NOT a gate failure. But it is the copy most likely to be pointed at in a "is this advice" conversation because it explicitly tells the user what to do with a specific rupee amount. 

**Recommended tightening (safe rewrite, no structural change needed):**
> "1. **Review the SIP amounts above** with a SEBI-registered adviser or distributor who can set them up for you."

Or, to preserve actionability without the directive tone:
> "1. The SIP amounts above are what the planning maths requires. Starting even a partial amount now and stepping up annually is how most planners approach this — confirm with an adviser before automating."

This is a low-severity flag. It should be fixed before any public re-launch or press coverage, but it does not block the current build.

### Issue B — `_render_goal_card` equity rupee amount shown adjacent to category name (`views.py:693–695`)

**File:line:** `views.py:693–695`

```python
st.markdown(
    f"{_rupees(eq_rupees)}/mo → **{_clean_category(cat)}** funds. "
    "We don't pick a fund *for you*; compare the ranked options yourself."
)
```

This renders `₹X,XXX/mo → Large Cap funds.` on the personalized plan screen. This is MODE A and is correct — the category string is not a named fund, and the disclaimer at `views.py:606–613` precedes it. However, when read in isolation by a user (not a regulator), `₹5,000/mo → Large Cap funds` reads as "put ₹5,000/mo into Large Cap funds" — which is true but is also the maximum specificity Mode A should ever carry. This is the correct design, not an error. I am flagging it so the build team does not "improve" it by replacing "Large Cap funds" with a single named fund — that single change would be the compliance break. The current rendering is the designed ceiling. Do not cross it.

---

## Gate Status

**ROUND 1 VERDICT: NO NEW GATE FAILURES INTRODUCED BY THE FOUR PROPOSED CHANGES.**

All four proposed changes are safe or safe-with-guardrail as described above. Issue A (directive-adjacent copy) is an existing minor issue, not introduced by the proposals. Issue B is a correct design, noted only to prevent regression.

The build team may proceed on all four changes subject to the named guardrails in Section 2. The compliance-guardrail agent should re-run the full pairing scan (`audits/compliance.md` checklist items 1a–2b) after implementation, specifically verifying that `view_explore` still reads no plan/profile session_state keys and that all metric-rename copy includes the per-metric "Past performance" caveat adjacent to the label.
