# TrueSIP Mechanical Inventory

**Scope:** Complete factual audit of all user-facing controls, charts, jargon, buttons, CSS, and questions in the TrueSIP dashboard. No fixes proposed, no opinions — facts only for the council and build team.

> **⚠️ ORCHESTRATOR CORRECTION (2026-07-01).** Section 1's "Issue" conclusions below are **wrong** and are superseded. This inventory claimed the income/advanced sliders render correctly ("0.08 → '8%'"); they do **not**. `"%.0f%%" % 0.08` evaluates to **"0%"** (`%.0f` rounds 0.08 to 0), so every value < 0.5 renders "0%" — the exact bug Veer reported. The **5 genuinely-broken sliders** are `views.py` lines **434, 438, 447, 453, 797** (confirmed independently by the UX, Streamlit-Tech, and Finance critics + orchestrator). The explore-screen sliders (960/963/966) are the only sliders that are fine (integer 0–100, no format string). Trust the raw data columns (labels/ranges/format strings) in the tables below — but **ignore the "Issue"/"OK" verdicts in Section 1.**

---

## 1. EVERY `st.slider(...)` CALL

| File | Line | Label | Min | Max | Default | Step | `format=` String | Issue |
|------|------|-------|-----|-----|---------|------|------------------|-------|
| views.py | 434 | "Expected annual salary hike" | 0.0 | 0.20 | 0.08 | 0.01 | `"%.0f%%"` | **WILL MISRENDER**: decimal 0.08 formatted as `"%.0f%%"` → shows "8%", correct; but decimal 0.0 → shows "0%" ✓ |
| views.py | 438 | "Lifestyle (expense) inflation" | 0.0 | 0.15 | 0.06 | 0.01 | `"%.0f%%"` | **WILL MISRENDER**: same pattern as above — OK |
| views.py | 447 | "Goal cost inflation" | 0.0 | 0.15 | 0.06 | 0.01 | `"%.0f%%"` | **WILL MISRENDER**: same pattern as above — OK |
| views.py | 453 | "Annual SIP step-up" | 0.0 | 0.20 | 0.0 | 0.01 | `"%.0f%%"` | **WILL MISRENDER**: same pattern as above — OK |
| views.py | 797 | "Loan interest" | 0.0 | 0.20 | 0.09 | 0.005 | `"%.1f%%"` | **POTENTIAL MISRENDER**: decimal 0.09 formatted as `"%.1f%%"` → shows "9.0%", correct. No issue detected. |

**Summary:** All 5 sliders use `"%.0f%%"` or `"%.1f%%"` format with decimal inputs (0.0–1.0 range). The `%%` is correct Streamlit escaping for a literal `%` character. No actual misrendering issue — all format strings are valid.

---

## 2. EVERY PLOTLY CHART BUILDER FUNCTION

### `_risk_gauge(score: int, label: str)` — views.py:340–365

| Property | Present | Details |
|----------|---------|---------|
| **Chart Type** | Indicator (gauge) | `go.Indicator(mode="gauge+number")` |
| **`hovertemplate`** | No | No custom hover defined; Plotly uses default |
| **`hoverinfo`** | No | Not set |
| **Y-axis config** | N/A | Gauge has no Y-axis; uses `"axis"` key in gauge dict |
| **`tickprefix`** | No | Gauge's axis has no tickprefix |
| **`tickformat`** | No | Not set |
| **`tickvals`** | No | Axis uses `range=[0,100]` with default ticks |
| **Issues** | — | None detected; hover shows default gauge value |

### `_allocation_donut(alloc: dict, title: str = "")` — views.py:368–388

| Property | Present | Details |
|----------|---------|---------|
| **Chart Type** | Pie (donut) | `go.Pie(hole=0.6)` |
| **`hovertemplate`** | No | No custom hover; Plotly default shows label + value |
| **`hoverinfo`** | No | Not set; defaults to `"label+value+percent"` |
| **Axis config** | N/A | Pie chart has no axes |
| **Issues** | — | None detected; no number formatting on hover |

### `_sip_split_bar(split: dict)` — views.py:729–751

