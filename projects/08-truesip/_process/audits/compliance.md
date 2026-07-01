# TrueSIP Compliance Audit
**Date:** 2026-06-30  
**Auditor:** compliance-guardrail-checker  
**Files audited:**  
- `dashboard/app.py`  
- `dashboard/views.py`  
- `shared/planning_engine.py`

**Acceptance criterion (verbatim gate):**  
> "No screen and no continuous user path may combine a personalized output (anything derived from the user's quiz/income/goals) with a specific named security AND an amount or buy-directive; the moment all three co-occur it is advice, not education."

---

## 1. PAIRING SCAN

### 1a. Where is `scheme_name` rendered?

**Evidence:** `scheme_name` appears in the rendered UI at exactly one location:

- `dashboard/views.py:1008` — inside `_render_fund_table()`, in the column mapping dict `{"scheme_name": "Scheme", ...}`. This function is called only by `view_explore()` (line 987), which is the "Explore Funds" screen.

**PASS** — Named funds (`scheme_name`) are rendered ONLY in `view_explore` → `_render_fund_table`. No other view function touches `scheme_name`.

### 1b. Does `view_explore` co-render a personalized amount alongside a named fund?

The `view_explore` function body (`views.py:922–1000`) reads exclusively:
- `df` (the seed DataFrame — general, not user-specific)
- `st.session_state.pop("explore_category", None)` — a CATEGORY STRING consumed and immediately popped (views.py:944)
- `st.session_state.pop("explore_reset_weights", False)` — a boolean flag (views.py:945)
- `st.session_state.get("_explore_weights")` — the user's own slider weights from the same screen (views.py:958)

It does NOT read `risk_label`, `goals`, `income`, `risk_score`, `base_allocation`, `plan`, `sip_params`, or any other profile/goal/income key. No personalized SIP amount, no buy-directive, appears anywhere in `view_explore` or `_render_fund_table`.

**PASS** — `view_explore` is neutral/general. Named funds appear with metrics (Sharpe, Alpha, Consistency, returns, AUM) only. Zero personalized figures on the same surface.

### 1c. Does `view_explore` receive a "#1 for you" pre-ranking from the user's profile?

The `explore_category` handoff from a goal card (`views.py:701`) carries only a CATEGORY STRING (e.g., `"Equity Scheme - Large Cap Fund"`) and sets `explore_reset_weights=True` (line 702), which forces the weights back to the neutral equal-thirds default (33/33/34) on load (lines 945, 958). No `risk_label`, no `income`, no `goals` are threaded through.

**PASS** — Goal-card handoff is category-string only, with neutral weights. No profile-derived sort bias.

---

## 2. PERSONALIZED-PATH TERMINATION

### 2a. Does `view_results` (step 3 / "Your Plan") ever name a specific fund?

Trace of personalized plan output in `view_results` (`views.py:561–644`):
- Calls `build_plan(goals, risk_label, income, sip_params, df)` — returns the plan dict.
- Renders per-goal cards via `_render_goal_card(g)` (`views.py:647–721`).

Inside `_render_goal_card`:
- Renders `monthly_sip`, `total_invested`, `wealth_gained`, `asset_split` donut, `sip_split` bars (all personalized — derived from the quiz and income).
- The equity slice section (`views.py:686–709`) renders the ₹ equity SIP amount and routes to the explore screen via `st.session_state["explore_category"] = cat` (a category STRING) plus `explore_reset_weights = True`. It explicitly states "We don't pick a fund *for you*" (line 695).
- Debt/gold notes (`views.py:711–721`) list generic product TYPES ("PPF", "SGB", "short-duration debt") — no scheme names, no scores/ranks.

`build_plan` (`planning_engine.py`) emits only `equity_category` (a category string or None) and never calls `get_top_funds` or embeds a `scheme_name`. The planning_engine module comment at line 112–113 confirms: "NEVER imports or calls data_store.get_top_funds. NEVER embeds a scheme_name / AMC / any named security."

**PASS** — "Your Plan" terminates at allocation + solved SIP + scoring methodology. No named fund is pre-selected or pre-ranked for the user on this screen or via this path.

### 2b. `planning_engine.build_plan` — does it embed any named fund?

Full text of `build_plan` (`planning_engine.py:445–570`) reviewed. The only place `df` is consumed is `_resolve_category(equity_category_for(goal), df)` (line 508), which reads only `df["category"]` to validate the category string exists. It never selects a row by fund name, never reads `scheme_name`, never calls `get_top_funds`.

**PASS** — `build_plan` outputs category strings only; no named fund embedded anywhere.

