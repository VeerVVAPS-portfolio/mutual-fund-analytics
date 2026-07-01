"""
shared/planning_engine.py — TrueSIP's reconciliation / composition engine.

This is the finance logic that only exists BECAUSE Profile + Pick + Size are
merged into one flow. It is where the council's three BUILD MANDATES live and
is the single source of every per-goal SIP, asset split, and equity-category
hand-off the UI renders.

╔══════════════════════════════════════════════════════════════════════════╗
║ WHAT THIS MODULE OWNS (and why it can't live in the three originals)      ║
╠══════════════════════════════════════════════════════════════════════════╣
║ Project 6 (Size) solves a SIP but uses a FLAT return (12%) for every      ║
║ goal regardless of horizon. Project 2 (Profile) makes ONE whole-person    ║
║ asset mix. Project 1 (Pick) ranks equity funds. None of them reconcile    ║
║ "a 2-year goal must be debt-heavy, so its SIP must assume a LOWER return  ║
║ than a 20-year equity-heavy goal." That reconciliation is THIS file's     ║
║ entire reason to exist. The financially-honest fix is step 3 below:       ║
║ each goal's expected return is BLENDED from its own horizon-banded asset  ║
║ split — not a flat 12% for all.                                           ║
╚══════════════════════════════════════════════════════════════════════════╝

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
THE RECONCILIATION PIPELINE (per goal)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  1. HORIZON sets the equity band   →  horizon_band(years)
        <3y 0–10% · 3–7y 20–40% · 7–15y 50–70% · >15y 70–85%
     RISK LABEL is a tilt within the band + a top cap (panic-prone /
     Conservative & Moderate-Conservative capped at band midpoint).
        →  reconcile_allocation(years, risk_label)   [delegates to
           risk_profiler.horizon_equity_band, then derives debt/gold]
  2. ASSET SPLIT (equity / debt / gold %) is derived from equity_pct
     (remainder split debt-heavy with a small gold sleeve).
  3. BLENDED expected annual return is computed from the asset split
        →  blended_expected_return(asset_split)
     (equity 12% · debt 7% · gold 6% — documented assumptions below).
     THIS is the honest fix: a near-term debt-heavy goal gets a lower
     return assumption than a long equity-heavy goal.
  4. SIP is SOLVED deterministically with that blended return
        →  goal_calculator.solve_goal(...)   (THE ONLY source of any SIP)
  5. The SIP is SPLIT across asset classes in rupees
        →  split_sip_by_asset(monthly_sip, asset_split)   (must sum to SIP)
  6. The goal's equity slice is mapped to a fund CATEGORY STRING only
        →  equity_category_for(goal)   (NEVER a named fund — see Mandate #4)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
RETURN ASSUMPTIONS (documented, conservative planning estimates — NOT forecasts)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  equity 12.0%  — matches Project 6's conservative default. The source Excel
                  assumed 16–17%; 12% is the deliberately conservative figure
                  Veer's P6 rebuild adopted for long-horizon SIP planning.
  debt    7.0%  — typical short/medium-duration debt / PPF-band assumption.
  gold    6.0%  — long-run INR gold appreciation planning assumption.
  alts    —     — TrueSIP folds the whole-person "alternatives" sleeve into
                  gold at the per-goal level (no investable alt product is
                  surfaced; keeping a phantom alt slice would be dishonest).
These live in RETURN_ASSUMPTIONS and are exposed for the UI/LLM to disclose.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
PLAN DICT SCHEMA  (returned by build_plan — matches app.py render_step_results)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
build_plan(goals, risk_label, income, sip_params, df) -> dict:
  {
    'goals': list[dict],            # one entry per input goal (see PER-GOAL below)
    'total_monthly_sip': float,     # Σ monthly_sip across goals (₹/month, Year 1)
    'affordability_ok':  bool,      # True if NO projected year is a shortfall
    'cashflow_rows':     list[ProjectionYear],  # from cashflow_projection (may be [])
    'return_assumptions': dict,     # RETURN_ASSUMPTIONS (for UI/LLM disclosure)
    'risk_label':        str,       # echoed person-level label (tilt context)
  }

  PER-GOAL entry (an element of plan['goals']):
  {
    # ── identity / inputs ──
    'name':            str,
    'amount':          float,       # today's cost (₹)
    'years':           float,       # horizon
    'importance':      str,         # "Essential"|"Important"|"Aspirational"
                                    #   (default "Important"); moves ONLY the
                                    #   equity_category — never the SIP/%/split.

    # ── GoalResult (deterministic SIZE output — flattened for the UI) ──
    'result':          GoalResult,  # full dataclass (schedule, totals, etc.)
    'future_value_required': float, # ₹ inflation-adjusted target at goal date
    'monthly_sip':     float,       # ₹/month Year-1 SIP  ← PERSONALIZED, DETERMINISTIC
    'total_invested':  float,
    'wealth_gained':   float,

    # ── allocation (horizon-banded, risk-tilted) ──
    'equity_pct':      float,       # 0–100, GUARANTEED within horizon band  ← PERSONALIZED
    'asset_split':     dict,        # {'equity','debt','gold'} %, sums to 100  ← PERSONALIZED
    'band':            dict,        # {'band_low','band_high','tilt'} (provenance)
    'blended_return':  float,       # decimal annual return used to solve the SIP

    # ── SIP split in rupees (Σ == monthly_sip) ──
    'sip_split':       dict,        # {'equity','debt','gold'} ₹/month        ← PERSONALIZED

    # ── fund hand-off (CATEGORY STRING ONLY — Mandate #4) ──
    'equity_category': str | None,  # e.g. "Equity Scheme - Large Cap Fund"
                                    #   None when equity slice is ~0 (near-term goal)
    'non_equity_notes': list[dict], # named-but-UNRANKED debt/gold instruments
                                    #   each {'sleeve','instrument','note'} — NO score
  }

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
COMPLIANCE — which fields are "PERSONALIZED" (council Mandate #4 / acceptance test)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
HARD ACCEPTANCE CRITERION: no function here returns, and no screen may render,
a PERSONALIZED output + a SPECIFIC NAMED SECURITY + an amount/buy-directive
together on one surface.

  Fields tagged ← PERSONALIZED above (monthly_sip, equity_pct, asset_split,
  sip_split) are tied to the individual's quiz/income inputs. They may appear
  next to an ASSET-CLASS or a CATEGORY STRING, but MUST NOT appear next to a
  named fund scheme. This module therefore:
    • NEVER imports or calls data_store.get_top_funds.
    • NEVER embeds a scheme_name / AMC / any named security.
    • Emits only `equity_category` (a string) for the DECOUPLED "Explore Funds"
      screener to consume on a separate, opt-in, neutral-weighted surface.
  `non_equity_notes` names generic instrument *types* (SGB, PPF, short-duration
  debt) which are product categories, not specific securities, and carry NO
  ranking / Sharpe / Alpha (those are computed vs NIFTY 50 and are meaningless
  off-equity — Mandate #3).

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
COUNCIL MANDATES ENFORCED HERE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  #1 Deterministic SIP only      → every monthly_sip comes from solve_goal().
  #2 Horizon-authoritative alloc → equity_pct from horizon_equity_band();
                                    risk_label is a tilt+cap, never an override.
  #3 Honest equity-only gap      → only equity rupees carry a category; debt/gold
                                    named but explicitly unranked.
  #4 Two-mode compliance split   → no named fund anywhere in this module's output.

Run `python shared/planning_engine.py` for the self-check / regression anchor.
"""

