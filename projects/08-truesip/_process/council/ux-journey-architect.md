# Council Critique — UX & User-Journey Architect

**Lens:** First-time UX, information architecture, the literal screen-by-screen flow, the data handoff at each seam, friction, "AI-generated design smells," and the minimum that makes a stranger succeed with zero instructions.
**Sources read (primary):** `linkedin-post/FINAL_POST.md`; the three READMEs; **and the actual code** — `02/dashboard/app.py`, `02/src/risk_profiler.py`, both `fund_recommender.py` files, `06/dashboard/app.py`. Arguments below are grounded in what the apps literally render today, not the marketing.

---

## 1. VERDICT

**Build it as ONE linear wizard with a single landing and ONE results dashboard — but the real work is not stitching screens (they already share a design system); it's reconciling the two SIP numbers and absorbing Size's second data-entry wall, or the "one product" illusion breaks at the third screen.**

---

## 2. ANALYSIS — screen by screen, with the exact data handoff

### The ground truth the council must internalise first
Three facts from the code change the whole conversation:

1. **They are already one design system.** All three apps ship the *identical* dark CSS: `--bg:#0A0A0E`, `--acc:#818CF8`, Space Grotesk headings, Inter body, Bootstrap Icons via CDN, the same `fadeUp`/`scalePop` keyframes, the same `.landing-wrap`, `.metric-card`, `.sip-hero`, `.fund-pick` classes. **"Make it feel like one tool" is ~80% done visually before we start.** The seams are in *flow and state*, not aesthetics. Anyone who frames this as a re-skin is solving the wrong problem.
2. **They are already three wizards** — each has a `st.session_state.step` router and a near-identical landing page with its own eyebrow, big title, pill row, and a four-stat trust row. Merging them means **deleting two landings and two "Get Started" buttons**, not building a new one.
3. **There are already TWO SIP numbers, from two different engines.** Project 2's results screen (`02/app.py` lines 826–839) renders a **"Suggested Monthly SIP ₹X — increase 10% annually"** that comes from the **LLM** (`result["monthly_sip_suggestion"]`). Project 6's whole thesis is that the SIP must be **solved backward deterministically** from a goal's future value. **If both appear in one flow, the product contradicts its own credibility spine on screen.** This is the single most important UX finding in this document.

### Screen 0 — The literal first screen a stranger sees
Today a stranger hits one of three landings. In the merged product there must be exactly **one**. What it must do in the first viewport, with zero scrolling:
- **State the whole promise as a 3-step path**, because the value *is* the chain: **"Your mix → your funds → your exact monthly SIP."** Project 2's current landing ("Find Your Perfect Investment Mix") only sells stage 1 — it undersells the integrated product.
- **One primary button.** Not three. Not "choose a tool." A stranger with zero instructions must not be asked to pick an entry point — picking *is* the cognitive load we're removing (D.1's "3 mental-model resets").
- Keep the existing trust row pattern but make the numbers tell the *pipeline* story (e.g. "2,000+ schemes · 5-factor profile · exact SIP"), not stage-1 stats.
- **Pre-existing bug to fix on contact:** Project 2's landing says *"Answer 6 questions"* but the code has **5 questions + 1 income step** (`WIZARD_STEPS` has 5 entries; `TOTAL_Q_STEPS = 5`). A merged flow inherits this off-by-one unless corrected.

### Stage A — PROFILE (5 questions + income)
**Friction:** 5 single-select radio screens, one per click, then an income screen. This is fine — it's well-built (icon, heading, plain-language hint per question, progress dots, Back button). The honest hint copy ("Be honest — emotional discipline matters") is a genuine trust signal; keep it.
**What it emits (the actual handoff payload):**
- `allocation` = `{equity, debt, gold, alternatives}` (percentages)
- `risk_label` ∈ {Conservative … Aggressive}
- `goal` = **one** string ("Wealth creation" / "Tax saving (ELSS)" / etc.)
- `monthly_income` (int)
- `risk_score` (0–100)

### SEAM 1 — Profile → Pick
**The handoff is genuinely small and clean.** `build_fund_recommendations(equity_pct, risk_label, goal)` needs only three values Profile already has. The mapping is pure rules (`02/src/fund_recommender.py`): equity>0 → Large Cap always; Aggressive adds Flexi/Mid Cap; goal=="Tax saving (ELSS)" → ELSS. Then it joins to Project 1's `scored_funds.csv` on the `category` string.
**Where it confuses or loses the user:**
- **The multi-asset → equity-only gap shows through right here.** Profile hands over a four-asset mix (equity/debt/gold/alternatives). Pick only has funds for the *equity* slice. A first-timer who just saw "Debt 55%, Gold 15%" and then sees only equity fund cards will feel the product **dropped 70% of their plan on the floor.** Today each standalone app hides this; chained, it's exposed. **This must be designed for, not ignored** — e.g. show all four asset rows, with equity expandable to specific funds and the other three carrying an honest "fund-level picks for debt/gold/alternatives are out of scope — here's the category and why."
- **Silent-empty failure mode.** Both `fund_recommender`s return `[]` if `scored_funds.csv` is missing (Project 1 never run / data gitignored). In the standalone apps that degrades quietly. In a *single advertised flow*, the user lands on "Pick" and sees **nothing**, with no explanation. The merged product must render an explicit state ("rankings unavailable right now") instead of a blank — and deployment must guarantee the CSV ships.