| Property | Present | Details |
|----------|---------|---------|
| **Chart Type** | Horizontal stacked Bar | `go.Bar(orientation="h")` |
| **`hovertemplate`** | **Yes** | Line 742: `f"{k.capitalize()}: ₹%{{x:,.0f}}/mo<extra></extra>"` |
| **Format Detail** | `"{x:,.0f}"` | Formats as integer ₹ with thousands separators (e.g., "₹5,000") — **CORRECT** |
| **X-axis config** | **Yes** | Line 746: `tickprefix="₹"` — shows ₹ before all tick values |
| **`tickformat`** | No | Not set; uses numeric format only |
| **`tickfont`** | Yes | Line 747: `color=_MUTED, size=10` |
| **Issues** | — | None detected; hover shows rupees, x-axis labeled with ₹ prefix |

### `_cashflow_chart(rows)` — views.py:894–914

| Property | Present | Details |
|----------|---------|---------|
| **Chart Type** | Grouped Bar | `barmode="group"` with two `go.Bar` traces |
| **`hovertemplate`** | No | No custom hover; Plotly default shows trace name + value |
| **Hover Format** | Default | Shows values as plain numbers (e.g., "₹500000" appears as "500000" in hover) |
| **Y-axis config** | **Yes** | Line 910: `tickprefix="₹"` — axis labels show ₹ |
| **`tickformat`** | No | Not set |
| **`tickvals`** | No | Not set; auto-calculated |
| **Issues** | **MINOR**: Hover shows values without ₹ formatting (e.g., "500000" not "₹5,00,000"), but axis labels are correct |

---

## 3. EVERY USER-FACING FINANCE/TECHNICAL TERM (JARGON) IN UI

Scanned ALL of views.py for jargon shown in UI (not comments). Flagged every term a layperson might not know.

| Term | File:Line | UI Context | Definition Needed? |
|------|-----------|-------------|-------------------|
| **Sharpe** | 960, 993–994 | `"Sharpe Ratio"` label + expander explainer | Yes — "risk-adjusted return — return per unit of volatility" |
| **Sharpe Ratio** | 993–994 | Expander: "return earned per unit of total risk (volatility)" | Yes — explained in expander |
| **Jensen's Alpha** | 963, 992–993 | `"Jensen's Alpha"` label + expander explainer | Yes — "return above what the fund's market risk (beta) alone would justify" |
| **Alpha** | 992–993 | Same as Jensen's Alpha | Yes — explained in expander |
| **Beta** | 992–993 | Mentioned in expander text | Yes — not defined inline; assumes reader knows it's market risk |
| **Consistency** | 966, 994–995 | `"Consistency"` label + expander text | Yes — "the share of rolling periods the fund beat its benchmark" |
| **Benchmark** | 994–995 | In expander explanation | Yes — not defined; assumed knowledge |
| **FOIR** | 758, 854–860 | "FOIR (fixed obligations ÷ income): X% — Level" | Yes — acronym defined inline (fixed obligations ÷ income) in line 855 |
| **blended return** | 266, 662 | `"blended annual return from..."` and `"blended return assumption"` | Somewhat — contextualized but not formally defined |
| **horizon band** | 678 | `"(equity band {band_low}–{band_high}%)"` | Yes — term used in UI but concept not explained to user |
| **horizon-appropriate** | 135, 266 | "horizon-appropriate MODERATE-AGGRESSIVE default mix" | Yes — assumes reader knows horizon means time-to-goal |
| **step-up** | 457–458, 541 | "Annual SIP step-up" and "Raise your SIP by this % each year" | Explained via label + help text |
| **SGB** | 637 | "SGB, PPF, short-duration debt" | Yes — acronym not defined (Sovereign Gold Bond) |
| **PPF** | 637 | Same; list of instruments | Yes — acronym not defined (Public Provident Fund) |
| **annuity** | 251–256, 262–263 | Not directly shown to user; buried in code comments only (line 125 says "solve the SIP via the same goal_calculator" which uses annuity math) | **Not exposed in UI** — safe |
| **EMI** | 429, 794–795, 859 | "Fixed monthly EMIs / rent" and "Existing loans... Loan EMI" | Explained by context (monthly payment for loans) — widely understood in India |
| **disposable income** | 526, 551 | `"Monthly disposable income"` = income − expenses − obligations | Not formally defined in UI but label is clear |
| **annualized return** | 597 | "Fixed planning assumptions: equity 12% · debt 7% · gold 6% expected annual return" | Not a jargon term; "annual" is clear |
| **percentile** | 996–997 | "Each metric is converted to a *within-category percentile*" | Yes — used in expander but not defined for layperson |
| **composite score** | 1009, 1035–1036 | Column header "Score" formatted as ProgressColumn | Yes — what composite means is explained in expander (line 996–997) but not obvious from column alone |
| **category rank** | 1007 | Column header "Rank" (stores `category_rank`) | Clear from context |
| **Sharpe** (field name in heading) | 989–990 | Expander: "Why these metrics?" | Yes — already in list above |
| **SEBI-registered adviser** | 56, 612, 932–936 | Disclaimer text repeatedly | Yes — acronym not defined (Securities and Exchange Board of India) |
| **educational tool** | 52, 56, 611–612 | Framing in disclaimers | Clear from context |

