# Streamlit Technical Feasibility — Round 1 Analysis
**Critic role:** STREAMLIT TECHNICAL FEASIBILITY  
**Date:** 2026-07-01  
**Files read:** `dashboard/app.py`, `dashboard/views.py`, `shared/theme.py`, `shared/cashflow_projection.py`, `shared/planning_engine.py` (skimmed)

---

## 1. Streamlit Version Detected

**Root `requirements.txt`:** `streamlit>=1.35`  
**Project `requirements.txt`:** `streamlit>=1.35`

Relevant version-gated features used in this analysis:

| Feature | Min version | Notes |
|---|---|---|
| `st.container(border=True)` | 1.27 | Already used in `_render_goal_card` |
| `st.status()` | 1.28 | Available but unused; `st.spinner` used instead |
| `st.column_config.ProgressColumn` | 1.26 | Already used in `_render_fund_table` |
| `on_change` callbacks on `st.slider` | 1.0+ | Core feature, always available |
| `st.empty()` for placeholder patterns | 1.0+ | Always available |
| `st.fragment` (partial reruns) | 1.37 | **NOT available at >=1.35**; do not rely on it |
| `st.rerun(scope="fragment")` | 1.37 | **NOT available** |

Critical consequence: `st.fragment` (which would solve the slider auto-sum rerun loop cleanly) is **not guaranteed** at >=1.35. All slider-interaction solutions below must work without it.

---

## 2. Exact Fix Mechanisms — All Six Bugs

### Fix 1: Percent Sliders Show "0%" (format="%.0f%%" on decimal values)

**Root cause:** `format="%.0f%%"` applies `printf` formatting to the raw slider *value*, which is a decimal (0.08). `%.0f` rounds 0.08 to `0` (it truncates to zero decimal places), then `%%` appends a literal `%` sign — producing `"0%"` instead of `"8%"`. Same for any value < 0.5: they all round to `0%`.

**Complete list of buggy sliders** (file:line, all in `dashboard/views.py`):

| Line | Slider label | Range | Value type | Bug |
|---|---|---|---|---|
| 434–436 | "Expected annual salary hike" | 0.0–0.20, step 0.01 | decimal | `format="%.0f%%"` → "0%" at 0.08 |
| 438–440 | "Lifestyle (expense) inflation" | 0.0–0.15, step 0.01 | decimal | same |
| 447–449 | "Goal cost inflation" | 0.0–0.15, step 0.01 | decimal | same |
| 453–455 | "Annual SIP step-up" | 0.0–0.20, step 0.01 | decimal | same |
| 797–798 | "Loan interest" | 0.0–0.20, step 0.005 | decimal | `format="%.1f%%"` → "0.1%" at 0.09 (off by 10x) |

**The explore-screen sliders (lines 960, 963, 966) are NOT affected** — they use integer ranges (0–100, step 1) with no format string; Streamlit renders integers correctly by default.

**Two viable approaches; Approach B is preferred:**

**Approach A — Convert slider to percent-unit range (simpler, no division needed at store time):**
```python
# views.py L434-436 — BEFORE (broken):
salary_hike_pct = st.slider(
    "Expected annual salary hike", 0.0, 0.20,
    float(income_prev.get("salary_hike_pct", 0.08)), 0.01, format="%.0f%%",
)

# AFTER — slider in percent units (0–20 int), divide on store:
_salary_hike_display = st.slider(
    "Expected annual salary hike", 0, 20,
    int(round(float(income_prev.get("salary_hike_pct", 0.08)) * 100)),
    1, format="%d%%",
)
salary_hike_pct = _salary_hike_display / 100.0
```

Apply the same pattern to all four goal/income sliders. For loan_rate (line 797, step 0.005 = 0.5%):
```python
# L797-798 — BEFORE (broken):
loan_rate = st.slider("Loan interest", 0.0, 0.20,
                      float(adv_prev.get("_loan_rate", 0.09)), 0.005, format="%.1f%%")

# AFTER — half-percent steps, displayed correctly:
_loan_rate_display = st.slider(
    "Loan interest", 0, 20,
    int(round(float(adv_prev.get("_loan_rate", 0.09)) * 100)),
    1, format="%d%%",    # 1% steps; if 0.5% granularity needed use float range below
)
loan_rate = _loan_rate_display / 100.0

# If 0.5% steps MUST be preserved (loan rate precision matters):
_loan_rate_display = st.slider(
    "Loan interest", 0.0, 20.0,
    round(float(adv_prev.get("_loan_rate", 0.09)) * 100, 1),
    0.5, format="%.1f%%",    # NOW the value IS already in %, so %.1f%% works
)
loan_rate = _loan_rate_display / 100.0
```