---

## 3. DISCLAIMERS

Required at: diagnosis (step 0), profile (step 1), results (step 3 before fund/category mention), explore.

| Screen | Location | Disclaimer Text | Verdict |
|--------|----------|-----------------|---------|
| Step 0 — Diagnosis | `views.py:229` (`_disclaimer()` call at end of `view_diagnosis`) | "Educational tool — not investment advice. TrueSIP is not a SEBI-registered investment adviser…" | **PASS** |
| Step 1 — Profile | `views.py:338` (`_disclaimer()` call at end of `view_profile`) | Same `_DISCLAIMER` string | **PASS** |
| Step 2 — Goals & Income | `views.py:475` (`_disclaimer()` call at end of `view_goals_income`) | Same `_DISCLAIMER` string | **PASS** (bonus — not required by checklist, present anyway) |
| Step 3 — Results | `views.py:606–613` (`st.warning(...)`) — appears BEFORE the per-goal cards loop at line 617 | "Educational, not investment advice. Not a SEBI-registered adviser… specific funds are never recommended for you here…" | **PASS** — disclaimer precedes any fund/category mention |
| Explore Funds | `views.py:932–936` (`st.warning(...)`) at top of `view_explore`, before any fund table | "Educational, not investment advice. Not a SEBI-registered adviser… Past performance does not indicate future results." Additional `_disclaimer()` at line 1000 (foot of screen) | **PASS** |

Additionally, `app.py:126–130` embeds a global "Not SEBI-registered investment advice." disclaimer in the Streamlit `menu_items["About"]` string (always visible via the hamburger menu).

**PASS** — All required disclaimer placements confirmed. Disclaimer appears before any fund or category content on every advice-shaped screen.

---

## 4. DATA HYGIENE

### 4a. Is user PII persisted to disk, database, or any at-rest store?

Full scan of `dashboard/app.py` and `dashboard/views.py` for file-write, database, or network-write patterns:

- **`open(` writes:** Not found in either dashboard file.
- **`sqlite` / `json.dump` / `pickle` / `.to_csv` / `.to_excel` / database connections:** Not found in any `.py` file under the project (grep across all `*.py` confirmed only `planning_engine.py:299` contains `db` as a variable name for `debt`, not a database).
- **Session state:** All user inputs (`goals`, `risk_score`, `risk_label`, `base_allocation`, `income`, `sip_params`, `plan`, `explanation`, `advanced`) are held exclusively in `st.session_state`, which is in-memory per browser session. State resets on browser close or "Start over" (`app.py:410–412`).

**PASS** — Stateless session only. No PII persisted at rest.

---

## Summary Table

| # | Checklist Item | Verdict | Evidence |
|---|---------------|---------|----------|
| 1a | Named fund (`scheme_name`) rendered ONLY in `view_explore` | PASS | `views.py:1008` — sole occurrence; called only by `view_explore` at `views.py:987` |
| 1b | `view_explore` does NOT co-render a personalized amount with a named fund | PASS | `views.py:922–1000` — no session_state profile/plan keys read; no SIP amount rendered |
| 1c | `view_explore` ranking is neutral/general (no "#1 for you" bias) | PASS | `views.py:944–968` — category handoff only; `explore_reset_weights=True` forces equal-thirds weights |
| 2a | "Your Plan" terminates at allocation + SIP + methodology; no named fund pre-selected | PASS | `views.py:647–721` — equity slice hands off category string only; "We don't pick a fund for you" (line 695) |
| 2b | `planning_engine.build_plan` embeds no named fund | PASS | `planning_engine.py:445–570` — only `df["category"]` read; `get_top_funds` never called |
| 3a | SEBI disclaimer at Diagnosis (step 0) | PASS | `views.py:229` |
| 3b | SEBI disclaimer at Profile (step 1) | PASS | `views.py:338` |
| 3c | SEBI disclaimer at Results (step 3), before any fund/category mention | PASS | `views.py:606–613` (precedes goal cards loop at line 617) |
| 3d | SEBI disclaimer at Explore Funds | PASS | `views.py:932–936` and `views.py:1000` |
| 4  | No PII persisted at rest (stateless session_state only) | PASS | No file/db writes found in any dashboard `.py` file |

---

GATE: PASS

---

## Amendment 2026-07-01 — feedback build (ladder incl. Mid/Small Cap, importance selector, jargon/Explore/motion)