from __future__ import annotations

from typing import Optional

# When imported as part of the app (dashboard/app.py puts the project root on
# sys.path), `shared.*` resolves normally. When this file is run DIRECTLY for
# its self-check (`python shared/planning_engine.py`), the project root isn't
# on sys.path yet — bootstrap it so the package imports below still work.
if __package__ in (None, ""):
    import sys as _sys
    from pathlib import Path as _Path
    _ROOT = _Path(__file__).resolve().parent.parent
    if str(_ROOT) not in _sys.path:
        _sys.path.insert(0, str(_ROOT))

# Engine is import-safe outside Streamlit: only pure-Python deps at module load.
from shared.goal_calculator import GoalResult, solve_goal
from shared.risk_profiler import horizon_equity_band
from shared.cashflow_projection import ProjectionYear, project_cashflow


# ══════════════════════════════════════════════════════════════════════════
# DOCUMENTED ASSUMPTIONS
# ══════════════════════════════════════════════════════════════════════════

# Per-asset-class expected ANNUAL return (decimal). Conservative planning
# estimates, NOT forecasts. Exposed in the plan dict for UI/LLM disclosure.
#
# P0 GUARDRAIL (Finance Q2c, Mandate #4-adjacent): Category selection affects
# only WHICH funds to browse — never the return assumption or the SIP. Equity
# stays 0.12 regardless of the cap a goal maps to (Large/Mid/Small). Coupling a
# riskier cap to a higher return would shrink the SIP on the riskier sleeve
# (honesty-backwards) and would break self-check [B] (r_near < r_far).
RETURN_ASSUMPTIONS: dict[str, float] = {
    "equity": 0.12,   # matches Project 6's conservative default (Excel used 16–17%)
    "debt":   0.07,   # short/medium-duration debt / PPF band
    "gold":   0.06,   # long-run INR gold appreciation
}

# Floor below which an equity slice is too small to bother routing to the
# screener (a sub-5% sleeve isn't a meaningful fund allocation). Such goals
# get equity_category = None and are funded debt/gold-first.
_EQUITY_ROUTING_FLOOR_PCT: float = 5.0


# ══════════════════════════════════════════════════════════════════════════
# 1. HORIZON BAND  (thin wrapper — band provenance without a risk tilt)
# ══════════════════════════════════════════════════════════════════════════

def horizon_band(years: float) -> tuple[float, float]:
    """
    Return the (min_equity_pct, max_equity_pct) band a goal's HORIZON places it in.

    Bands (council Build Mandate #2):
        <3y   →   0–10%
        3–7y  →  20–40%
        7–15y →  50–70%
        >15y  →  70–85%

    Implemented by asking risk_profiler.horizon_equity_band for a neutral
    (tilt-agnostic) read so the band tables live in ONE place. The risk label
    passed here ("__band_probe__") is unknown to _LABEL_TILT and falls back to
    its 0.5 default, but we ignore the tilted value and return only band_low /
    band_high — so this stays a pure horizon→band function.
    """
    probe = horizon_equity_band(years, "__band_probe__")
    return (probe["band_low"], probe["band_high"])


# ══════════════════════════════════════════════════════════════════════════
# 2. RECONCILE ALLOCATION  (horizon band + risk tilt/cap → equity/debt/gold)
# ══════════════════════════════════════════════════════════════════════════