**Approach B — Keep decimal range, fix format string (fewest code changes):**
```python
# Multiply value by 100 inside the format string — NOT possible in Streamlit.
# Streamlit's format= is a printf string applied to the raw value with no
# transformation. So "%.0f%%" on 0.08 will always render "0%". Approach B
# does not exist — Approach A is the only correct path.
```

**Confirmed correct approach: Approach A for all 5 buggy sliders.** The stored value remains a decimal (divided by 100 after reading), so ALL downstream code (`session_state['income']`, `session_state['sip_params']`, `session_state['advanced']`) continues to receive decimals — no changes elsewhere needed.

**Round-trip safety for session_state restore:** When the user navigates back, the slider default is reconstructed as `int(round(prev_decimal * 100))`. This is safe: `round(0.08 * 100) = 8`, `round(0.06 * 100) = 6`, `round(0.09 * 100) = 9`. No precision loss for the step sizes used.

---

### Fix 2: Donut Hover Shows "Equity 75 75%" (double label + raw value)

**Root cause:** `views.py` L379–384, `_allocation_donut()`. `go.Pie` with `textinfo="label+percent"` controls the *on-chart text*, but the **hover tooltip** is governed by `hovertemplate`/`hoverinfo`. When neither is set, Plotly defaults to showing `{label} {value} {percent}` — so if values are already percentages (e.g. 75), hover reads "Equity 75 75%".

**Exact fix (add `hovertemplate` to the `go.Pie` call, L379–384):**
```python
# views.py L379-388 — BEFORE:
fig = go.Figure(go.Pie(
    labels=labels, values=values, hole=0.6,
    marker=dict(colors=colors, line=dict(color="#0A0A0E", width=2)),
    textinfo="label+percent", textfont=dict(color=_TEXT, size=12),
    sort=False, direction="clockwise",
))

# AFTER — add hovertemplate:
fig = go.Figure(go.Pie(
    labels=labels, values=values, hole=0.6,
    marker=dict(colors=colors, line=dict(color="#0A0A0E", width=2)),
    textinfo="label+percent", textfont=dict(color=_TEXT, size=12),
    sort=False, direction="clockwise",
    hovertemplate="%{label}: %{value:.0f}%<extra></extra>",
))
```

`%{value:.0f}%` renders the stored value (already a percentage integer like 75) with no decimal places, followed by a literal `%`. `<extra></extra>` suppresses the secondary trace name box Plotly appends by default. Result: hover reads "Equity: 75%".

**Same fix must be applied to every call site of `_allocation_donut()`:**
- `views.py` L327: `view_profile()` — the whole-person base mix donut
- `views.py` L676: `_render_goal_card()` — the per-goal allocation donut

Both call the same helper so one fix to `_allocation_donut` propagates to both.

**Also check `_sip_split_bar` (L729–751):** that chart already has `hovertemplate=f"{k.capitalize()}: ₹%{{x:,.0f}}/mo<extra></extra>"` on each bar trace — it is correct and does not need fixing.

---

### Fix 3: Cashflow Chart Y-Axis Shows "₹" + Raw Millions

**Root cause:** `views.py` L894–914, `_cashflow_chart()`. The `yaxis` uses `tickprefix="₹"` (L910), which prepends `₹` to Plotly's default SI-prefix auto-formatting. On large values Plotly auto-scales to `M` (millions), producing tick labels like `₹1.2M` or raw large integers like `₹1200000`. Plotly has **no native lakh/crore formatter** — it only knows SI prefixes (k, M, G).

**The `_lakh_cr()` helper already exists at views.py L83–90** and already generates correct labels like `₹45.0 L` and `₹1.20 Cr`. Goal-card metrics (`_render_goal_card` L663–671) already use it. The cashflow chart does not.