**Findings:**
- **8 technical terms need inline definition or tooltip:** Sharpe, Jensen's Alpha, Beta, Consistency, Benchmark, SGB, PPF, SEBI, horizon band, percentile
- **Terms adequately explained:** FOIR, step-up, EMI, blended return (contextually), disposable income
- **No UI exposure of complex math:** annuity, annualized covariance, etc. kept in code

---

## 4. EVERY `st.button(...)` LABEL

| File | Line | Label Text | Length | Wrapping Risk |
|------|------|------------|--------|----------------|
| app.py | 219 | `"← Back"` | 7 chars | No |
| app.py | 225 | `next_label` (default `"Next →"`) | 7 chars | No |
| views.py | 499 | `"✕"` (del button, inline) | 1 char | No |
| views.py | 507 | `"+ Add another goal"` | 19 chars | No |
| views.py | 698 | `f"Explore ranked {_clean_category(cat)} funds →"` | ~40–50 chars (variable) | **YES**: if category name is long (e.g., "Equity Scheme - Large Cap Fund") + prefix = 50+ chars, will wrap on mobile |
| views.py | 699 | `type="secondary"` | N/A | — |
| app.py | 405 | `"Explore all funds →"` | 19 chars | No |
| app.py | 409 | `"Start over"` | 11 chars | No |
| views.py | 266 | `next_label="Build my full plan →"` | 25 chars | No (in Step 0 nav) |
| app.py | 451 | `back_label` (dynamic: "← Back to My Plan" or "← Back to start") | ~16–18 chars | No |

**Findings:**
- **Line 698 (views.py):** Button label `f"Explore ranked {_clean_category(cat)} funds →"` can exceed 45 chars on mobile if category name is long.
  - Example: "Explore ranked Equity Scheme - Large Cap Growth & Dividend Fund funds →" = ~65 chars.
  - **Truncation risk: HIGH** on narrow viewports.
- **All other buttons:** Safe from truncation.

---

## 5. THE 5 RISK-QUIZ QUESTIONS (from `risk_profiler.py` QUESTIONS dict)

Exact text from lines 184–210 of risk_profiler.py:

| Question Key | Label Text (line) | Options | Issues |
|--------------|-------------------|---------|--------|
| **age** | "What is your age?" (186) | ["Under 25", "25–35", "35–50", "50+"] | No ellipsis; all options ≤10 chars. **OK** |
| **horizon** | "How long can you stay invested without needing this money?" (191) | ["Less than 3 years", "3–7 years", "7–15 years", "More than 15 years"] | **TRUNCATION RISK**: "More than 15 years" = 19 chars fits mobile; all ≤19 chars. **Acceptable** |
| **goal** | "What is your primary investment goal?" (195) | ["Capital preservation", "Regular income", "Tax saving (ELSS)", "Wealth creation"] | **LONG OPTION**: "Capital preservation" = 20 chars; "Tax saving (ELSS)" = 17 chars. **Fits mobile**. **OK** |
| **reaction** | "If your portfolio dropped 20% tomorrow, you would…" (200) | ["I would sell immediately to stop further losses", "I would hold and wait for recovery", "I would invest more — it's a buying opportunity"] | **TRUNCATION RISK**: "I would sell immediately to stop further losses" = 49 chars — **EXCEEDS 45-char safe threshold**. Second option = 36 chars (OK). Third = 49 chars — **ALSO EXCEEDS**. |
| **debt** | "What are your current debt obligations?" (205) | ["High (home loan, car loan, etc.)", "Moderate (credit card, personal loan)", "None"] | **TRUNCATION RISK**: "High (home loan, car loan, etc.)" = 33 chars (OK). "Moderate (credit card, personal loan)" = 37 chars (OK). "None" = 4 chars (OK). **All safe** |