def reconcile_allocation(years: float, risk_label: str) -> dict:
    """
    The core reconciliation rule (council Build Mandate #2).

    Step A — the goal's HORIZON sets the equity band.
    Step B — the person's RISK LABEL is a tilt WITHIN that band, with a top cap:
             panic-prone labels (Conservative / Moderate Conservative) are
             capped at the band midpoint. This is OWNED by
             risk_profiler.horizon_equity_band (_LABEL_TILT puts Conservative
             at tilt 0.0 and Moderate Conservative at the 0.5 midpoint cap).
    Step C — the equity remainder is split into debt + gold (debt-heavy, with a
             small gold sleeve) to form a full per-goal asset split.

    Returns:
        {
          'equity': float,   # % (within the horizon band, by construction)
          'debt':   float,   # %
          'gold':   float,   # %
          'band_low':  float,
          'band_high': float,
          'tilt':      float,  # 0–1 tilt actually applied
        }
        equity + debt + gold == 100.0 (within float tolerance).

    NOTE: equity is GUARANTEED in [band_low, band_high]. build_plan asserts this.
    """
    band = horizon_equity_band(years, risk_label)
    equity = float(band["equity_pct"])

    # Defensive clamp: equity must never leave its horizon band even if an
    # unknown risk_label slipped a tilt outside [0,1]. (horizon_equity_band
    # already keeps it in-band for known labels; this guards the unknown case.)
    equity = max(band["band_low"], min(band["band_high"], equity))

    asset_split = _derive_asset_split(equity)
    return {
        **asset_split,                 # equity / debt / gold (sums to 100)
        "band_low":  band["band_low"],
        "band_high": band["band_high"],
        "tilt":      band["tilt"],
    }


def _derive_asset_split(equity_pct: float) -> dict:
    """
    Split the non-equity remainder into a debt-heavy mix with a small gold sleeve.

    Policy (documented):
      - Gold sleeve = 25% of the non-equity remainder, capped at 15 percentage
        points (gold is a diversifier, never the bulk of a goal).
      - Debt takes the rest of the remainder (it is the stability anchor,
        especially for near-term goals where equity_pct is low).
    Rounded to 1 dp, with debt absorbing any rounding residue so the three
    always sum to exactly 100.0.

    Examples:
      equity  5% → remainder 95 → gold 15.0 (capped), debt 80.0
      equity 30% → remainder 70 → gold 15.0 (capped), debt 55.0
      equity 60% → remainder 40 → gold 10.0,           debt 30.0
      equity 85% → remainder 15 → gold  3.75→3.8,       debt 11.2
    """
    equity_pct = round(float(equity_pct), 1)
    remainder = 100.0 - equity_pct

    gold = min(remainder * 0.25, 15.0)
    gold = round(gold, 1)
    debt = round(remainder - gold, 1)

    # Absorb any 0.1 rounding residue into debt so the split sums to 100.0.
    drift = round(100.0 - (equity_pct + debt + gold), 1)
    debt = round(debt + drift, 1)

    return {"equity": equity_pct, "debt": debt, "gold": gold}


# ══════════════════════════════════════════════════════════════════════════
# 3. BLENDED EXPECTED RETURN  (the honest per-goal return — not a flat 12%)
# ══════════════════════════════════════════════════════════════════════════

def blended_expected_return(asset_split: dict) -> float:
    """
    Weight RETURN_ASSUMPTIONS by a goal's asset_split to get its blended annual
    return (decimal). THIS is the financially-honest fix the merged product adds:

        near-term, debt-heavy goal  → lower blended return  → larger required SIP
        long-term, equity-heavy goal → higher blended return → smaller required SIP

    Project 6 used a flat 12% for every goal; TrueSIP derives each goal's return
    from its own (horizon-banded) mix.

    Args:
        asset_split: {'equity','debt','gold'} in PERCENT (need not be exactly
                     100; weights are normalised defensively).

    Returns:
        Blended expected annual return as a decimal (e.g. 0.0945).
    """
    eq = float(asset_split.get("equity", 0.0))
    db = float(asset_split.get("debt", 0.0))
    gd = float(asset_split.get("gold", 0.0))
    total = eq + db + gd
    if total <= 0:
        # Degenerate input — fall back to the debt assumption (most conservative
        # sensible floor) rather than 0% which would explode the SIP.
        return RETURN_ASSUMPTIONS["debt"]

    blended = (
        eq * RETURN_ASSUMPTIONS["equity"]
        + db * RETURN_ASSUMPTIONS["debt"]
        + gd * RETURN_ASSUMPTIONS["gold"]
    ) / total
    return round(blended, 4)


# ══════════════════════════════════════════════════════════════════════════
# 5. SPLIT SIP BY ASSET  (rupees — must sum to the SIP)
# ══════════════════════════════════════════════════════════════════════════

def split_sip_by_asset(monthly_sip: float, asset_split: dict) -> dict:
    """
    Split a goal's monthly SIP (₹) across asset classes by its asset_split (%).

    The equity/debt slices are rounded to the rupee; GOLD absorbs the rounding
    residue so the three slices sum EXACTLY to monthly_sip (build_plan asserts
    this). Gold is chosen as the residue-bearer because it is the smallest /
    least structurally-significant sleeve.

    Args:
        monthly_sip: total Year-1 SIP for the goal (₹/month).
        asset_split: {'equity','debt','gold'} in PERCENT (sums to ~100).

    Returns:
        {'equity','debt','gold'} in ₹/month; equity+debt+gold == monthly_sip.
    """
    eq_pct = float(asset_split.get("equity", 0.0)) / 100.0
    db_pct = float(asset_split.get("debt", 0.0)) / 100.0

    equity_rs = round(monthly_sip * eq_pct, 2)
    debt_rs = round(monthly_sip * db_pct, 2)
    gold_rs = round(monthly_sip - equity_rs - debt_rs, 2)  # residue → exact sum

    return {"equity": equity_rs, "debt": debt_rs, "gold": gold_rs}