**Exact fix — use `tickvals` + `ticktext` with `_lakh_cr()`:**
```python
def _cashflow_chart(rows):
    """Grouped bars: disposable income vs total SIP outflow per year."""
    import plotly.graph_objects as go
    import numpy as np

    years = [f"Y{r.year_index + 1}" for r in rows]
    disposable = [r.disposable_income for r in rows]
    sip = [r.total_sip_outflow for r in rows]

    # Determine a sensible tick range based on the data max.
    all_vals = [v for v in disposable + sip if v is not None and v > 0]
    max_val = max(all_vals) if all_vals else 1_00_00_000

    # Generate 5-6 evenly-spaced tick positions, label each with _lakh_cr().
    tick_count = 5
    tick_step = max_val / tick_count
    # Round tick_step to a "nice" lakh/crore boundary.
    if tick_step >= 1_00_00_000:
        tick_step = round(tick_step / 1_00_00_000) * 1_00_00_000
    elif tick_step >= 1_00_000:
        tick_step = round(tick_step / 1_00_000) * 1_00_000
    else:
        tick_step = round(tick_step / 10_000) * 10_000
    tick_step = max(tick_step, 1)  # guard against zero

    tickvals = [i * tick_step for i in range(tick_count + 2)]
    ticktext = [_lakh_cr(v) for v in tickvals]

    fig = go.Figure()
    fig.add_trace(go.Bar(x=years, y=disposable, name="Disposable income",
                         marker=dict(color=_ACCENT)))
    fig.add_trace(go.Bar(x=years, y=sip, name="Total SIP outflow",
                         marker=dict(color=_WARNING)))
    fig.update_layout(
        barmode="group",
        xaxis=dict(showgrid=False, tickfont=dict(color=_MUTED, size=10)),
        yaxis=dict(
            showgrid=True, gridcolor="rgba(255,255,255,0.06)",
            tickfont=dict(color=_MUTED, size=10),
            tickvals=tickvals, ticktext=ticktext,  # REPLACES tickprefix="₹"
        ),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, font=dict(color=_MUTED)),
    )
    return _base_layout(fig, height=320)
```

**Remove `tickprefix="₹"` from the yaxis dict** — the `_lakh_cr()` labels already include the `₹` symbol. Keeping both would double-prefix.

**Hover tooltips:** The bar traces inherit Plotly's default hover (`%{y}`) which will still show raw numbers. Fix hover too:
```python
fig.add_trace(go.Bar(
    x=years, y=disposable, name="Disposable income",
    marker=dict(color=_ACCENT),
    hovertemplate="%{x}: %{customdata}<extra>Disposable income</extra>",
    customdata=[_lakh_cr(v) for v in disposable],
))
fig.add_trace(go.Bar(
    x=years, y=sip, name="Total SIP outflow",
    marker=dict(color=_WARNING),
    hovertemplate="%{x}: %{customdata}<extra>Total SIP outflow</extra>",
    customdata=[_lakh_cr(v) for v in sip],
))
```

**`tickformat` alternative considered and rejected:** Plotly's `tickformat` uses d3 format strings, which support `s` (SI suffix) but not lakh/crore. A custom `tickformat` cannot produce `₹45.0 L`. The `tickvals`+`ticktext` approach is the only correct Plotly path for Indian number system axis labels.

---

### Fix 4: "Build my full plan" Button Wraps

**Root cause:** `app.py` L215, `_nav_buttons()`. `st.columns([1, 4, 1])` puts the Next button in a column that is `1/(1+4+1) = 16.7%` of the 860px container width (`max-width: 860px` set in theme.py L77). That is ~143px — barely enough for a short label. "Build my full plan →" is ~170px at `Inter 500 0.6rem/1.4rem padding`, so it wraps.

**This function is shared across all steps** (steps 0–3 call `_nav_buttons`). Changes must not break "← Back" / "Next →" / "See My Plan →" / "← Revise Goals".

**Three viable approaches:**

**Approach A (recommended) — `use_container_width=True` on the Next button only:**
```python
# app.py L223-226 — AFTER:
if next_step is not None:
    with col_next:
        if st.button(
            next_label,
            key=f"next_{st.session_state['step']}",
            type="primary",
            disabled=next_disabled,
            use_container_width=True,   # ADD THIS
        ):
            st.session_state["step"] = next_step
            st.rerun()
```
`use_container_width=True` makes the button fill its column regardless of label length. The column itself is still 1/6 of the container, but the button text will no longer overflow — it stays within its column box and the label renders on one line because the column width is wider than the button's natural size at most zoom levels. **Caveat:** at very small viewport widths (<600px) the column may still be too narrow; see CSS fix below.

