# Round 1 — UX & MOTION critique (TrueSIP feedback 2026-07)

**Lens:** microinteractions, state transitions, entrance vs hover motion under Streamlit full-page reruns, visual hierarchy/depth, first-run zero-state, and the specific "broken/janky" complaints. Grounded in the code as it renders today, not the spec.

**Ground truth I verified before writing anything (this reframes the whole "make it feel modern" ask):**
- `shared/theme.py` has **zero `@keyframes` and exactly two `transition` rules** — buttons (L120) and the step bar (L253). There are **no** `fadeUp`/`scalePop`/`.landing-wrap` classes here (the Round-0 UX persona's "80% done, they share fadeUp keyframes" claim was true of Projects 1/2/6 and is **false of TrueSIP** — this codebase was rebuilt clean). So "feels static" is literally accurate: nothing moves except a button lift and a 300ms bar color fade. That is good news for motion-under-rerun — **there is nothing currently replaying/flashing on rerun, so we start from a clean slate and only add motion we can defend.**
- There is a real `.streamlit/config.toml` in the project (`base="dark"`, `primaryColor=#818CF8`) AND a `!important` CSS override in `theme.py` L111-112 that styles **every** `.stButton > button` (both `kind` values) with `padding: 0.6rem 1.4rem`. This matters for the button-wrap fix.

---

## 1. POSITION SUMMARY

- **"Static" is the correct diagnosis but the wrong first fix.** Four of Veer's seven complaints are literally *broken widgets* (sliders reading 0%, chart in "M", donut double-number, question truncation), not "not enough animation." Ship polish onto broken controls and you've gilded a bug. **Correctness → hierarchy/depth → motion, in that order.** (Full argument in Q1.)
- **The single biggest "feels cheap" lever here is not animation — it's depth/elevation and spacing, which Streamlit strips by default.** Metric cards, goal cards, and the step bar currently sit flat on `#0A0A0E`. Adding resting elevation + one hover-lift class buys 80% of the "modern SaaS" feel for ~30 lines of CSS, with **zero rerun-flash risk** because hover/transition-on-existing-elements never replays on rerun.
- **Almost every *entrance* animation is an anti-pattern in this app** and must be rejected, because Streamlit re-runs the entire script on every widget touch — and this app scores the quiz *live on every radio change* (`view_profile` L292-317) and re-solves SIPs live on every slider drag. A `fadeUp` on cards would re-fire the instant a user nudges any slider. The safe motion subset is **hover-triggered + CSS `transition` on state change + one-time skeleton during the LLM call only.** (Full taxonomy in Q3.)
- **The diagnosis screen screaming "~100% short" on first paint is the worst trust smell in the product** — it fabricates alarm from a default (`current_sip=0` vs a preset ₹1Cr goal) before the user has told us anything. Gate the reveal behind an explicit action. (Q6.)
- **The Explore weight sliders should stop pretending to "sum to 100."** The code already normalises internally (`weights = ws/total_w …` L974) — the "must sum to 100%" label is a lie the UI tells and can't keep. Reframe as relative importance; don't build auto-balancing sliders (they fight Streamlit's rerun model and feel broken). (Q4.)

---

## 2. PER-ITEM VERDICTS (my lane)

### A. Overall "tool feels static" — add a defensible motion+depth layer
- **Root cause:** `theme.py` ships flat surfaces and only 2 transitions; no elevation system, no hover affordance on cards/metrics, no acknowledgement of state changes. Nothing communicates "this is a live, responsive product."
- **Fix (the shippable subset):** add to `theme.py` CSS — (1) resting **elevation** on `[data-testid="stMetric"]`, `stContainer`-border cards, and the expander (`box-shadow: 0 1px 3px rgba(0,0,0,.4), 0 1px 2px rgba(0,0,0,.6)`); (2) a **hover-lift** on those same cards (`transition: transform 150ms ease, box-shadow 150ms ease; :hover { transform: translateY(-2px); box-shadow: 0 8px 24px rgba(0,0,0,.5) }`); (3) a subtle **accent border-glow on hover** for goal cards to signal interactivity; (4) keep the existing button lift. All hover/transition — **none replay on rerun.**
- **Severity:** P1 (trust — "static" reads as "unfinished/AI-generated" to a recruiter). **Effort:** S (CSS-only, ~40 lines). **Risk:** Low. Only watch: the card selector `div[data-testid="stVerticalBlock"] > div[data-testid="stVerticalBlock"]` (theme.py L81) is fragile across Streamlit versions — scope the hover to bordered containers carefully or it bleeds onto every column block.

### B. Diagnosis instant shortfall (zero-state) — **P0-adjacent trust bug**
- **Root cause:** `view_diagnosis` persists a valid goal on first paint (preset Retirement ₹1Cr / 25y, L167-174), `current_sip` defaults to 0 (L204-208), `valid` is True immediately (L213), so `_render_shortfall_reveal` fires on load (L224-226) and prints **"You're about 100% short"** in a warning box (L259-263) before the user has entered a single thing.
- **Fix:** gate the reveal behind an explicit **"Check my SIP →"** button (or: only reveal once `current_sip > 0`). Until then render an **instructional empty state** in the reveal slot ("Enter your current SIP above to see if you're on track — ₹0 is fine, we'll show the target."). Keep the goal presets pre-filled (they're helpful scaffolding); it's the *verdict* that must wait for input. See Q6 for the exact recommendation.
- **Severity:** P1 (trust — the tool's first impression is a false alarm). **Effort:** S. **Risk:** Low; must keep the Next-gate logic (`has_goal`) working — decouple "goal is valid enough to advance" from "show the shortfall verdict."

### C. "Build my full plan →" button wraps to 2 lines ("looks like a dice")
- **Root cause:** `_nav_buttons` (app.py L215) puts Next in a **1/6-width column** (`st.columns([1,4,1])`); the step-0 label "Build my full plan →" (app.py L266) can't fit, and `theme.py` L119 forces `padding: 0.6rem 1.4rem !important` on it, so it wraps into a near-square. Confirmed.
- **Fix:** for step 0 specifically, give the primary CTA real width. Cleanest: change the diagnosis nav to `st.columns([1, 2])` or a full-width primary button (`use_container_width=True`) on its own row, with Back below/beside. Add `white-space: nowrap;` to `.stButton > button` in `theme.py` as a belt-and-suspenders guard so no CTA ever wraps into a "dice" again. Don't just shorten the label — the label is good ("Build my full plan" sells the payoff); fix the container.
- **Severity:** P1 (a wrapped primary CTA on the first screen is the loudest "hand-built by a model" tell). **Effort:** S. **Risk:** Low.

### D. Donut hover "Equity 75 75%" (number repeated)
- **Root cause:** `_allocation_donut` (views.py L379-384) sets `textinfo="label+percent"` but no `hovertemplate`, so Plotly's default hover = label + **value** + percent; since the allocation dict stores whole-number percents, value==percent (both 75). Confirmed. Same bug hits **every** donut — profile base mix AND all per-goal cards (L327, L677).
- **Fix:** add `hovertemplate="%{label}<br>%{percent}<extra></extra>"` (or `hoverinfo="label+percent"`). One line, fixes all donuts.
- **Severity:** P2 (polish, but it's visible and cheap). **Effort:** S. **Risk:** None.

### E. Visual hierarchy / depth across steps
- **Root cause:** everything is the same flat surface at the same elevation; headings, captions, disclaimers, and results all read at one visual "weight." The step bar (app.py L182-194) is a thin 3px line + a caption — it doesn't anchor the user in the flow. Stacked full-width `st.warning` disclaimers (views.py L607, L932) compete visually with actual results.
- **Fix:** (1) elevate the *results* (goal cards, total-SIP headline) above the *chrome* (disclaimers, captions) using the elevation system from item A; (2) make the total-SIP headline (`### Total SIP:` L593) a proper hero — bigger, Space Grotesk, accent-tinted card — it's the product's payoff and currently renders as a plain h3; (3) demote the repeated SEBI disclaimers to a single, smaller, consistently-styled callout (they're load-bearing for compliance but shouldn't out-shout the plan); (4) give the step bar a numbered/labeled active state, not just a color fade, so "where am I" is unambiguous.
- **Severity:** P2 (P1 for the total-SIP hero specifically — it's the climax and it's under-designed). **Effort:** M. **Risk:** Low, but respect the SACRED constraint — the disclaimer must still appear **before** any fund/category mention (L606-613); restyle, don't relocate past the fund content.

### F. Explore-slider UX ("weights should auto-adjust to sum 100")
- **Root cause:** label claims "must sum to 100% — we normalise for you" (views.py L955) while the three sliders default 33/33/34 and are independent; the code silently normalises (`ws/total_w` L974). So the UI *says* one thing and *does* another — the user sees 33+33+34 and can't make them "sum to 100" by dragging. Confirmed.
- **Fix (recommended interaction, not just a label):** **reframe as relative weights** — relabel to "How much should each metric count?" with sliders 0–100 each and a live caption "**Sharpe 45% · Alpha 30% · Consistency 25%** (of total)" computed from the normalised split, updating as they drag. This tells the truth (they're relative importances), needs no auto-balancing hack, and is one caption + label change. **Do NOT build auto-balancing sliders** — see Q4 for why they feel broken under Streamlit's rerun model.
- **Severity:** P1 (the current label is actively false → erodes the "we're rigorous" story on the one screen that names funds). **Effort:** S. **Risk:** None; internal normalisation already correct.

### G. Skeleton / loading states
- **Root cause:** two genuine waits exist — `build_plan` under `st.spinner` (views.py L580) and the LLM `explain_plan` under `st.spinner` (L622). `build_plan` is pure Python and near-instant; the LLM call is the only perceptible wait and it's currently a generic spinner.
- **Fix:** keep a spinner (not a skeleton) for `build_plan` — it's too fast to skeleton and a skeleton would flash. For the **LLM explanation only**, replace the spinner with a **skeleton placeholder** (3 shimmer lines via `st.empty()` + a CSS `@keyframes shimmer` that runs *only* on that placeholder, then gets replaced by real text). This is the ONE place an entrance-ish animation is safe: it's tied to a real async wait, not to every rerun. Everywhere else, skeletons are an anti-pattern here (deterministic content is instant; a skeleton would appear-then-vanish on every slider drag).
- **Severity:** P2 (polish; the explanation wait is real but short). **Effort:** M (needs an `st.empty()` swap pattern + one scoped keyframe). **Risk:** Medium — a shimmer keyframe *will* replay if you attach it to anything that re-renders on rerun; it must live only inside the placeholder that is immediately overwritten.

---

## 3. DEBATE ANSWERS

### Q1 — ORDERING: **Agree, with teeth. Correctness → hierarchy/depth → motion.**
Four of the seven items (sliders showing 0%, chart in millions, donut double-number, Q4 truncation) are **broken output**, not missing polish. A recruiter who drags a slider that reads "0%" concludes the tool doesn't work — no amount of hover-lift saves that. Sequence:
1. **Correctness/trust (P0/P1):** fix the sliders' `format` (they store decimals 0.0–0.20 but print `%.0f%%` → always "0%"; fix by scaling to 0–20 ints or using `format="%d%%"` on integer-percent values — the functional-critic's lane but it's a prerequisite for anything I do), the millions→lakh/cr axis, donut hover, Q4 truncation, and the diagnosis false-alarm. These also **restructure the DOM I'd animate** (e.g. the diagnosis reveal moves behind a button; the total-SIP becomes a hero card) — animating first means redoing it.
2. **Structure/hierarchy/depth:** elevation system, total-SIP hero, disclaimer demotion, step-bar clarity.
3. **Motion:** hover-lift, transitions, the single LLM skeleton.
Doing motion first is building the paint job around a car that's still up on the lift.

### Q3 — MOTION UNDER STREAMLIT: the defensible subset vs the anti-patterns
The governing fact: **Streamlit re-executes the whole script on every widget interaction, and this app recomputes live on nearly every input** (quiz scores on each radio, SIPs re-solve on each slider). So any CSS animation that plays *on element mount* re-plays on essentially every click. Verdict per effect:

**SHIP (safe — triggered by user hover or by CSS state transition, never by mount):**
- **Hover microinteractions** — card/metric lift + shadow, button lift (already present), goal-card accent glow, table-row hover highlight. These fire on `:hover`, are stateless, never replay. *This is where 80% of the "modern" feeling comes from.* Components: metric cards, goal cards (`st.container(border=True)`), Explore fund rows, both CTAs.
- **Elevation/depth (resting state)** — static `box-shadow` on cards/metrics/expander. Not animation at all; the single highest-ROI "not-flat" change. Components: every `stMetric`, every bordered container, the total-SIP hero, expander header.
- **`transition` on genuine state change** — the step bar already fades color on step change (theme.py L253); extend the same idea: metric-delta color, FOIR level color, affordability success/warning callouts can transition. Because the *element persists* across reruns and only its class/color changes, the transition fires only on real change, not on every rerun. Safe.
- **ONE skeleton/shimmer** — only on the LLM `explain_plan` placeholder (item G), because it's gated behind a real async wait and immediately replaced.

**REJECT (anti-patterns — will flash/jank on every rerun):**
- **Entrance animations** (`fadeUp`/`slide-in`/`scalePop` on cards, metrics, the shortfall reveal, step transitions). The shortfall reveal `fadeUp` would re-fire every time the user edits the amount/years/SIP number inputs on the same screen. Hard no.
- **Staggered list reveals** on goal cards / fund table rows — re-staggers on every slider drag in the results screen (SIPs re-solve live).
- **Number count-up / odometer** on the total-SIP or metrics — would re-count from 0 on every rerun; actively nauseating during slider drags. (Tempting for the hero; forbidden here.)
- **Full-page loaders / route transitions** — there are no routes; `st.session_state.step` swaps content in place. A page-transition animation has nothing to animate between and would just flash.
- **Auto-playing / looping ambient animation** (pulsing glows, animated gradients) — replays on every rerun and reads as "AI-generated demo."

**Net:** the app can feel markedly more alive using *only* hover + resting depth + state-change transitions + one scoped skeleton — and that subset is coincidentally the tasteful, professional one. The stuff that would flash is also the stuff that reads as cheap. Constraint and taste point the same direction here.

### Q4 — EXPLORE SLIDERS: **relative-weight reframe. Reject auto-balancing sliders.**
Three options considered:
- **Auto-balancing sliders** (drag one, others rebalance to keep sum=100): in Streamlit each drag triggers a full rerun; to rebalance you must write the *other* sliders' `session_state` and rerun again, causing a visible two-step "jump" and occasional fights with widget state. It *feels broken* — the opposite of the goal. **Reject.**
- **Single budget allocator** (one control splitting 100 across 3): no native Streamlit widget; you'd fake it with `st.select_slider` pairs or a custom component. Over-engineered for three weights. **Reject.**
- **Relative weights (RECOMMENDED):** keep three independent 0–100 sliders; relabel "Scoring weights (must sum to 100%)" → **"How much should each metric count?"**; show a live normalised caption ("**Sharpe 45% · Alpha 30% · Consistency 25%**") derived from the split the code *already computes* (L974). Tells the truth, zero rerun fights, one label + one caption. This is the whole fix.
Bonus: it also resolves the "confusing for laymen" half of Veer's complaint if we pair each slider with the plain-language help text that's already there (L961-967) surfaced as a visible caption, not just a tooltip.

### Q6 — ZERO-STATE: **gate the verdict behind an explicit "Check my SIP →", with an instructional empty state in the meantime.**
Options weighed:
- *Start amount at 0:* the goal amount at 0 breaks the presets (the presets are genuinely useful scaffolding) and still shows "you need ₹X/mo, you're 100% short" the moment they pick a preset. Doesn't fix the alarm. **Reject.**
- *Keep presets, but only reveal the verdict once `current_sip > 0`:* better, but a user who genuinely hasn't started (₹0, the exact person this tool should serve — see the help text L210 "Enter ₹0 if you haven't started yet") then *never* sees the reveal, which is wrong — ₹0 is a valid, important input.
- **Explicit action (RECOMMENDED):** pre-fill the preset goal + horizon (keep the scaffolding), leave `current_sip` at 0, and render an **instructional empty state** in the reveal slot: *"Enter your current SIP (₹0 is fine) and hit Check my SIP — we'll show whether you're on track."* The shortfall/on-track verdict renders **only after the button is pressed** (store a `diagnosis_checked` flag in session_state). This (a) kills the false first-paint alarm, (b) still serves the ₹0 "haven't started" user because they can press the button with 0 and get "here's what it'd take," (c) turns the reveal into an *earned* moment (a microinteraction payoff — the one place a gentle fade-in *is* acceptable because it's user-triggered, not mount-triggered). Keep the existing `has_goal` Next-gate independent so advancing still works whether or not they checked.
This is the correct fix and it dovetails with Q3: the reveal becomes the app's one legitimately-animatable entrance because it fires on a click, not on a rerun.

---

## 4. WHAT THE OTHERS MIGHT GET WRONG (I'll defend these in R2)

1. **"Add entrance animations / stagger / count-up to fix 'static'."** This is the intuitive read of Veer's feedback and it's a trap under Streamlit's rerun model — it will flash on every widget touch and read *worse* (cheaper) than the current flat state. I will hard-block mount-triggered motion and insist the "alive" feeling comes from hover + resting depth + state transitions. If a critic proposes `fadeUp` on cards, ask them where the user edits an input on the same screen (answer: every screen) — that's the replay.
2. **"Just shorten the button label to stop the wrap."** No — the label sells the payoff. The bug is the 1/6-width column (app.py L215) + `!important` padding, not the text. Fix the container + add `white-space:nowrap`; keep the copy.
3. **"Auto-balancing sliders are the modern answer to sum-to-100."** They're the *broken-feeling* answer in Streamlit specifically. Relative-weight reframe is both more honest and more robust.
4. **Someone will want to relocate/soften the SEBI disclaimer for "visual cleanliness."** SACRED constraint: it must precede any fund/category mention (views.py L606-613, L932). I'll defend restyle-in-place (smaller, single, consistent) but **never** moving it after the fund content or hiding it behind an expander.
5. **A functional critic may treat the diagnosis false-alarm as purely a logic bug and just flip a default.** It's a UX-sequencing problem (verdict-before-input) — the right fix is the action-gate + empty state, which is a shared correctness+UX change, not a one-liner default flip.

---

## 5. THINGS MISSING FROM VEER'S FEEDBACK THAT I'D FIX WHILE WE'RE IN HERE

- **The donut hover bug is not just the base-mix donut Veer saw — it's every per-goal card donut too** (views.py L677). Fix once at the helper (item D) so we don't ship it fixed in one place and broken in three.
- **`_lakh_cr` already exists** (views.py L83-90) and is used for headlines/cards — but the affordability chart y-axis (L910) and SIP-split bar (L746) still emit raw Plotly auto-format ("M"/plain). Route **all** chart ₹ axes through a lakh/cr tick formatter, not just the one chart Veer flagged, or we ship an inconsistent unit story (cards say "₹1.2 Cr", the chart beside them says "1.2M").
- **Step bar is under-communicating.** It's a 3px line + caption (app.py L182-194); labels exist in code (`["Goals","Profile","Income","Your Plan"]`) but aren't shown on the segments. Surface the labels + a numbered active pill so a first-timer always knows the 4-step shape. Low effort, high "this is a real product" payoff, no motion risk.
- **No focus-visible styling.** `theme.py` styles `:hover`/`:active`/`input:focus` but not `:focus-visible` on buttons — keyboard users get no ring. Cheap accessibility + trust add while we're in the CSS (aligns with the global anti-pattern "never `outline:none` without a replacement").
- **Emoji-in-metric-delta** (`delta="✓"` L246, `"Covered ✓"` L888): the theme hides metric-delta SVGs (L176-178) but these are literal emoji check marks in the value/delta strings — a small "AI-generated" tell. Swap for a Bootstrap Icon or a styled span to match the "real icon set, not emoji" standard the Round-0 persona rightly called out.
- **The `.stButton > button` (no `kind`) selector at theme.py L112 styles secondary buttons as primary-colored too**, then the L131 secondary rule overrides — but the cascade is fragile and depends on order. Worth tightening so hover states don't leak between button types when we add the hover-lift.