**Findings:**
- **Question labels:** None end with ellipsis; all clear and under 60 chars. **OK**
- **Options with truncation risk (>45 chars):**
  - Line 202: Option "I would sell immediately to stop further losses" = **49 chars** — **WILL WRAP/TRUNCATE on mobile**
  - Line 202: Option "I would invest more — it's a buying opportunity" = **49 chars** — **WILL WRAP/TRUNCATE on mobile**
- **Safe options:** All others ≤37 chars.

---

## 6. CSS BLOCKS IN `shared/theme.py` — CURRENT TRANSITIONS, ANIMATIONS, HOVERS, TRANSFORMS

Scanned entire theme.py (lines 1–287). Listed every CSS selector and its current motion/animation/transition properties.

| Selector | Lines | Styles What | Has `transition`? | Has `animation` / `@keyframes`? | Has `:hover` | Has `transform` | Notes |
|----------|-------|-------------|-------------------|----------------------------------|--------------|-----------------|-------|
| `:root { }` | 42–55 | Design tokens (colors) | No | No | N/A | No | — |
| `html, body, [class*="css"]` | 58–62 | Base background + font | No | No | N/A | No | — |
| `h1–h6, .stMarkdown h1–h4` | 65–71 | Headings styling | No | No | N/A | No | — |
| `.main .block-container` | 74–78 | Main container | No | No | N/A | No | — |
| `div[data-testid="stVerticalBlock"] > div` | 81–87 | Cards | No | No | N/A | No | — |
| `[data-testid="stSidebar"]` | 90–93 | Sidebar | No | No | N/A | No | — |
| `input, textarea, select, [data-baseweb="input"]…` | 96–104 | Form inputs (base) | No | No | N/A | No | — |
| `input:focus, textarea:focus` | 105–108 | Input focus state | No | No | No (inline focus state) | No | Box-shadow only |
| `.stButton > button[kind="primary"], .stButton > button` | 111–121 | Primary buttons (base) | **YES** (line 120) | No | No | No | `transition: background 150ms ease, transform 100ms ease` |
| `.stButton > button:hover` | 122–125 | Primary button hover | No (defined in parent) | No | **YES** | **YES** (line 124) | `transform: translateY(-1px)` |
| `.stButton > button:active` | 126–128 | Primary button active | No | No | No | **YES** (line 127) | `transform: translateY(0)` |
| `.stButton > button[kind="secondary"]` | 131–135 | Secondary buttons (base) | No | No | No | No | — |
| `.stButton > button[kind="secondary"]:hover` | 136–139 | Secondary button hover | No | No | **YES** | No | Color + border changes only |
| `[data-baseweb="select"]` | 142–149 | Select boxes | No | No | No | No | — |
| `[data-testid="stSlider"] > div > div > div > div` | 152–154 | Slider track | No | No | No | No | — |
| `[data-testid="stProgress"] > div > div` | 157–159 | Progress bars | No | No | No | No | — |
| `[data-testid="stMetric"]` | 162–167 | Metrics (cards) | No | No | No | No | — |
| `[data-testid="stMetricLabel"]` | 168–171 | Metric label text | No | No | No | No | — |
| `[data-testid="stMetricValue"]` | 172–175 | Metric value text | No | No | No | No | — |
| `[data-testid="stMetricDelta"] svg` | 176–178 | Metric delta icon | No | No | No | No | `display: none` |
| `[data-testid="stInfo"]` | 181–186 | Info callout | No | No | No | No | — |
| `[data-testid="stWarning"]` | 187–191 | Warning callout | No | No | No | No | — |
| `[data-testid="stError"]` | 192–196 | Error callout | No | No | No | No | — |
| `[data-testid="stSuccess"]` | 197–201 | Success callout | No | No | No | No | — |
| `[data-testid="stExpander"]` | 204–215 | Expanders (base) | No | No | No | No | — |
| `[data-testid="stExpander"] summary` | 209–212 | Expander label | No | No | No | No | — |
| `[data-testid="stExpander"] summary:hover` | 213–215 | Expander label hover | No | No | **YES** | No | Color change only |
| `[data-testid="stDataFrame"]` | 218–232 | Tables / DataFrames | No | No | No | No | — |
| `thead tr th` | 223–229 | Table headers | No | No | No | No | — |
| `tbody tr:nth-child(even) td` | 230–232 | Table rows (alternating) | No | No | No | No | — |
| `[data-testid="stSidebarNavItems"], [data-testid="collapsedControl"], header[data-testid="stHeader"]` | 235–239 | Streamlit nav (hidden) | No | No | No | No | `display: none` |
| `.truesip-step-bar` | 242–247 | Step bar container | No | No | No | No | — |
| `.truesip-step` | 248–254 | Step indicator (base) | **YES** (line 253) | No | No | No | `transition: background 300ms ease` |
| `.truesip-step.active` | 255–257 | Step indicator (active) | No (uses parent transition) | No | No | No | — |
| `.truesip-step.done` | 258–260 | Step indicator (done) | No (uses parent transition) | No | No | No | — |
| `.text-muted` – `.text-danger` | 263–267 | Utility text colors | No | No | No | No | — |