**Approach B — Widen the Next column in the ratio tuple:**
```python
# app.py L215 — BEFORE:
col_back, col_spacer, col_next = st.columns([1, 4, 1])

# AFTER — give Next twice the space:
col_back, col_spacer, col_next = st.columns([1, 3, 2])
```
This increases `col_next` from 16.7% to 33% of container width (~284px). "Build my full plan →" is comfortably under 284px. The Back button stays at 16.7% (~143px) which is fine for "← Back" (shorter labels). Risk: if a future `next_label` is even longer, the problem recurs.

**Approach C — CSS `white-space: nowrap` on primary buttons:**

The theme at `theme.py` L111–126 already styles `.stButton > button`. Add `white-space: nowrap !important` there:
```css
/* theme.py _CSS addition inside the primary button block: */
.stButton > button[kind="primary"],
.stButton > button {
  ...existing properties...
  white-space: nowrap !important;
}
```
This prevents wrapping at the text level regardless of column width. Combined with `use_container_width=True` (Approach A) this is belt-and-suspenders. **Caveat:** `nowrap` on a fixed-width column can cause horizontal overflow if the container is very narrow — test at 375px mobile.

**Recommended:** Approach A (`use_container_width=True`) + Approach C (CSS `nowrap`) together. The column ratio stays at `[1, 4, 1]` so you're not hard-coding an arbitrary ratio that may need revisiting.

---

### Fix 5: Explore Weight Sliders Should Auto-Sum to 100

**The three sliders** are at `views.py` L960–966:
```python
ws = st.slider("Sharpe Ratio", 0, 100, ..., 1)
wa = st.slider("Jensen's Alpha", 0, 100, ..., 1)
wc = st.slider("Consistency", 0, 100, ..., 1)
```
Currently the sum `ws + wa + wc` can be anything 0–300; the code normalises to proportions at L974 (`weights = {"sharpe": ws / total_w, ...}`). The UI says "must sum to 100% — we normalise for you" but the sliders don't enforce it.

**The rerun-loop problem:** If you use `on_change` to auto-adjust other sliders, Streamlit immediately triggers another rerun when the adjusted slider's value changes, potentially causing an infinite loop. The "which slider moved" problem: you cannot distinguish which slider the user moved vs. which was auto-adjusted.

**Approach A — Two sliders + computed third (recommended):**
```python
# views.py L956-974 — REPLACEMENT:
saved = st.session_state.get("_explore_weights") if not reset_weights else None

w1, w2, _ = st.columns(3)
with w1:
    ws = st.slider("Sharpe Ratio", 0, 100,
                   int((saved or {}).get("sharpe", 33)), 1,
                   help="Risk-adjusted return — return per unit of volatility.",
                   key="exp_ws")
with w2:
    wa = st.slider("Jensen's Alpha", 0, 100,
                   int((saved or {}).get("alpha", 33)), 1,
                   help="Excess return over what its market risk (beta) would predict.",
                   key="exp_wa")

# Third weight is always the remainder — no slider, no rerun loop.
wc_raw = 100 - ws - wa
wc = max(0, wc_raw)   # clamp: if ws+wa > 100, Consistency gets 0

st.caption(f"Consistency weight: **{wc}%** (remainder after Sharpe + Alpha)")

st.session_state["_explore_weights"] = {"sharpe": ws, "alpha": wa, "consistency": wc}
```
This eliminates the rerun loop entirely. The user controls two sliders; the third is always `100 - ws - wa`, shown as a read-only caption. If ws + wa > 100, consistency is 0 (clamp). The normalization at L974 becomes mathematically unnecessary but can stay as a safety net.