# ══════════════════════════════════════════════════════════════════════════
# 6. EQUITY CATEGORY FOR  (category STRING only — never a named fund)
# ══════════════════════════════════════════════════════════════════════════

# Map a goal's horizon (× importance) to an equity fund CATEGORY (string) for
# the screener hand-off. Longer horizons tolerate higher-volatility caps;
# near-term equity (the thin sleeve of a 3–7y goal) stays in the most stable
# large-cap space. Values are exact strings from data_store.CATEGORIES (seed).
#
# ── P0 GUARDRAIL (Finance Q2c, Mandate #4-adjacent) ────────────────────────
# Category selection affects only WHICH funds to browse — never the return
# assumption or the SIP. Do NOT let the cap chosen here feed back into
# RETURN_ASSUMPTIONS or blended_expected_return: a riskier cap must never
# shrink the required SIP (that would be honesty-backwards and would break
# self-check [B], which asserts r_near < r_far off a single equity constant).
LARGE_CAP = "Equity Scheme - Large Cap Fund"
LARGE_AND_MID_CAP = "Equity Scheme - Large & Mid Cap Fund"
FLEXI_CAP = "Equity Scheme - Flexi Cap Fund"
MID_CAP = "Equity Scheme - Mid Cap Fund"
SMALL_CAP = "Equity Scheme - Small Cap Fund"

# ── The 6-band × 3-importance equity-category ladder (Finance §2) ───────────
# Each row: (years_min, years_max, (Essential, Important, Aspirational)) and the
# lookup is HALF-OPEN [years_min, years_max) — a value at a boundary belongs to
# the band it OPENS (so exactly 7y → the 7–12y band, exactly 20y → the 15–20y
# band). The category COLUMNS reproduce the Finance critic's hand-justified
# table verbatim; the ±1 "importance notch" is BAKED INTO those columns, NOT a
# uniform programmatic shift. That is why two rows look irregular and MUST stay
# so:
#   • 12–15y Aspirational stays Flexi (does NOT jump to Mid Cap).
#   • 15–20y Essential   stays Flexi (does NOT drop to Large & Mid).
# SMALL-CAP GATE: Small Cap is reachable ONLY at years > 20 AND Aspirational.
# The critic's gate is a STRICT ">20y" ("won't be touched for two decades"), so
# the top band opens at 20-EXCLUSIVE: its years_min is set just above 20 so an
# exactly-20y goal stays in the 15–20y band (Flexi/Flexi/Mid) and never lands in
# Small Cap. This keeps self-check [H]'s "no goal with years ≤ 20 → Small Cap"
# green. (A 20.x-year goal rounding into 15–20y is the conservative direction —
# it keeps borderline goals OUT of the riskiest cap.) None means the equity
# sleeve is too thin to route (<3y goals are debt/gold-first).
_SMALL_CAP_GATE_YEARS: float = 20.0  # Small Cap only for horizons STRICTLY beyond this
_CATEGORY_LADDER: list[tuple[float, float, tuple]] = [
    # (years_min,                      years_max, (essential,         important,          aspirational))
    (0,                                3,   (None,              None,              None)),
    (3,                                7,   (LARGE_CAP,         LARGE_CAP,         LARGE_AND_MID_CAP)),
    (7,                                12,  (LARGE_CAP,         LARGE_AND_MID_CAP, FLEXI_CAP)),
    (12,                               15,  (LARGE_AND_MID_CAP, FLEXI_CAP,         FLEXI_CAP)),
    (15,                               _SMALL_CAP_GATE_YEARS + 1e-9,
                                            (FLEXI_CAP,         FLEXI_CAP,         MID_CAP)),
    (_SMALL_CAP_GATE_YEARS + 1e-9,     999, (FLEXI_CAP,         MID_CAP,           SMALL_CAP)),
]
_IMPORTANCE_COL: dict[str, int] = {"Essential": 0, "Important": 1, "Aspirational": 2}


def equity_category_for(goal: dict) -> Optional[str]:
    """
    Map a goal to an equity fund CATEGORY STRING for the decoupled screener.

    COMPLIANCE (Mandate #4): returns a CATEGORY string ONLY — never a named
    fund, never a "#1 for you". The "Explore Funds" screen takes this string
    and ranks within it on a neutral, opt-in surface; this module never pairs
    the personalized SIP with a named security.

    P0 GUARDRAIL (Finance Q2c): category selection affects only WHICH funds to
    browse — never the return assumption or the SIP. The cap picked here does
    NOT feed RETURN_ASSUMPTIONS / blended_expected_return; a riskier cap must
    never shrink the SIP (breaks self-check [B]).

    Ladder (horizon × importance, per _CATEGORY_LADDER — the Finance critic's
    hand-justified 6-band table; the ±1 importance notch is baked into the
    columns, not applied uniformly):
        <3y   → None (all importances; sleeve too thin to route)
        3–7y  → Large Cap / Large Cap / Large & Mid Cap
        7–12y → Large Cap / Large & Mid Cap / Flexi Cap
        12–15y→ Large & Mid Cap / Flexi Cap / Flexi Cap
        15–20y→ Flexi Cap / Flexi Cap / Mid Cap
        >20y  → Flexi Cap / Mid Cap / Small Cap

    `importance` is read from the goal dict (default "Important" → middle column,
    backward-compatible with goals that carry no importance key). Importance
    moves ONLY this category — NEVER equity_pct / asset_split / blended_return
    (self-check [G] proves the invariance).

    Returns the category string, or None for horizons under the band that
    carries no investable equity sleeve.
    """
    years = float(goal.get("years", 0.0))
    importance = goal.get("importance", "Important")
    col = _IMPORTANCE_COL.get(importance, _IMPORTANCE_COL["Important"])
    for y_min, y_max, categories in _CATEGORY_LADDER:
        if y_min <= years < y_max:
            return categories[col]
    return None