### SEAM 2 — Pick + goals → Size  *(the hard seam)*
This is where "one continuous flow with 0 manual re-entries" (CTQ1) is hardest, and the deck is honest that it's manual today.
**The friction is NOT mainly "re-typing income."** Income is one number Profile already has. The real wall: **Size needs a whole second data-entry burst that Profile never collected** — per-goal target amounts + horizons + inflation + step-up, then expenses, then loans/EMIs, then dependents, then city tier (`06/app.py` wizard: goals → income/expenses/loans → protection → results). Profile collected *none* of that except income. So the seam can't be "auto-filled"; **it's a genuine second form.** Pretending otherwise (a fake progress bar that implies continuity) would be a lie the user feels.
**Two concrete contradictions to resolve at this seam:**
1. **The double-SIP problem (critical).** Profile's results already show an LLM "Suggested Monthly SIP." Size computes a deterministic per-goal SIP. **One product cannot show both** without looking like it doesn't trust its own math. **Resolution: in the integrated product, Profile must STOP emitting a SIP number** — its job ends at the allocation + risk. The *only* SIP in the whole product comes from Size's annuity solver. (This also tightens CTQ2: zero numbers from the LLM.) Reframe Profile's `monthly_income` question as "we'll use this later to check your SIP is affordable," not "here's your SIP."
2. **Two notions of "goal."** Profile's `goal` is a single risk-flavour string ("Wealth creation"). Size's goals are concrete funded objectives (House ₹1.5 Cr in 12 yrs). Same word, different meaning. If both surface, users conflate them. Pick a vocabulary: Profile asks about *investing intent*; Size asks about *life goals*. Label them differently on screen.