**Approach B — Three sliders with on_change callbacks (works, but has pitfalls):**
```python
# session_state pattern — requires careful key discipline:

def _init_weights():
    if "_w_sharpe" not in st.session_state:
        st.session_state["_w_sharpe"] = 33
        st.session_state["_w_alpha"] = 33
        st.session_state["_w_consistency"] = 34

def _on_sharpe_change():
    remainder = 100 - st.session_state["_w_sharpe"]
    # Split remainder evenly (or proportionally) between alpha and consistency.
    half = remainder // 2
    st.session_state["_w_alpha"] = half
    st.session_state["_w_consistency"] = remainder - half

def _on_alpha_change():
    remainder = 100 - st.session_state["_w_alpha"]
    half = remainder // 2
    st.session_state["_w_sharpe"] = half
    st.session_state["_w_consistency"] = remainder - half

# ... analogous for consistency.

_init_weights()
ws = st.slider("Sharpe", 0, 100, key="_w_sharpe", on_change=_on_sharpe_change)
wa = st.slider("Alpha", 0, 100, key="_w_alpha", on_change=_on_alpha_change)
wc = st.slider("Consistency", 0, 100, key="_w_consistency", on_change=_on_consistency_change)
```

**Pitfalls with Approach B:**
1. **The "which slider moved" problem IS solved** because each slider has its own `on_change` callback — Streamlit only calls the callback for the widget whose value actually changed.
2. **Rerun loop risk:** `on_change` callbacks run BEFORE the script reruns. Writing to other session_state keys inside the callback does NOT trigger additional callbacks — it just sets values that the next rerun will pick up as the slider defaults. So there is NO loop. This is safe.
3. **UX friction:** Moving any slider causes the other two to jump, which can be disorienting if the user wants fine control over all three independently. The re-normalization is aggressive.
4. **Edge case:** if the user drags Sharpe to 100, alpha and consistency both snap to 0 — this is correct but jarring.

**Verdict:** Approach A (two sliders + computed third) is cleaner, has zero loop risk, and is less surprising to users. The current code already has the normalization (`ws / total_w`) so any combination still works — the auto-sum is just cosmetic UX improvement. Unless the UX critic specifically requires all three to be interactive, **Approach A is the right call**.

---

### Fix 6: Diagnosis Zero-State — Suppress Shortfall on First Load

**Current behavior:** `views.py` L224–226 — the shortfall reveal runs whenever `valid` is True:
```python
if valid:
    required, blended, asset_split = _required_sip_preliminary(...)
    _render_shortfall_reveal(...)
```
On first load, `existing = st.session_state["goals"][0]` is empty (the list is `[]`), so `existing` is `None`, and the fields default to the preset values (Retirement, ₹1 Cr, 25 years). The slider defaults `current_sip = 0`. The condition `valid = amount > 0 and years > 0 and bool(goal_name.strip())` is immediately True with defaults. So the shortfall IS computed and shown on first load — before the user has entered anything.

**Gate mechanism — session_state flag + explicit trigger:**
```python
# views.py, inside view_diagnosis(), after the current_sip input:

# Gate: only reveal after user has either (a) changed a value, or
# (b) explicitly clicked "Check my SIP".
if "diagnosis_revealed" not in st.session_state:
    st.session_state["diagnosis_revealed"] = False

# Optional: auto-reveal when user edits any of the three fields.
# Since Streamlit reruns on any widget change, we can set the flag
# when values differ from the preset defaults:
_defaults = _GOAL_PRESETS[preset]
user_has_edited = (
    amount != _defaults["amount"]
    or years != _defaults["years"]
    or current_sip != 0  # any non-zero SIP counts as a real entry
)

if not st.session_state["diagnosis_revealed"] and not user_has_edited:
    st.info("Enter your goal details above to see your preliminary check.")
elif valid:
    st.session_state["diagnosis_revealed"] = True
    required, blended, asset_split = _required_sip_preliminary(float(amount), float(years))
    _render_shortfall_reveal(goal_name, float(current_sip), required, blended, asset_split, float(years))
```

**Alternative — explicit "Check my SIP" button:**
```python
if valid:
    if st.button("Check my SIP against this goal", type="primary", key="diag_check"):
        st.session_state["diagnosis_revealed"] = True
    if st.session_state.get("diagnosis_revealed"):
        required, blended, asset_split = _required_sip_preliminary(...)
        _render_shortfall_reveal(...)
```

**Recommendation:** The auto-reveal on edit is better UX than a separate button (one fewer click, feels more live/interactive). The `user_has_edited` check prevents the confusing "you're 100% short" message from appearing before the user has touched anything.