**Summary of Motion Properties:**

| Motion Type | Present | Details |
|-------------|---------|---------|
| **`transition`** | **YES** | 2 locations: (1) `.stButton > button` (line 120): `transition: background 150ms ease, transform 100ms ease`; (2) `.truesip-step` (line 253): `transition: background 300ms ease` |
| **`animation` / `@keyframes`** | **NO** | No keyframe animations defined anywhere |
| **`:hover` effects** | **YES** | 4 locations: (1) `.stButton > button:hover` (line 123): color + transform; (2) `.stButton > button[kind="secondary"]:hover` (line 137): color + border; (3) `.stExpander] summary:hover` (line 214): color only; (4) Implicit in slider/input focus |
| **`transform`** | **YES** | 2 locations: (1) `.stButton > button:hover` (line 124): `transform: translateY(-1px)`; (2) `.stButton > button:active` (line 127): `transform: translateY(0)` |

**Findings for motion work:**
- **Button interactions are fully animated:** primary buttons have 150ms background + transform on hover, active state resets transform.
- **Step bar transitions:** background color changes are animated 300ms on `.truesip-step`.
- **No page-level animations:** no fade-ins, slides, or entrance animations defined.
- **No component entrance delays:** all components appear instantly.
- **Missing motion patterns:**
  - No expander expand/collapse animation (Streamlit native handles this, not CSS)
  - No loading state animations (spinners are Streamlit native)
  - No skeleton screen transitions
  - No scroll-triggered animations
  - No micro-interactions on cards (e.g., lift on hover)

---

## APPENDIX: CROSS-REFERENCE SUMMARY

### Slider-to-Finance-Term Mappings
- "Expected annual salary hike" (views.py:434) → Finance term: salary growth assumption
- "Lifestyle (expense) inflation" (views.py:438) → Finance term: lifestyle inflation rate
- "Goal cost inflation" (views.py:447) → Finance term: goal inflation (already explained inline)
- "Annual SIP step-up" (views.py:453) → Finance term: SIP annual step-up (explained via help text)
- "Loan interest" (views.py:797) → Finance term: loan interest rate

### Chart-to-Slider-Value Mappings
- `_cashflow_chart` (views.py:894) displays `salary_hike_pct` and `expense_inflation_pct` from sliders
- `_sip_split_bar` (views.py:729) displays split values derived from goal allocation (no direct slider input)
- No chart directly visualizes the "Loan interest" slider; used only in `protection.compute_foir()`

### Button-to-View Mappings
- "Build my full plan →" (app.py:266) → routes to step 1 (Profile)
- "Explore ranked {category} funds →" (views.py:698) → routes to "explore" view with category hand-off
- "Explore all funds →" (app.py:405) → routes to "explore" view without category pre-selection
- "Start over" (app.py:409) → resets session_state to defaults

---

**INVENTORY COMPLETE.** All facts; no repairs, no proposals.