**Auditor:** compliance-guardrail-checker  
**Files re-read (full):**
- `dashboard/views.py` (1224 lines — complete)
- `dashboard/app.py` (501 lines — complete)
- `shared/theme.py` (436 lines — complete)
- `shared/planning_engine.py` L340–459 (equity-category section)  
**Reference:** `_process/feedback-2026-07/PLAN.md` (GUARDRAILS CHECKLIST) + `_process/feedback-2026-07/round1/compliance.md`

---

### Re-scan Results (7 gate items)

---

#### Item 1 — Mode B neutrality: `view_explore` session_state reads

**Criterion:** `view_explore` reads ONLY `explore_category`, `explore_reset_weights`, `_explore_weights`. Zero plan/profile keys (`risk_label`, `goals`, `plan`, `income`, etc.).

**Evidence (grep of all `session_state` accesses in `view_explore`, `views.py:1075–1224`):**

```
views.py:1097  handoff = st.session_state.pop("explore_category", None)
views.py:1098  reset_weights = st.session_state.pop("explore_reset_weights", False)
views.py:1114  saved = st.session_state.get("_explore_weights") if not reset_weights else None
views.py:1136  st.session_state["_explore_weights"] = {"sharpe": ws, "alpha": wa, "consistency": wc}
```

No read of `risk_label`, `goals`, `plan`, `income`, `sip_params`, `base_allocation`, `risk_score`, or any profile/plan key. The four accesses are exactly the three permitted keys plus one write-back to `_explore_weights` (which is itself a Mode B screen-local key).

**VERDICT: PASS**

---

#### Item 2 — No named security in Mode A: `_render_goal_card` equity hand-off

**Criterion:** The personalized plan/goal cards emit only equity CATEGORY strings (now including "Mid Cap" / "Small Cap" from the 6-band ladder) — never a `scheme_name`, AMC name, or ISIN. The "→ **<Category>** funds" pattern must hold.

**Evidence:**

```python
# views.py:786–798 — _render_goal_card (equity slice section)
st.markdown(
    f"{_rupees(eq_rupees)}/mo → **{_clean_category(cat)}** funds. "
    "We don't pick a fund *for you*; compare the ranked options yourself."
)
if st.button(f"Explore ranked {_clean_category(cat)} funds →",
             key=f"explore_{name}", type="secondary"):
    st.session_state["explore_category"] = cat   # ← category STRING only
    st.session_state["explore_reset_weights"] = True
    st.session_state["step"] = "explore"
```

`cat` is derived from `g.get("equity_category")`, which `build_plan` populates exclusively from `equity_category_for(goal)` → the `_CATEGORY_LADDER` returning one of `{LARGE_CAP, LARGE_AND_MID_CAP, FLEXI_CAP, MID_CAP, SMALL_CAP, None}` — all AMFI/SEBI scheme-category strings, never scheme names. Confirmed in `planning_engine.py:369–403`.

`_clean_category()` at `views.py:818–820` strips the `"Equity Scheme - "` prefix for display only; it never outputs a fund name.

No `scheme_name`, AMC, or ISIN appears anywhere in `view_results` or `_render_goal_card`.

**VERDICT: PASS**

---

#### Item 3 — Importance framing: context not verdict; volatility caveat for Mid/Small Cap

**Criterion:** The importance selector changes only the category string. Card copy is CONTEXT framing, never the word "recommend". When Mid Cap / Small Cap is the category, the one-line volatility caveat is present.

**Evidence:**

Importance-aware framing block in `_render_goal_card` (`views.py:760–779`):

```python
if cat in (MID_CAP, SMALL_CAP):
    # Volatility caveat rendered as .truesip-vol-caveat styled tag:
    "This goal ({years}-year horizon, {importance}) sits in the "
    "{cat_label} band — higher volatility than large-cap funds. "
    "Explore those funds below and confirm fit with an adviser."
elif cat:
    st.caption(
        f"This goal ({g['years']:.0f}-year horizon, {importance}) maps to the "
        f"**{cat_label}** equity band — explore those funds below."
    )
```

Neither branch uses "recommend", "you should", or any directive verb. The Mid/Small Cap branch explicitly adds the volatility caveat ("higher volatility than large-cap funds") plus an adviser-confirmation prompt. The standard category branch uses "maps to" (descriptive) and "explore those funds below" (opt-in invitation). The importance value appears as contextual metadata in the framing sentence, not as a verdict driver.

**VERDICT: PASS**

---

#### Item 4 — Local caveats: per-metric "Past performance" adjacent to every renamed metric; FOIR note intact

**Criterion:** Sharpe/Alpha/Consistency each carry "Past performance does not indicate future results" adjacent (slider help text or expander). FOIR carries the "planning benchmark, not eligibility" note.