**Important nuance:** When the user navigates back from step 1+ to step 0, `st.session_state["diagnosis_revealed"]` will still be `True`, so the reveal re-appears with their previously entered values — correct behavior.

**Reset needed:** If the user changes the preset chip (`preset` radio), the defaults change. The `diagnosis_revealed` flag should reset when the preset changes:
```python
if st.session_state.get("_last_preset") != preset:
    st.session_state["diagnosis_revealed"] = False
    st.session_state["_last_preset"] = preset
```

---

## 3. Complete Buggy Slider Inventory

All sliders in `dashboard/views.py`:

| File:Line | Label | Range | Step | Format | Bug? |
|---|---|---|---|---|---|
| views.py:434 | "Expected annual salary hike" | 0.0–0.20 | 0.01 | `"%.0f%%"` | **YES** — shows "0%" |
| views.py:438 | "Lifestyle (expense) inflation" | 0.0–0.15 | 0.01 | `"%.0f%%"` | **YES** — shows "0%" |
| views.py:447 | "Goal cost inflation" | 0.0–0.15 | 0.01 | `"%.0f%%"` | **YES** — shows "0%" |
| views.py:453 | "Annual SIP step-up" | 0.0–0.20 | 0.01 | `"%.0f%%"` | **YES** — shows "0%" |
| views.py:797 | "Loan interest" | 0.0–0.20 | 0.005 | `"%.1f%%"` | **YES** — shows "0.1%" at 0.09 |
| views.py:960 | "Sharpe Ratio" | 0–100 | 1 | (none) | No bug |
| views.py:963 | "Jensen's Alpha" | 0–100 | 1 | (none) | No bug |
| views.py:966 | "Consistency" | 0–100 | 1 | (none) | No bug |

**5 buggy sliders total, all in `views.py`.** No sliders in `app.py` or any `shared/` module.

---

## 4. Motion Feasibility Table

The full-rerun model is the key constraint: Streamlit executes the entire script top-to-bottom on every widget interaction. **CSS `transition` and `:hover` effects defined in `<style>` tags persist across reruns** (the injected CSS lives in the browser DOM, not the Python script). However, **`@keyframes` animations reset on rerun** because the element is recreated in the DOM, replaying the animation from the start — this produces a flash/jank visible on every slider move.