### Stage C — SIZE + the unified results
Size is the richest screen (affordability, funding sequencer, protection, advisor's note, PDF). Its deterministic "guessed-vs-solved ~6–8% shortfall" finding is the **emotional payoff of the entire chain** and the hook of the LinkedIn post — it must be the climax of the flow, not buried in a tab.
**Friction:** waiting on the LLM happens in **Stage A**, not here (Size is pure Python, instant). So the one perceptible wait (`st.spinner("Building your allocation…")`) is early; good. Just make that spinner honest about what it's doing and never block the deterministic parts behind it.

### Should it be a linear wizard, a staged dashboard, or progressive disclosure?
**Linear wizard for the first run; a results dashboard at the end. Argue:**
- The product's entire reason to exist is to remove the "which tool do I open?" decision (D.1). A **staged dashboard/hub** re-introduces exactly that choice on screen one — it's the lighter D2 option but it surrenders the core CTQ1 benefit and reads as "a menu," which is the failure mode the charter names.
- **Progressive disclosure within each stage** (Size's protection/loan detail behind "add more detail") is right — but the *spine* must be linear so a zero-instruction user is carried, never asked to navigate.
- **The end-state, though, must be a single scrollable/ tabbed results dashboard** (Mix · Funds · SIP & affordability · Plan PDF), each section traceable, with an "edit any input" path back. Both existing apps already end in a tabbed result screen — this composes naturally. A dead-end results page (no way back to tweak an answer) is the most common Streamlit-wizard sin; Size already added an "Edit Goals" back-button for exactly this — preserve it product-wide.

### How to make it FEEL like one tool, not three stitched together
1. **One continuous progress spine** across all stages (Profile 1–6 → Funds → Plan), not three independent dot-rows that reset.
2. **One landing, one "Start," one footer, one disclaimer voice.** Today there are three footers and two disclaimer blocks with slightly different wording — unify them.
3. **Carry the user's identity forward visibly:** once "Moderate Aggressive · 60% equity" is established, echo it as a small persistent chip on later screens so the funds and SIP read as *consequences of the profile*, not a fresh app.
4. **Kill the second "Get Started."** The transition Profile→Pick→Size must be auto-advance, never a button that looks like launching a different app.
5. **One state object.** All three keep separate `st.session_state` shapes; a unified `st.session_state.profile / .picks / .plan` makes the handoff real instead of re-derived.

### "AI-generated design smells" this MUST avoid
- **Three near-identical hero landings in a row** (eyebrow + giant gradient word + 4 pills + 4 trust stats) — the single most recognisable "an LLM generated each of these" tell. Merge to one.
- **Emoji section headers / emoji as iconography** (🎯📊🧮 from the post) leaking into the UI chrome. Bootstrap Icons are already in use — stay with the real icon set, not emoji.
- **Stat rows that don't add up or repeat** ("2,000+ schemes" on three screens; "Answer 6 questions" when there are 5). Inconsistent numbers across stitched stages scream auto-generated.
- **Two different SIP figures** for the same user — the clearest "these were built separately" giveaway.
- **A fake unified progress bar** over what is really two separate forms — users feel the dishonesty when stage 2 dumps a fresh 4-section form.
- **Gradient-on-gradient + pill-overload + "Powered by AI ✨" badges.** One accent, restrained pills, named mechanisms ("annuity-due solver," "percentile scoring") instead of vague "AI."
- **Tab labels padded with spaces** (`"  Allocation  "` in `02/app.py`) to fake centering — a small but real hand-built-by-a-model artifact; do it with CSS.

### The minimum that makes a first-time user succeed with ZERO instructions
A stranger lands → clicks **one** button → answers 5 plainly-worded questions + income → sees **their mix** → auto-advances to **funds for the equity slice (with the other assets honestly labelled, not silently dropped)** → is told "now let's size it to a real goal," enters **one** goal + expenses → sees **one deterministic monthly SIP** and whether they can afford it → downloads a plan. **No point where they choose which tool to open; no point where a number's origin is unexplained; no blank screen if data is missing; exactly one SIP figure.** If all of that holds, it's a product. If any seam asks them to navigate or re-orient, it's three demos in a trench coat.

---

## 3. POSITIONS on D1–D5

- **D1 — Stack:** **Unified Streamlit, single app.** All three are already Streamlit wizards sharing one CSS system and one deploy target; Veer is new to web frameworks (CTQ6). React/Next buys polish he can't maintain and throws away the 80%-shared UI. A hybrid landing adds a second codebase for no journey benefit. One Streamlit app, multi-page or single-file router.
- **D2 — Integration depth:** **Full automated single-flow** (with progressive disclosure inside Size). A "hub" re-introduces the tool-picking decision the product exists to kill — it fails CTQ1 by design.
- **D3 — Portfolio:** **Flagship on top; keep the 3 live URLs alive.** The flagship is the "I think in products" proof; the 3 components remain 3 independent proofs and 3 working demos. Replacing them collapses 3 verifiable artifacts into 1 single point of failure.
- **D4 — MVP:** **The auto-handoff Profile→Pick→Size with ONE deterministic SIP and zero re-entry of anything Profile already knows.** Concretely: profile auto-seeds the equity fund picks, and the *only* SIP shown anywhere is Size's annuity-solved one. That single reconciliation is what turns a menu into a product.
- **D5 — Name & positioning:** **Action-led, journey-named — e.g. "Profile → Pick → Size" as the tagline under a plain noun** ("Wealth Path" / "SIP Studio"-type). Avoid "AI" in the name; lead with the outcome (your mix, your funds, your exact SIP), put "GenAI explains the why" as a supporting line.

---

## 4. BIGGEST RISK (one paragraph)

The biggest UX risk is **the integration exposes seams the standalone apps comfortably hid, and "fixing" them with a smooth-looking shell makes the dishonesty worse, not better.** Two land mines specifically: (1) **the double-SIP** — Profile already prints an LLM-suggested SIP, Size prints a deterministically-solved one, and a single flow showing both visibly contradicts the "every number is deterministic, the LLM only explains why" spine that is the whole credibility/interview story; and (2) **the multi-asset→equity-only gap and Size's second data-entry wall** — Profile promises a four-asset plan and collects only income, but Pick can only show equity funds and Size demands a full second form (goals, expenses, loans, dependents, city tier). If the product papers over these with a continuous progress bar and a single "AI plan" framing, a sharp first-time user — or worse, a recruiter — feels the stitch and downgrades trust precisely where the post claims rigor. The risk is not ugliness; it's a *credibility* failure dressed as polish.

---

## 5. TOP 3 RECOMMENDATIONS

1. **Reconcile to ONE SIP, deterministically.** Strip Profile's LLM `monthly_sip_suggestion` from the integrated flow; the only SIP anywhere is Size's annuity-due solved figure. Reframe Profile's income question as "for affordability later." This single change protects CTQ2/CTQ3 and removes the loudest "built-separately" smell.
2. **Design the multi-asset→equity-only seam honestly, on screen.** On the Pick step, render all four asset rows; expand *equity* into specific ranked funds; for debt/gold/alternatives show the category + a one-line "fund-level picks out of scope here, and why." Add an explicit non-blank state when `scored_funds.csv` is absent. Never let the user feel 70% of their plan vanished.
3. **Collapse to one landing + one continuous progress spine + one shared state object, and treat the "guessed-vs-solved ~6–8% shortfall" as the flow's climax.** Delete the two extra hero landings and "Get Started" buttons; thread `st.session_state.profile/.picks/.plan` end-to-end; echo a persistent "Moderate Aggressive · 60% equity" chip so later stages read as consequences; and land the deterministic shortfall finding as the payoff screen, not a buried tab. Fix the inherited "6 questions" copy bug on contact.