**Evidence — slider `help=` text (`views.py:1116–1135`):**

| Metric | Slider label | `help=` caveat |
|--------|-------------|----------------|
| Sharpe | "Return per unit of risk (Sharpe)" | "…historically. Past performance does not indicate future results." (L1119–1120) |
| Alpha | "Manager's track record (Alpha)" | "…historical data. Past performance does not indicate future results." (L1126–1127) |
| Consistency | "How often it beat benchmark (Consistency)" | "…historically. Past performance does not indicate future results." (L1133–1134) |

Each caveat is in the `help=` tooltip of the same slider widget that carries the metric label — same visible unit, per the Round-1 ruling.

**Evidence — "Why these metrics?" expander (`views.py:1165–1183`):** Each metric entry ends with an italicised "Past performance does not indicate future results." line — present for all three.

**Evidence — FOIR (`views.py:973–980`):**
```python
st.caption(
    "FOIR = EMIs + fixed obligations ÷ income. Lenders typically view above ~50–55% as "
    "stretched — a planning benchmark, not a guarantee of loan eligibility. Lender criteria vary."
)
```
Exact approved copy from Round-1 Q5 — "planning benchmark, not a guarantee of loan eligibility. Lender criteria vary."

**VERDICT: PASS**

---

#### Item 5 — Disclaimer placement: pre-fund SEBI disclaimer before any fund/category mention on Results AND Explore; Explore "Past performance" banner intact

**Criterion:** The pre-fund SEBI disclaimer appears BEFORE any fund or category mention on Results and Explore. The Explore "Past performance…" banner at what was previously L935 is intact.

**Evidence — Results (`views.py:667–677`):**

```python
# SEBI disclaimer BEFORE any fund/category mention (SACRED — must stay here)
st.markdown(
    '<div class="truesip-disclaimer">'
    '<strong>Educational, not investment advice. Not a SEBI-registered adviser.</strong> '
    'SIP amounts are deterministically solved from your goals using documented '
    'planning assumptions (not forecasts). Fund <em>categories</em> are shown for the '
    'equity slice; specific funds are never recommended for you here — explore '
    'them yourself on the neutral <em>Explore Funds</em> screen.'
    '</div>',
    unsafe_allow_html=True,
)
# Per-goal cards loop starts at views.py:680 — AFTER the disclaimer above.
```

The disclaimer is now a styled `div.truesip-disclaimer` callout (restyled per PLAN.md §2.2) rather than `st.warning`. It remains in the same code position — before the `for g in plan["goals"]: _render_goal_card(g)` loop at L681. Position (before fund content) is preserved; only the visual style changed. This is explicitly permitted by Round-1 ruling on §2.2: "restyle in place; never move it after the fund content."

**Evidence — Explore banner (`views.py:1085–1089`):**

```python
st.warning(
    "**Educational, not investment advice. Not a SEBI-registered adviser.** Rankings are "
    "built from historical metrics (Sharpe, Jensen's Alpha, return consistency vs the "
    "category). **Past performance does not indicate future results.**"
)
```

Banner is at the top of `view_explore`, before the category selector, sliders, and fund table. The "Past performance does not indicate future results" bolded phrase is intact, in the same `st.warning` block.

Additional `_disclaimer()` call at `views.py:1185` (foot of Explore screen) is also present.

**Importance UI disclaimer (`views.py:514–518`):** A `st.caption` reading "Educational tool — not investment advice. Not a SEBI-registered adviser." appears at the top of `_render_goal_editor()`, above the importance selectbox widgets — satisfying the Round-1 guardrail that the disclaimer must be placed ABOVE any importance-derived UI block.

**VERDICT: PASS**

---

#### Item 6 — Emphasis guardrail: "Explore … funds →" button stays `type="secondary"`; no countdown/urgency/timer

**Criterion:** The per-card Explore button must be `type="secondary"`, not primary/animated. No countdown, urgency badge, or timer anywhere.

**Evidence:**

```python
# views.py:792–793
if st.button(f"Explore ranked {_clean_category(cat)} funds →",
             key=f"explore_{name}", type="secondary"):
```

Confirmed `type="secondary"`.

**CSS audit (`shared/theme.py`):** The `.stButton > button[kind="secondary"]` rule at `theme.py:144–153` gives secondary buttons `background: transparent`, `color: var(--text-muted)`, `border: 1px solid var(--border)` on rest, and on hover only changes text and border color — no animation, no scale, no glow. Primary buttons have a `translateY(-1px)` hover-lift; secondary buttons do NOT.