| Motion Effect | Classification | Implementation Mechanism | Notes |
|---|---|---|---|
| Button hover lift (`translateY(-1px)`) | **GREEN** | Already in `theme.py` L121–126. CSS `:hover` + `transition`. Does not replay on rerun. | Works now; keep as-is. |
| Button hover color shift | **GREEN** | Already in `theme.py` L120–138. CSS `:hover` + `transition: background 150ms`. | Works now; keep as-is. |
| Step bar color transition (active/done) | **GREEN** | Already in `theme.py` L254 `transition: background 300ms ease`. Applies when class changes — but only fires on step change, not on every widget rerun within a step. | Works correctly by accident (step changes are rare vs. widget reruns). |
| Input focus glow | **GREEN** | Already in `theme.py` L105–109 `box-shadow` on focus. Pure CSS, no rerun involvement. | Works now. |
| Expander open/close animation | **GREEN** | Streamlit's native expander has a built-in fold animation (no CSS needed from us). | Do not override with custom CSS — it will conflict. |
| Card hover highlight (metric / goal card) | **GREEN** | Add to `theme.py`: `[data-testid="stMetric"]:hover { border-color: var(--accent); transition: border-color 150ms; }`. For goal cards: `div[data-testid="stVerticalBlock"] > div[data-testid="stVerticalBlock"]:hover { border-color: var(--accent); }`. | CSS-only hover, no rerun. |
| Entrance animation (fade-in on page load / step change) | **YELLOW** | `@keyframes fadeIn` in `theme.py` applied to `.main .block-container`. **Replays on every rerun** (flash). Mitigation: use very short duration (≤100ms) so the flash is imperceptible. Alternatively, apply only to specific elements that don't change on widget interaction (e.g., the title `h1`). Do NOT apply to the whole page or interactive areas. | Short enough duration (80–100ms) is tolerable. |
| Metric value count-up animation | **YELLOW** | CSS `@keyframes` counter trick does not work in Streamlit (values are rendered as static text nodes, not `counter()`-compatible). Could use a CSS `@keyframes` on the container `opacity` + `transform` — achieves a "pop in" effect on rerun. Problem: replays on every widget interaction including sliders. At 150ms it's barely perceptible but present. | Not recommended for interactive steps (2 & 3). Only safe on the Results screen where there are no persistent sliders after plan builds. |
| Skeleton loader (content loading state) | **YELLOW** | See dedicated section below. |  |
| Donut chart entrance spin/draw animation | **RED** | Plotly chart animations set via `fig.update_layout(transition={"duration": 500})` — this works in standard Plotly but in Streamlit the chart is re-rendered from scratch on rerun, so the animation fires every time any widget changes. On the profile screen with 5 radio buttons, the donut re-animates on every quiz answer. Highly distracting. | Skip. Use static `config={"displayModeBar": False}` only. |
| Cashflow bar chart animated grow-in | **RED** | Same reason as above. Plotly `transition` in Streamlit = replay on every widget interaction. | Skip. |
| Step-to-step slide transition | **RED** | Would require a custom Streamlit component (iframe-based with its own DOM lifecycle). Not achievable with CSS alone because the entire DOM is replaced on step change (`st.rerun()`). | Not worth building for a portfolio app. |
| Ripple effect on button click | **RED** | Requires JavaScript event listeners. Streamlit's `st.markdown(..., unsafe_allow_html=True)` can inject `<script>` tags, but Streamlit sandboxes most JS execution — `<script>` in markdown is stripped/ignored in modern Streamlit versions (≥1.28+). Would require a custom component. | Skip. |
| Glassmorphism card hover glow (box-shadow) | **GREEN** | Add to `theme.py`: `div[data-testid="stVerticalBlock"] > div[data-testid="stVerticalBlock"] { transition: box-shadow 200ms ease; } div[data-testid="stVerticalBlock"] > div[data-testid="stVerticalBlock"]:hover { box-shadow: 0 0 0 1px var(--accent-glow), 0 8px 32px rgba(129,140,248,0.12); }` | Pure CSS hover — no rerun involvement. |
| Slider thumb accent color | **GREEN** | Already in `theme.py` L152–154. CSS selector `[data-testid="stSlider"] > div > div > div > div`. | Works now. |

### Skeleton Loaders — Detailed Assessment

**Does Streamlit's native skeleton suffice?** Partially. When a Streamlit script is running (between `st.rerun()` and completion), Streamlit shows a built-in "running" indicator (spinner in the top-right corner + a thin red progress bar at the top in some versions, or a spinner overlay on widgets). This is **not** a skeleton screen — it does not show placeholder content shapes.

**The two `st.spinner()` calls in `views.py`** (L580: "Sizing each goal's SIP…" and L622: "Writing the plain-language explanation…") do render a spinner inside the content area, which is a reasonable loading indicator for the 2–3 second operations they gate.

**Building a CSS shimmer skeleton via `st.empty()`:**
```python
# Pattern: pre-render a placeholder, then replace with real content.
placeholder = st.empty()
placeholder.markdown("""
<div class="skeleton-card">
  <div class="skeleton-line w-60"></div>
  <div class="skeleton-line w-40"></div>
</div>
""", unsafe_allow_html=True)

# ... do the computation ...
plan = build_plan(...)

placeholder.empty()   # clear the skeleton
# render actual content
```
Then in `theme.py`, add:
```css
@keyframes shimmer {
  0%   { background-position: -200% 0; }
  100% { background-position:  200% 0; }
}
.skeleton-line {
  height: 16px;
  border-radius: 4px;
  background: linear-gradient(90deg,
    var(--border) 25%, var(--surface) 50%, var(--border) 75%);
  background-size: 200% 100%;
  animation: shimmer 1.5s infinite;
  margin: 8px 0;
}
.skeleton-card { padding: 1.5rem; }
.w-60 { width: 60%; }
.w-40 { width: 40%; }
```

**Verdict:** The shimmer skeleton is buildable and safe — `st.empty()` is a stable Streamlit API. The `@keyframes shimmer` animation does NOT replay on rerun because it runs inside the `placeholder` element during the computation phase, which is replaced (not re-rendered) once `placeholder.empty()` is called. This makes it **GREEN for the specific loading window** of `build_plan()` and `explain_plan()` calls only. It is not appropriate as a general page skeleton.

---