def _resolve_category(category: Optional[str], df) -> Optional[str]:
    """
    Defensive: if the chosen category isn't present in the seed `df`, fall back
    to the nearest broad-market category that IS present, else None. Keeps the
    UI hand-off honest (never hands the screener a category with zero funds).
    Reads ONLY the category column of df — never selects or names a fund.
    """
    if category is None or df is None:
        return category
    try:
        available = set(df["category"].dropna().unique().tolist())
    except Exception:
        return category
    if category in available:
        return category
    # Graceful broad-market fallbacks, most→least preferred.
    for fallback in (FLEXI_CAP, "Equity Scheme - Multi Cap Fund",
                     LARGE_AND_MID_CAP, LARGE_CAP):
        if fallback in available:
            return fallback
    return None


# ── Named-but-UNRANKED non-equity instruments (Mandate #3) ──────────────────
# Generic product CATEGORIES, not specific securities; carry NO ranking/metrics.
def _non_equity_notes(asset_split: dict, years: float) -> list[dict]:
    """
    Describe the debt & gold sleeves as named-but-explicitly-UNRANKED instrument
    *types* (Mandate #3). No Sharpe/Alpha/score — those are equity-vs-NIFTY
    metrics and meaningless off-equity. These are product categories (SGB, PPF,
    short-duration debt), never specific securities.
    """
    notes: list[dict] = []
    if asset_split.get("debt", 0) > 0:
        if years < 3:
            instrument = "Liquid / ultra-short-duration debt funds, or a bank FD"
            note = "Capital-stability sleeve for a near-term goal — not ranked here."
        elif years < 7:
            instrument = "Short-duration debt funds or PPF"
            note = "Stability anchor; unranked (debt metrics aren't comparable to equity)."
        else:
            instrument = "PPF or medium-duration debt funds"
            note = "Long-horizon debt ballast; unranked by design."
        notes.append({"sleeve": "debt", "instrument": instrument, "note": note})
    if asset_split.get("gold", 0) > 0:
        notes.append({
            "sleeve": "gold",
            "instrument": "Sovereign Gold Bonds (SGB) or a gold ETF",
            "note": "Diversifier sleeve; unranked (no equity-style metrics apply).",
        })
    return notes


# ══════════════════════════════════════════════════════════════════════════
# THE ORCHESTRATOR  —  build_plan
# ══════════════════════════════════════════════════════════════════════════