No `@keyframes`, `animation:`, countdown, timer, progress-toward-close, or urgency element appears anywhere in `theme.py` or `views.py` except the shimmer skeleton scoped to `.truesip-skeleton-line` (the LLM wait placeholder) — which is not attached to any fund-adjacent element and fires only during the `explain_plan` call.

The "Explore all funds →" button at `app.py:424` is also `type="secondary"`.

**VERDICT: PASS**

---

#### Item 7 — Issue A fixed: "What to do next" directive copy

**Criterion:** `views.py` "What to do next" must no longer say "Automate the SIPs at the amounts above" (the directive-adjacent Round-1 Issue A). Must be the softened adviser-referred copy.

**Evidence (`views.py:702–714`):**

```python
st.markdown(
    "1. **Review the SIP amounts above** with a SEBI-registered adviser or distributor "
    "who can set them up for you.\n"
    "2. For each goal's **equity slice**, open *Explore Funds* (button on each card) to compare "
    "ranked funds in that category — then pick what fits.\n"
    "3. The **debt/gold slices** name the instrument types (SGB, PPF, "
    "short-duration debt) — these are planning pointers, not ranked picks.\n"
    "4. Open **Advanced wealth check** below to confirm insurance, emergency fund and "
    "year-by-year affordability."
)
```

"Automate the SIPs" is completely gone. Step 1 now reads "Review the SIP amounts above with a SEBI-registered adviser or distributor who can set them up for you." — the exact softened rewrite from Round-1 Issue A. No buy-directive language ("automate", "start now", "set up") remains.

**VERDICT: PASS (Issue A closed)**

---

### New Compliance Surface Observations

**Motion / CSS additions (theme.py):** The shimmer skeleton (`@keyframes truesip-shimmer`) is correctly scoped to `.truesip-skeleton-line` / `.truesip-skeleton-card` and is attached only to the LLM explanation placeholder (`views.py:687–693`), which lives on the personalized plan screen but carries zero named funds. The card hover-lift (`translateY(-2px)`) on `[data-testid="stVerticalBlock"]` and metric elevation on `[data-testid="stMetric"]` are passive `:hover` CSS — they fire on user hover, never auto-replay on Streamlit rerun, and never create a "plan → animate → fund" visual funnel (the explore hand-off button stays secondary per Item 6). No ambient loop, no entrance animation, no urgency element. Motion additions are clean.

**Issue B status (from Round-1):** `_render_goal_card` equity rupees + category pattern (`views.py:786–790`) is unchanged: `₹X,XXX/mo → Large Cap funds.` The category string may now be Mid Cap or Small Cap in addition to the previous three categories. This continues to be the designed ceiling — correct, not a violation. The volatility caveat for Mid/Small Cap is the new addition that compensates for the higher-risk category routing.

**No new issues identified.**

---

### Amendment Summary Table

| # | Gate Item | Verdict | Key Evidence (file:line) |
|---|-----------|---------|--------------------------|
| G1 | Mode B neutrality — `view_explore` reads zero plan/profile keys | PASS | `views.py:1097–1136` — only `explore_category` (pop), `explore_reset_weights` (pop), `_explore_weights` (get/set) |
| G2 | No named security in Mode A — category strings only, incl. Mid Cap / Small Cap | PASS | `views.py:786–798`; `planning_engine.py:369–403` — category ladder returns AMFI strings only |
| G3 | Importance framing — context not verdict; Mid/Small Cap volatility caveat present | PASS | `views.py:760–779` — "maps to … band", no "recommend"; vol caveat on Mid/Small at L765–772 |
| G4 | Local caveats — per-metric "Past performance" adjacent; FOIR note intact | PASS | Slider `help=`: L1119–1120, L1126–1127, L1133–1134. Expander: L1170, L1174–1175, L1178–1179. FOIR: L978–980 |
| G5 | Disclaimer placement — SEBI disclaimer before fund/category on Results + Explore; Explore banner intact | PASS | Results: L667–677 (before card loop at L681). Explore banner: L1085–1089. Importance UI: L515–518 |
| G6 | Emphasis guardrail — Explore button `type="secondary"`; no countdown/urgency/timer | PASS | `views.py:793`; `theme.py:144–153` (secondary button CSS, no animation); no timer/countdown found |
| G7 | Issue A fixed — "Automate the SIPs" directive copy replaced | PASS | `views.py:705–714` — "Review the SIP amounts above with a SEBI-registered adviser…" |

---

GATE: PASS