## 5. Q3 (Buildable Motion) and Q4 (Auto-Sum Sliders) — My Lane

### Q3: Motion Subset That Is Actually Buildable

**Build these — safe and additive:**
1. Card hover glow (`box-shadow` transition) — pure CSS, add 4 lines to `theme.py`
2. Metric card hover border highlight — pure CSS, add 3 lines to `theme.py`
3. CSS shimmer skeleton for `build_plan()` + `explain_plan()` calls — `st.empty()` pattern, safe
4. Button `:hover` effects already in place — keep, no changes needed

**Skip these — fight Streamlit or need custom components:**
1. Plotly chart entrance animations — replay on every widget rerun, very distracting
2. Step-to-step slide transitions — requires full custom component
3. Metric count-up animation — CSS counter trick doesn't work on Streamlit text nodes
4. Button ripple — requires JS, stripped by Streamlit

**Accept with caution (very short duration only):**
1. Page-level fade-in on step change — only if ≤100ms, only applied to non-interactive elements (h1, step bar), never to the full `.block-container`

### Q4: Auto-Sum Sliders Mechanism

As detailed in Fix 5 above: **Approach A (two sliders + computed third) is the correct implementation.** It eliminates rerun loop risk entirely and produces clearer UX. The `on_change` callback approach (Approach B) technically works in Streamlit ≥1.0 without loops (callbacks run before the next script rerun, not recursively), but it produces jarring slider jump behavior when any weight is changed.

The current normalization at `views.py` L974 (`ws / total_w`) is actually a reasonable compromise that already solves the mathematical problem. The UI label "we normalise for you" is accurate. The only remaining UX issue is that the three sliders can sum to wildly different totals (e.g. 3 vs 300), giving no clear feedback. Two-slider + computed-third solves this cleanly.

---

## 6. What the Others Might Get Wrong

**The UX critic may propose:**

1. **"Add a step transition animation"** — not doable in Streamlit without a custom component. A full-page CSS animation would replay on every slider interaction within a step, not just on step changes. The step change itself calls `st.rerun()` which destroys and rebuilds the DOM — CSS transitions on the container have nothing to transition from/to. The UX critic should be told: page-level transitions are RED; accept the instant repaint and focus on within-step micro-interactions instead.

2. **"Use Streamlit's `st.fragment` for partial reruns on the explore screen"** — `st.fragment` requires streamlit>=1.37. The requirement pins `>=1.35`. On Streamlit Cloud the exact deployed version depends on when the app was last deployed and what Streamlit Cloud's default is. Do not rely on `st.fragment` unless the requirement is bumped to `>=1.37` and tested.

3. **"Show a skeleton loader while the risk quiz scores"** — the quiz scores synchronously (no API call, pure Python arithmetic). `compute_risk_score()` takes <1ms. There is no perceptible loading window to fill with a skeleton. A skeleton here would flash for a single frame and disappear, which is worse than nothing.

4. **"Animate the donut chart when the risk profile completes"** — see RED classification above. Plotly chart transitions replay on every radio button click in the quiz. The quiz has 5 radio buttons; the user changes them interactively. Every click re-animates the donut. Do not add Plotly transitions to charts on interactive screens.

5. **"The goal-card metric values should animate in when the Results page loads"** — the Results page runs `build_plan()` synchronously inside `st.spinner()`. Once the spinner clears, all metrics appear together. A CSS entrance animation on `[data-testid="stMetricValue"]` would work (GREEN) only if it's a simple `opacity` + `translateY` with very short duration (≤150ms). At longer durations it becomes distracting on the Results screen where users will re-enter to see updated metrics after using the Back button.

6. **"Make the shortfall percentage animate/count up"** — not achievable without a custom JS component. The percentage is rendered as a string inside `st.metric()`, which Streamlit manages as a React text node. CSS `@keyframes counter()` only works with CSS `counter()` values, not arbitrary text.

7. **"The cashflow chart bar width should be narrower for aesthetics"** — Plotly bar width in Streamlit is controlled by `bargap` and `bargroupgap` in `fig.update_layout()`. This is fine. But if the UX critic proposes a width that collapses bars to invisible on a 25-year horizon, push back: readability matters more than aesthetics at 25+ year labels.

---

*Analysis complete. No code was modified — all fixes documented as exact proposed replacements for the build pass.*