def build_plan(
    goals: list[dict],
    risk_label: str,
    income: Optional[dict],
    sip_params: Optional[dict],
    df,
) -> dict:
    """
    Compose the full personalized plan from goals + risk profile + income.

    Pipeline per goal: reconcile_allocation → blended_expected_return →
    solve_goal (deterministic SIP) → split_sip_by_asset → equity_category_for.

    Args:
        goals:      list of {'name','amount','years'} (from step 0).
        risk_label: person-level label from the quiz (tilt context only).
        income:     {'monthly_income','monthly_expenses','fixed_obligations',
                     'salary_hike_pct','expense_inflation_pct'} or None.
        sip_params: {'inflation_rate','step_up_pct'} or None
                    (defaults: inflation 6%, step_up 0).
        df:         scored_funds DataFrame — used ONLY to validate that a chosen
                    equity CATEGORY exists. NEVER used to name/rank a fund here.

    Returns:
        The PLAN DICT documented at the top of this module.

    Raises:
        AssertionError if any invariant is violated (band membership, rupee
        sum), so a contract break fails loudly instead of rendering wrong money.
    """
    sip_params = sip_params or {}
    inflation_rate = float(sip_params.get("inflation_rate", 0.06))
    step_up_pct = float(sip_params.get("step_up_pct", 0.0))

    plan_goals: list[dict] = []
    total_monthly_sip = 0.0

    for goal in goals:
        name = goal.get("name", "Goal")
        amount = float(goal.get("amount", 0.0))
        years = float(goal.get("years", 0.0))

        # 1–2. Horizon band + risk tilt/cap → asset split.
        alloc = reconcile_allocation(years, risk_label)
        asset_split = {"equity": alloc["equity"], "debt": alloc["debt"], "gold": alloc["gold"]}

        # 3. Honest blended return for THIS goal's mix.
        blended_return = blended_expected_return(asset_split)

        # 4. Deterministic SIP — the ONLY source of any SIP number (Mandate #1).
        result: GoalResult = solve_goal(
            present_value=amount,
            inflation_rate=inflation_rate,
            years=years,
            annual_return=blended_return,
            step_up_pct=step_up_pct,
        )

        # 5. Split the SIP across asset classes in rupees (Σ == monthly_sip).
        sip_split = split_sip_by_asset(result.monthly_sip, asset_split)

        # 6. Equity slice → CATEGORY STRING only (Mandate #4); thin slice → None.
        if asset_split["equity"] >= _EQUITY_ROUTING_FLOOR_PCT:
            equity_category = _resolve_category(equity_category_for(goal), df)
        else:
            equity_category = None

        non_equity_notes = _non_equity_notes(asset_split, years)

        # ── Invariants (fail loudly) ──
        assert alloc["band_low"] - 1e-6 <= asset_split["equity"] <= alloc["band_high"] + 1e-6, (
            f"Goal '{name}': equity {asset_split['equity']}% outside horizon band "
            f"[{alloc['band_low']}, {alloc['band_high']}] — Mandate #2 violated."
        )
        rupee_sum = sip_split["equity"] + sip_split["debt"] + sip_split["gold"]
        assert abs(rupee_sum - result.monthly_sip) < 0.05, (
            f"Goal '{name}': asset rupee split {rupee_sum:.2f} != SIP {result.monthly_sip:.2f}."
        )

        plan_goals.append({
            "name": name,
            "amount": amount,
            "years": years,
            # Optional per-goal importance ("Essential"|"Important"|"Aspirational").
            # Echoed back (default "Important") so the UI can render the right
            # caveat. Importance moves ONLY equity_category — never the SIP,
            # equity_pct, asset_split, band, or blended_return (self-check [G]).
            "importance": goal.get("importance", "Important"),
            "result": result,
            "future_value_required": result.future_value_required,
            "monthly_sip": result.monthly_sip,
            "total_invested": result.total_invested,
            "wealth_gained": result.wealth_gained,
            "equity_pct": asset_split["equity"],
            "asset_split": asset_split,
            "band": {
                "band_low": alloc["band_low"],
                "band_high": alloc["band_high"],
                "tilt": alloc["tilt"],
            },
            "blended_return": blended_return,
            "sip_split": sip_split,
            "equity_category": equity_category,
            "non_equity_notes": non_equity_notes,
        })
        total_monthly_sip += result.monthly_sip

    # ── Affordability via the cashflow projection (longest goal horizon) ──
    cashflow_rows: list[ProjectionYear] = []
    affordability_ok = True
    if income and plan_goals:
        horizon_years = max(1, round(max(g["years"] for g in plan_goals)))
        cashflow_rows = project_cashflow(
            starting_salary=float(income.get("monthly_income", 0.0)) * 12,
            salary_hike_pct=float(income.get("salary_hike_pct", 0.0)),
            starting_expenses=float(income.get("monthly_expenses", 0.0)) * 12,
            expense_inflation_pct=float(income.get("expense_inflation_pct", 0.0)),
            fixed_obligations=float(income.get("fixed_obligations", 0.0)) * 12,
            total_monthly_sip=total_monthly_sip,
            horizon_years=horizon_years,
        )
        affordability_ok = not any(row.is_shortfall for row in cashflow_rows)

    return {
        "goals": plan_goals,
        "total_monthly_sip": round(total_monthly_sip, 2),
        "affordability_ok": affordability_ok,
        "cashflow_rows": cashflow_rows,
        "return_assumptions": dict(RETURN_ASSUMPTIONS),
        "risk_label": risk_label,
    }


# ══════════════════════════════════════════════════════════════════════════
# SELF-CHECK  /  REGRESSION ANCHOR
#   Run:  python shared/planning_engine.py
# ══════════════════════════════════════════════════════════════════════════

def _selfcheck() -> None:
    import pandas as pd

    # Windows consoles default to cp1252, which can't encode ₹ / arrows. Force
    # UTF-8 on stdout so the self-check prints cleanly regardless of codepage.
    import sys as _sys
    try:
        _sys.stdout.reconfigure(encoding="utf-8")  # py3.7+
    except Exception:
        pass

    print("=" * 74)
    print("TrueSIP planning_engine — self-check")
    print("=" * 74)

    # ── A. REGRESSION ANCHOR: reproduce Project 6's Education goal ──────────
    # P6 README table: Education FV required ₹59,04,327; original GUESSED SIP
    # ₹8,000/mo falls ~6.6% short. P6 Education template = inflation 7%,
    # return 12% (dashboard/app.py). Task anchor: PV ~₹30,00,000 @ 7% × 10y.
    print("\n[A] Regression anchor — Project 6 Education goal")
    edu = solve_goal(present_value=30_00_000, inflation_rate=0.07,
                     years=10, annual_return=0.12)
    print(f"    PV ₹30,00,000 @ 7% × 10y  →  FV required = ₹{edu.future_value_required:,.0f}")
    print(f"    (P6 README table FV       =  ₹59,04,327)")
    assert abs(edu.future_value_required - 59_04_327) / 59_04_327 < 0.01, \
        "FV anchor drifted >1% from P6 README's ₹59,04,327"
    print(f"    Required SIP @12%         =  ₹{edu.monthly_sip:,.0f}/mo (deterministic)")
    print(f"    Original GUESS            =  ₹8,000/mo  →  INSUFFICIENT "
          f"(needs ₹{edu.monthly_sip:,.0f})")
    assert edu.monthly_sip > 8000, "Anchor broken: required SIP should exceed the ₹8,000 guess"
    print("    ✓ FV reproduces P6 (<1%); ✓ '₹8,000 needs more' behaviour confirmed")

    # ── B. RECONCILIATION: near-term debt-heavy < long equity-heavy return ──
    print("\n[B] Honest blended return — horizon changes the return assumption")
    near = reconcile_allocation(2, "Aggressive")     # <3y band, even for aggressive
    far = reconcile_allocation(20, "Aggressive")     # >15y band
    r_near = blended_expected_return({k: near[k] for k in ("equity", "debt", "gold")})
    r_far = blended_expected_return({k: far[k] for k in ("equity", "debt", "gold")})
    print(f"    2y  goal split={ {k: near[k] for k in ('equity','debt','gold')} }  "
          f"→ blended {r_near*100:.2f}%")
    print(f"    20y goal split={ {k: far[k] for k in ('equity','debt','gold')} }  "
          f"→ blended {r_far*100:.2f}%")
    assert r_near < r_far, "Near-term goal must assume a LOWER return than long-term"
    print("    ✓ near-term debt-heavy goal gets a LOWER return than long equity goal")

    # ── C. RISK CAP: panic-prone capped at band midpoint ───────────────────
    print("\n[C] Risk tilt/cap — Moderate Conservative capped at band midpoint")
    band_lo, band_hi = horizon_band(10)              # 7–15y → 50–70
    mc = reconcile_allocation(10, "Moderate Conservative")
    agg = reconcile_allocation(10, "Aggressive")
    print(f"    7–15y band = {band_lo:.0f}–{band_hi:.0f}%")
    print(f"    Moderate Conservative equity = {mc['equity']:.0f}%  (midpoint cap)")
    print(f"    Aggressive           equity = {agg['equity']:.0f}%  (top of band)")
    assert mc["equity"] <= (band_lo + band_hi) / 2 + 1e-6, "MC not capped at midpoint"
    assert band_lo - 1e-6 <= agg["equity"] <= band_hi + 1e-6, "Aggressive left the band"
    print("    ✓ panic-prone capped at midpoint; ✓ aggressive stays inside band")

    # ── D. FULL build_plan + invariants on a multi-goal plan ───────────────
    print("\n[D] build_plan end-to-end — invariants")
    df = pd.DataFrame({  # minimal stand-in seed (only 'category' is read here)
        "category": [LARGE_CAP, LARGE_AND_MID_CAP, FLEXI_CAP,
                     "Equity Scheme - Multi Cap Fund"],
        "scheme_name": ["A", "B", "C", "D"],
        "composite_score": [1, 2, 3, 4],
        "category_rank": [1, 1, 1, 1],
    })
    plan = build_plan(
        goals=[
            {"name": "Emergency top-up", "amount": 2_00_000, "years": 2},
            {"name": "Child's Education", "amount": 30_00_000, "years": 10},
            {"name": "Retirement", "amount": 50_00_000, "years": 25},
        ],
        risk_label="Moderate Aggressive",
        income={
            "monthly_income": 1_50_000, "monthly_expenses": 50_000,
            "fixed_obligations": 20_000, "salary_hike_pct": 0.08,
            "expense_inflation_pct": 0.06,
        },
        sip_params={"inflation_rate": 0.06, "step_up_pct": 0.0},
        df=df,
    )
    print(f"    total_monthly_sip = ₹{plan['total_monthly_sip']:,.0f}/mo  "
          f"| affordability_ok = {plan['affordability_ok']}  "
          f"| cashflow_rows = {len(plan['cashflow_rows'])}")
    for g in plan["goals"]:
        rupee_sum = sum(g["sip_split"].values())
        in_band = g["band"]["band_low"] - 1e-6 <= g["equity_pct"] <= g["band"]["band_high"] + 1e-6
        assert in_band, f"{g['name']}: equity {g['equity_pct']}% out of band"
        assert abs(rupee_sum - g["monthly_sip"]) < 0.05, f"{g['name']}: rupee split != SIP"
        print(f"      {g['name']:<18} {g['years']:>4.0f}y  eq={g['equity_pct']:>4.1f}%  "
              f"ret={g['blended_return']*100:>5.2f}%  SIP=₹{g['monthly_sip']:>10,.0f}  "
              f"cat={g['equity_category']}")

    # ── E. COMPLIANCE: no named security paired with personalized output ───
    print("\n[E] Compliance (Mandate #4) — no named fund in any plan output")
    seed_names = set(df["scheme_name"].tolist())
    leaked = []
    for g in plan["goals"]:
        # equity_category must be a CATEGORY string, never a scheme name.
        if g["equity_category"] in seed_names:
            leaked.append((g["name"], g["equity_category"]))
        # non_equity_notes carry no numeric ranking / score keys.
        for note in g["non_equity_notes"]:
            assert not any(k in note for k in ("score", "sharpe", "alpha", "composite_score", "rank")), \
                f"{g['name']}: non-equity note carries a ranking metric (Mandate #3)"
    assert not leaked, f"Named security leaked into personalized plan: {leaked}"
    assert all(g["equity_category"] is None or g["equity_category"].startswith("Equity Scheme")
               for g in plan["goals"]), "equity_category must be a CATEGORY string"
    print("    ✓ only category strings handed off; ✓ no scheme name in plan; "
          "✓ non-equity sleeves unranked")

    # A seed containing EVERY laddered cap so _resolve_category never masks a
    # distinct category behind a broad-market fallback (blocks F–H test the
    # ladder end-to-end, not the fallback path).
    df_full = pd.DataFrame({
        "category": [LARGE_CAP, LARGE_AND_MID_CAP, FLEXI_CAP, MID_CAP, SMALL_CAP,
                     "Equity Scheme - Multi Cap Fund"],
        "scheme_name": ["A", "B", "C", "D", "E", "F"],
        "composite_score": [1, 2, 3, 4, 5, 6],
        "category_rank": [1, 1, 1, 1, 1, 1],
    })

    # ── F. LADDER RESOLUTION: distinct tenures → distinct categories ────────
    # Proves the "only one scheme" complaint is fixed: goals at 5/10/14/25y (all
    # "Important") now resolve to ≥3 DISTINCT categories, with the specific
    # endpoints the Finance critic's table fixes (25y → Mid Cap, 5y → Large Cap).
    print("\n[F] Ladder resolution — distinct tenures yield distinct categories")
    ladder_years = [5, 10, 14, 25]
    ladder_cats = [equity_category_for({"years": y, "importance": "Important"})
                   for y in ladder_years]
    for y, c in zip(ladder_years, ladder_cats):
        print(f"      {y:>3}y (Important) → {c}")
    distinct = {c for c in ladder_cats if c is not None}
    assert len(distinct) >= 3, \
        f"Ladder collapsed: {ladder_years} → only {len(distinct)} distinct categories"
    assert equity_category_for({"years": 25, "importance": "Important"}) == MID_CAP, \
        "25y Important must map to Mid Cap"
    assert equity_category_for({"years": 5, "importance": "Important"}) == LARGE_CAP, \
        "5y Important must map to Large Cap"
    # And the full build_plan path surfaces ≥3 distinct categories too.
    plan_ladder = build_plan(
        goals=[{"name": f"G{y}", "amount": 10_00_000, "years": y} for y in ladder_years],
        risk_label="Aggressive", income=None, sip_params=None, df=df_full,
    )
    distinct_plan = {g["equity_category"] for g in plan_ladder["goals"]
                     if g["equity_category"] is not None}
    assert len(distinct_plan) >= 3, \
        f"build_plan collapsed categories: only {len(distinct_plan)} distinct"
    print(f"    ✓ {len(distinct)} distinct via ladder; ✓ {len(distinct_plan)} distinct via "
          f"build_plan; ✓ 25y→Mid Cap, 5y→Large Cap")

    # ── G. IMPORTANCE INVARIANCE (THE SACRED QUARANTINE PROOF) ─────────────
    # For a fixed horizon, Essential/Important/Aspirational give DIFFERENT
    # equity_category but BYTE-IDENTICAL equity_pct / asset_split / blended_return.
    # Importance is allowed to move ONLY which funds you browse — never the money.
    print("\n[G] Importance invariance — category moves, the money does NOT")
    H = 22  # >20y band: Flexi (Essential) / Mid (Important) / Small (Aspirational)
    variants = {}
    for imp in ("Essential", "Important", "Aspirational"):
        p = build_plan(
            goals=[{"name": "Retirement", "amount": 60_00_000, "years": H, "importance": imp}],
            risk_label="Aggressive", income=None, sip_params=None, df=df_full,
        )
        variants[imp] = p["goals"][0]
        print(f"      {imp:<12} cat={variants[imp]['equity_category']:<32} "
              f"eq={variants[imp]['equity_pct']:.1f}%  ret={variants[imp]['blended_return']*100:.2f}%")
    # Categories MUST differ across the three importances at 22y.
    cats = {variants[i]["equity_category"] for i in variants}
    assert cats == {FLEXI_CAP, MID_CAP, SMALL_CAP}, \
        f"22y importances should be Flexi/Mid/Small, got {cats}"
    # equity_pct, asset_split, blended_return, band, sip_split MUST be identical.
    base = variants["Important"]
    for imp in ("Essential", "Aspirational"):
        v = variants[imp]
        assert v["equity_pct"] == base["equity_pct"], f"{imp}: equity_pct moved"
        assert v["asset_split"] == base["asset_split"], f"{imp}: asset_split moved"
        assert v["blended_return"] == base["blended_return"], f"{imp}: blended_return moved"
        assert v["band"] == base["band"], f"{imp}: band moved"
        assert v["sip_split"] == base["sip_split"], f"{imp}: sip_split moved"
        assert v["monthly_sip"] == base["monthly_sip"], f"{imp}: monthly_sip moved"
    print("    ✓ category differs (Flexi/Mid/Small); ✓ equity_pct, asset_split, "
          "blended_return, sip_split IDENTICAL")

    # ── H. SMALL CAP GATE: only >20y AND Aspirational reaches Small Cap ─────
    print("\n[H] Small Cap gate — years ≤ 20 never reaches Small Cap")
    for y in (3, 7, 12, 15, 20):
        for imp in ("Essential", "Important", "Aspirational"):
            c = equity_category_for({"years": y, "importance": imp})
            assert c != SMALL_CAP, f"{y}y/{imp} wrongly reached Small Cap (gate is >20y)"
    assert equity_category_for({"years": 25, "importance": "Aspirational"}) == SMALL_CAP, \
        ">20y Aspirational must reach Small Cap"
    assert equity_category_for({"years": 25, "importance": "Essential"}) != SMALL_CAP, \
        ">20y Essential must NOT reach Small Cap (non-Essential gate)"
    print("    ✓ no goal ≤ 20y hits Small Cap under any importance; "
          "✓ >20y Aspirational does; ✓ >20y Essential does not")

    print("\n" + "=" * 74)
    print("ALL SELF-CHECKS PASSED")
    print("=" * 74)


if __name__ == "__main__":
    _selfcheck()
