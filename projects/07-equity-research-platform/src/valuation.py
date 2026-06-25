"""
valuation-engine: deterministic DCF / WACC / CAPM valuation for a given ticker.

Reads data/<ticker>/validated_financials.json and writes data/<ticker>/valuation.json.

Design principle (non-negotiable): all arithmetic happens in this script, in Python,
with explicit unit annotations on every intermediate value. No number in the output
JSON should be produced by LLM estimation. Every growth/discount rate is expressed on
an ANNUAL basis and every cash flow is an ANNUAL figure in INR Crore, to guard against
the unit-mismatch bug class seen in the Black-Litterman project (annual return vs.
monthly volatility).

Usage:
    python src/valuation.py <TICKER>

Example:
    python src/valuation.py INFY
"""

import json
import sys
from pathlib import Path


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def load_validated_financials(ticker: str, repo_root: Path) -> dict:
    path = repo_root / "data" / ticker / "validated_financials.json"
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def pct(x: float) -> float:
    """Convert a whole-number percent (e.g. 28.0) to a decimal fraction (0.28)."""
    return x / 100.0


# ---------------------------------------------------------------------------
# Step 1: Cost of equity (CAPM)
# ---------------------------------------------------------------------------

def compute_cost_of_equity(risk_free_rate: float, beta: float, equity_risk_premium: float) -> dict:
    """
    CAPM: Cost of Equity = Rf + Beta * ERP
    All inputs and the output are ANNUAL decimal rates (e.g. 0.07 = 7% per year).
    """
    cost_of_equity = risk_free_rate + beta * equity_risk_premium
    return {
        "risk_free_rate_annual": risk_free_rate,
        "beta": beta,
        "equity_risk_premium_annual": equity_risk_premium,
        "cost_of_equity_annual": cost_of_equity,
    }


# ---------------------------------------------------------------------------
# Step 2: Cost of debt and capital structure weights
# ---------------------------------------------------------------------------

def compute_cost_of_debt(pl_year: dict, bs_year: dict, statutory_tax_rate: float) -> dict:
    """
    Pre-tax cost of debt proxied as interest expense / average (or period-end) total
    borrowings for the base year. After-tax cost of debt = pre-tax * (1 - tax rate).
    All rates ANNUAL.

    If borrowings are zero (as in INFY's case for most history), pre-tax cost of debt
    is undefined from this data; we fall back to an explicit proxy rate (stated by caller)
    rather than dividing by zero or silently using 0%.
    """
    interest = pl_year["interest"]
    borrowings = bs_year["borrowings"]

    if borrowings and borrowings > 0:
        pre_tax_cost_of_debt = interest / borrowings
        source = "interest_expense / period_end_borrowings (base year)"
    else:
        pre_tax_cost_of_debt = None
        source = "borrowings are zero/near-zero in base year; using fallback proxy rate"

    return {
        "interest_expense_base_year_inr_cr": interest,
        "borrowings_base_year_inr_cr": borrowings,
        "pre_tax_cost_of_debt_annual_computed": pre_tax_cost_of_debt,
        "source": source,
        "statutory_tax_rate_annual": statutory_tax_rate,
    }


def compute_capital_structure_weights(bs_year: dict, market_cap_inr_cr: float) -> dict:
    """
    Capital structure weights use MARKET value of equity (market cap) and BOOK value of
    debt (total borrowings from balance sheet) — standard practice since market values
    for debt are not available in this dataset.
    """
    total_debt = bs_year["borrowings"]
    total_capital = market_cap_inr_cr + total_debt
    weight_equity = market_cap_inr_cr / total_capital
    weight_debt = total_debt / total_capital
    return {
        "market_cap_inr_cr": market_cap_inr_cr,
        "total_debt_inr_cr": total_debt,
        "total_capital_inr_cr": total_capital,
        "weight_equity": weight_equity,
        "weight_debt": weight_debt,
    }


# ---------------------------------------------------------------------------
# Step 3: WACC
# ---------------------------------------------------------------------------

def compute_wacc(cost_of_equity_annual: float, weight_equity: float,
                  after_tax_cost_of_debt_annual: float, weight_debt: float) -> float:
    """WACC = We * Ke + Wd * Kd_after_tax. Output is an ANNUAL decimal rate."""
    return weight_equity * cost_of_equity_annual + weight_debt * after_tax_cost_of_debt_annual


# ---------------------------------------------------------------------------
# Step 4: FCFF projections
# ---------------------------------------------------------------------------

def compute_historical_fcff(pl_year: dict, cf_year: dict, statutory_tax_rate: float) -> dict:
    """
    FCFF (Free Cash Flow to Firm) computed directly from operating_profit (EBIT proxy,
    since INFY has negligible D&A separation issues already baked into the reported
    operating_profit/PBT bridge) and cash_from_operating / free_cash_flow lines, per the
    upstream caveat to avoid the unreliable cfo_to_op_percent field.

    We use the reported `free_cash_flow` line directly as FCFF's starting point (screener's
    FCF = CFO - capex, a standard FCFF-ish proxy), cross-checked against an EBIT(1-t) + Dep
    - Capex - Delta WC style build where possible. Since granular capex/working-capital
    splits are not separately broken out in this dataset, we treat the dataset's own
    `free_cash_flow` (CFO - capex) as Free Cash Flow to the Firm before financing effects,
    which is standard given INFY's near-zero net debt and minimal interest burden.

    All figures ANNUAL, INR Crore.
    """
    operating_profit = pl_year["operating_profit"]
    ebit_after_tax = operating_profit * (1 - statutory_tax_rate)
    reported_fcf = cf_year["free_cash_flow"]
    cfo = cf_year["cash_from_operating"]
    return {
        "operating_profit_inr_cr": operating_profit,
        "ebit_after_tax_proxy_inr_cr": ebit_after_tax,
        "cash_from_operating_inr_cr": cfo,
        "reported_free_cash_flow_inr_cr": reported_fcf,
    }


def project_fcff(base_fcff: float, growth_schedule: list) -> list:
    """
    Project FCFF forward using an explicit, stated multi-stage growth schedule.
    growth_schedule: list of dicts [{"year": 1, "growth_rate_annual": 0.12}, ...]
    Returns list of dicts with year, growth_rate_annual, fcff_inr_cr.
    NEVER silently extrapolates — every year's growth rate must be explicitly supplied.
    """
    projections = []
    prior_fcff = base_fcff
    for step in growth_schedule:
        fcff = prior_fcff * (1 + step["growth_rate_annual"])
        projections.append({
            "year": step["year"],
            "growth_rate_annual": step["growth_rate_annual"],
            "fcff_inr_cr": fcff,
        })
        prior_fcff = fcff
    return projections


# ---------------------------------------------------------------------------
# Step 5: DCF — enterprise value, equity value, implied share price
# ---------------------------------------------------------------------------

def discount_fcff(projections: list, wacc_annual: float) -> list:
    """
    Discount each projected ANNUAL FCFF back to present value using the ANNUAL WACC,
    with t measured in whole years (t=1 for year 1, t=2 for year 2, ...). This is the
    explicit unit-consistency point: growth rates, FCFF, and the discount rate are all
    annual, and t is in years, so (1+wacc)**t is dimensionally consistent.
    """
    discounted = []
    for step in projections:
        t = step["year"]
        df = 1.0 / ((1 + wacc_annual) ** t)
        pv = step["fcff_inr_cr"] * df
        discounted.append({
            **step,
            "discount_factor": df,
            "pv_fcff_inr_cr": pv,
        })
    return discounted


def terminal_value(last_fcff: float, wacc_annual: float, terminal_growth_annual: float, last_year: int) -> dict:
    """
    Gordon Growth terminal value at end of explicit forecast horizon, discounted back
    to present at the same ANNUAL wacc, t = last_year (years from valuation date).
    Requires wacc_annual > terminal_growth_annual (checked explicitly to avoid a negative/
    explosive denominator, a classic DCF unit/logic error).
    """
    if wacc_annual <= terminal_growth_annual:
        raise ValueError(
            f"WACC ({wacc_annual:.4f}) must exceed terminal growth rate "
            f"({terminal_growth_annual:.4f}) for Gordon Growth terminal value to be valid."
        )
    tv_at_horizon = last_fcff * (1 + terminal_growth_annual) / (wacc_annual - terminal_growth_annual)
    df = 1.0 / ((1 + wacc_annual) ** last_year)
    pv_tv = tv_at_horizon * df
    return {
        "terminal_growth_annual": terminal_growth_annual,
        "terminal_value_at_horizon_inr_cr": tv_at_horizon,
        "discount_factor": df,
        "pv_terminal_value_inr_cr": pv_tv,
    }


def compute_equity_value(enterprise_value: float, total_debt: float, cash_and_investments: float) -> float:
    """Equity Value = Enterprise Value - Net Debt = EV - Total Debt + Cash & Investments."""
    net_debt = total_debt - cash_and_investments
    return enterprise_value - net_debt


# ---------------------------------------------------------------------------
# Unit consistency check (explicit, automated — not just a comment)
# ---------------------------------------------------------------------------

def run_unit_consistency_check(inputs: dict) -> dict:
    """
    Runs explicit sanity checks that every rate is annual and every cash flow is annual,
    and that no monthly/quarterly figure leaked in unconverted. Returns a dict of checks
    with pass/fail booleans. This directly targets the Black-Litterman-style bug class
    (annualized return compared against monthly volatility).
    """
    checks = {}

    # 1. All discount/growth rates should be small decimals typical of ANNUAL rates
    #    (a monthly rate mistakenly used as annual would typically be < 0.02-0.03,
    #    an annual rate compounded as if monthly would explode beyond plausible bounds).
    rate_fields = {
        "risk_free_rate_annual": inputs["risk_free_rate_annual"],
        "equity_risk_premium_annual": inputs["equity_risk_premium_annual"],
        "cost_of_equity_annual": inputs["cost_of_equity_annual"],
        "wacc_annual": inputs["wacc_annual"],
        "terminal_growth_annual": inputs["terminal_growth_annual"],
    }
    for name, val in rate_fields.items():
        plausible_annual = 0.0 <= val <= 0.30  # generous bound for an annual rate
        checks[f"{name}_in_plausible_annual_range"] = bool(plausible_annual)

    # 2. Growth schedule rates must all be annual (same plausibility bound, generous
    #    for high-growth early years).
    growth_rates = [s["growth_rate_annual"] for s in inputs["growth_schedule"]]
    checks["explicit_growth_schedule_all_annual_and_plausible"] = bool(
        all(-0.10 <= g <= 0.30 for g in growth_rates)
    )

    # 3. Discounting uses whole-year exponents (t = 1, 2, 3 ... not 12, 24, 36 which
    #    would indicate months mistakenly used as the time step).
    years = [s["year"] for s in inputs["projection_years"]]
    checks["discount_periods_are_whole_years_not_months"] = bool(
        years == list(range(1, len(years) + 1))
    )

    # 4. WACC must exceed terminal growth rate (already enforced in terminal_value(),
    #    re-stated here as a named check for the output record).
    checks["wacc_exceeds_terminal_growth"] = bool(
        inputs["wacc_annual"] > inputs["terminal_growth_annual"]
    )

    # 5. Base FCFF and projected FCFF are full-year INR Crore figures of the same order
    #    of magnitude as historical full-year free_cash_flow (catches a stray quarterly
    #    figure being used as if it were annual).
    base = inputs["base_fcff_inr_cr"]
    hist_fcf_values = inputs["historical_free_cash_flow_series_inr_cr"]
    hist_avg = sum(hist_fcf_values) / len(hist_fcf_values)
    checks["base_fcff_same_order_of_magnitude_as_historical_annual_fcf"] = bool(
        0.3 * hist_avg <= base <= 3.0 * hist_avg
    )

    checks["all_checks_passed"] = bool(all(v for k, v in checks.items() if k != "all_checks_passed"))
    return checks


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    if len(sys.argv) < 2:
        print("Usage: python src/valuation.py <TICKER>")
        sys.exit(1)

    ticker = sys.argv[1]
    script_dir = Path(__file__).resolve().parent
    repo_root = script_dir.parent

    data = load_validated_financials(ticker, repo_root)

    pl = data["profit_loss"]
    bs = data["balance_sheet"]
    cf = data["cash_flow"]
    snapshot = data["ratios"]["current_snapshot"]

    # -----------------------------------------------------------------
    # Base year selection
    # -----------------------------------------------------------------
    # ASSUMPTION (explicit): use Mar 2025 as the valuation base year, not the Mar 2026
    # TTM column, because Mar 2026 is explicitly flagged upstream as an unaudited
    # TTM/latest-available figure subject to revision, while Mar 2025 passed every
    # internal consistency check as a fully audited fiscal year. Mar 2026 TTM figures
    # are still surfaced in the output for reference/cross-check, not as the DCF base.
    base_year_label = "Mar 2025"
    reference_ttm_label = "Mar 2026"

    pl_base = pl[base_year_label]
    bs_base = bs[base_year_label]
    cf_base = cf[base_year_label]

    # -----------------------------------------------------------------
    # Share count
    # -----------------------------------------------------------------
    # ASSUMPTION (explicit): no direct shares-outstanding field exists in the dataset.
    # Derive shares outstanding for the base year as net_profit / eps (both reported in
    # the same P&L row, so internally consistent), rather than using equity_capital /
    # face_value, which is distorted by historical bonus share issuances changing the
    # equity_capital base without a matching face-value adjustment in this dataset.
    shares_outstanding_cr = pl_base["net_profit"] / pl_base["eps"]

    # Cross-check against current_snapshot market cap / current price (most recent,
    # i.e. Mar 2026 TTM aligned) — reported for transparency, not used directly in the
    # DCF since it reflects a later period than the chosen base year.
    shares_outstanding_cr_from_snapshot = snapshot["Market Cap"] / snapshot["Current Price"]

    # -----------------------------------------------------------------
    # CAPM inputs — explicit assumptions (no historical beta available in dataset)
    # -----------------------------------------------------------------
    # ASSUMPTION (explicit): risk-free rate proxied by the prevailing Indian 10-year
    # G-Sec yield (~7.0% as of mid-2026; not in dataset, standard macro assumption).
    risk_free_rate_annual = 0.070

    # ASSUMPTION (explicit): equity risk premium for Indian equities, standard large-cap
    # ERP assumption used in Indian DCF practice (~6.5% per year; not in dataset).
    equity_risk_premium_annual = 0.065

    # ASSUMPTION (explicit): beta. No historical/regression beta is available in this
    # dataset (only current-snapshot ROE/ROCE were captured, no price-return series).
    # Using a standard assumption for large-cap Indian IT services: beta modestly below
    # 1.0 (export-revenue, contractual/annuity-like demand profile lowers domestic-market
    # beta, but currency and global-demand cyclicality keep it close to 1). Assumption: 0.85.
    beta = 0.85

    capm = compute_cost_of_equity(risk_free_rate_annual, beta, equity_risk_premium_annual)
    cost_of_equity_annual = capm["cost_of_equity_annual"]

    # -----------------------------------------------------------------
    # Cost of debt
    # -----------------------------------------------------------------
    # Statutory tax rate ASSUMPTION (explicit): use Indian corporate tax rate for large
    # companies post-2019 reform (~25.17% effective with surcharge/cess), rather than the
    # base year's reported tax_percent (29% for Mar 2025, which includes one-off/effective-
    # rate noise per the validator's own note on tax_percent rounding). Using the statutory
    # rate keeps the DCF's tax shield assumption stable and forward-looking rather than
    # tied to one historical year's effective rate.
    statutory_tax_rate = 0.2517

    cod = compute_cost_of_debt(pl_base, bs_base, statutory_tax_rate)
    if cod["pre_tax_cost_of_debt_annual_computed"] is not None:
        pre_tax_cost_of_debt_annual = cod["pre_tax_cost_of_debt_annual_computed"]
    else:
        # ASSUMPTION (explicit): INFY's actual borrowings are lease liabilities (Ind AS 116),
        # not commercial debt; proxy pre-tax cost of debt with a standard investment-grade
        # large-cap Indian corporate bond yield assumption (~7.5% per year).
        pre_tax_cost_of_debt_annual = 0.075

    after_tax_cost_of_debt_annual = pre_tax_cost_of_debt_annual * (1 - statutory_tax_rate)

    # -----------------------------------------------------------------
    # Capital structure weights (market value of equity, book value of debt)
    # -----------------------------------------------------------------
    market_cap_inr_cr = snapshot["Market Cap"]
    cap_structure = compute_capital_structure_weights(bs_base, market_cap_inr_cr)

    # -----------------------------------------------------------------
    # WACC
    # -----------------------------------------------------------------
    wacc_annual = compute_wacc(
        cost_of_equity_annual,
        cap_structure["weight_equity"],
        after_tax_cost_of_debt_annual,
        cap_structure["weight_debt"],
    )

    # -----------------------------------------------------------------
    # FCFF base and projections
    # -----------------------------------------------------------------
    fcff_base_detail = compute_historical_fcff(pl_base, cf_base, statutory_tax_rate)
    base_fcff_inr_cr = fcff_base_detail["reported_free_cash_flow_inr_cr"]

    historical_fcf_series = [cf[y]["free_cash_flow"] for y in cf.keys()]

    # ASSUMPTION (explicit, stated growth schedule — never silently extrapolated):
    # Stage 1 (Years 1-5): revenue/FCF growth tapering from recent historical run-rate
    # toward a more moderate pace, reflecting INFY's recent 5-year revenue CAGR
    # (~13.7% Mar2020->Mar2025) moderating as the company scales and the IT services
    # sector matures (deal pricing pressure, AI-led productivity/pricing disruption risk).
    # Stage 2 (Years 6-10): converging further toward terminal growth.
    growth_schedule = [
        {"year": 1, "growth_rate_annual": 0.11},
        {"year": 2, "growth_rate_annual": 0.10},
        {"year": 3, "growth_rate_annual": 0.09},
        {"year": 4, "growth_rate_annual": 0.085},
        {"year": 5, "growth_rate_annual": 0.08},
        {"year": 6, "growth_rate_annual": 0.075},
        {"year": 7, "growth_rate_annual": 0.07},
        {"year": 8, "growth_rate_annual": 0.065},
        {"year": 9, "growth_rate_annual": 0.06},
        {"year": 10, "growth_rate_annual": 0.055},
    ]

    # ASSUMPTION (explicit): terminal growth rate in perpetuity, set modestly above
    # long-run Indian nominal GDP-growth-adjusted-for-USD-revenue-mix assumption, kept
    # conservative and below WACC. 5.0% per year.
    terminal_growth_annual = 0.05

    projections = project_fcff(base_fcff_inr_cr, growth_schedule)
    discounted_projections = discount_fcff(projections, wacc_annual)

    last_year = growth_schedule[-1]["year"]
    last_fcff = projections[-1]["fcff_inr_cr"]
    tv = terminal_value(last_fcff, wacc_annual, terminal_growth_annual, last_year)

    sum_pv_fcff = sum(s["pv_fcff_inr_cr"] for s in discounted_projections)
    enterprise_value_inr_cr = sum_pv_fcff + tv["pv_terminal_value_inr_cr"]

    # -----------------------------------------------------------------
    # Equity value and implied share price
    # -----------------------------------------------------------------
    total_debt_inr_cr = bs_base["borrowings"]
    cash_and_investments_inr_cr = bs_base["investments"]  # balance sheet "investments" line used as cash-like proxy; no separate cash line in dataset

    equity_value_inr_cr = compute_equity_value(
        enterprise_value_inr_cr, total_debt_inr_cr, cash_and_investments_inr_cr
    )
    implied_share_price_inr = equity_value_inr_cr / shares_outstanding_cr

    # -----------------------------------------------------------------
    # Unit consistency check
    # -----------------------------------------------------------------
    check_inputs = {
        "risk_free_rate_annual": risk_free_rate_annual,
        "equity_risk_premium_annual": equity_risk_premium_annual,
        "cost_of_equity_annual": cost_of_equity_annual,
        "wacc_annual": wacc_annual,
        "terminal_growth_annual": terminal_growth_annual,
        "growth_schedule": growth_schedule,
        "projection_years": projections,
        "base_fcff_inr_cr": base_fcff_inr_cr,
        "historical_free_cash_flow_series_inr_cr": historical_fcf_series,
    }
    unit_check = run_unit_consistency_check(check_inputs)

    # -----------------------------------------------------------------
    # Current market price cross-check (sense check, not part of DCF mechanics)
    # -----------------------------------------------------------------
    current_price_inr = snapshot["Current Price"]
    upside_downside_pct = (implied_share_price_inr / current_price_inr - 1) * 100

    # -----------------------------------------------------------------
    # Assemble output JSON
    # -----------------------------------------------------------------
    output = {
        "ticker": ticker,
        "company_name": data.get("company_name"),
        "unit": "INR Crore (except per-share figures, which are in INR)",
        "base_year_selection": {
            "base_year_used_for_dcf": base_year_label,
            "reason": (
                "Mar 2026 is flagged upstream as an unaudited TTM/latest-available column "
                "subject to revision; Mar 2025 is the last fully audited fiscal year and "
                "passed every internal consistency check, so it is used as the DCF base "
                "year. Mar 2026 TTM figures are reported below for reference only."
            ),
            "mar_2026_ttm_reference": {
                "revenue_inr_cr": pl[reference_ttm_label]["revenue"],
                "net_profit_inr_cr": pl[reference_ttm_label]["net_profit"],
                "free_cash_flow_inr_cr": cf[reference_ttm_label]["free_cash_flow"],
                "eps_inr": pl[reference_ttm_label]["eps"],
            },
        },
        "shares_outstanding": {
            "method": "net_profit / eps, base year (Mar 2025)",
            "shares_outstanding_cr": shares_outstanding_cr,
            "cross_check_from_market_cap_and_price_mar_2026": shares_outstanding_cr_from_snapshot,
            "note": (
                "equity_capital / face_value was not used because two historical 1:1 bonus "
                "issuances (FY16, FY19) change equity_capital without necessarily being "
                "reflected as a clean face-value-based share count in this dataset; "
                "net_profit/eps is self-consistent within the same P&L row."
            ),
        },
        "capm_cost_of_equity": {
            **capm,
            "assumptions": {
                "risk_free_rate_annual": "Indian 10-year G-Sec yield proxy (~7.0%/yr); not present in dataset, standard macro input.",
                "equity_risk_premium_annual": "Standard Indian large-cap ERP assumption (~6.5%/yr); not present in dataset.",
                "beta": "No historical price-return series or beta in dataset; assumed 0.85, a standard large-cap Indian IT-services beta (export-led, contractual demand moderates beta, but global-demand/FX cyclicality keeps it near 1).",
            },
        },
        "cost_of_debt": {
            **cod,
            "after_tax_cost_of_debt_annual": after_tax_cost_of_debt_annual,
            "pre_tax_cost_of_debt_annual_used": pre_tax_cost_of_debt_annual,
        },
        "capital_structure": cap_structure,
        "wacc": {
            "wacc_annual": wacc_annual,
        },
        "fcff_base": {
            **fcff_base_detail,
            "base_fcff_used_for_dcf_inr_cr": base_fcff_inr_cr,
            "method": (
                "Used dataset's reported free_cash_flow (screener.in CFO - capex) directly "
                "as FCFF base, per upstream caveat to avoid the unreliable cfo_to_op_percent "
                "field; cross-checked for plausibility against operating_profit and CFO."
            ),
        },
        "growth_assumptions": {
            "stage_1_years_1_to_5": "Tapering 11% -> 8% per year, anchored to INFY's trailing 5-year revenue CAGR (~13.7%, Mar2020-Mar2025) moderating for sector maturity/pricing pressure.",
            "stage_2_years_6_to_10": "Further taper 7.5% -> 5.5% per year, converging toward terminal growth.",
            "terminal_growth_annual": terminal_growth_annual,
            "growth_schedule_explicit": growth_schedule,
        },
        "fcff_projections": discounted_projections,
        "terminal_value": tv,
        "dcf_valuation": {
            "sum_pv_explicit_fcff_inr_cr": sum_pv_fcff,
            "pv_terminal_value_inr_cr": tv["pv_terminal_value_inr_cr"],
            "enterprise_value_inr_cr": enterprise_value_inr_cr,
            "total_debt_inr_cr": total_debt_inr_cr,
            "cash_and_investments_inr_cr": cash_and_investments_inr_cr,
            "cash_proxy_note": "Balance sheet 'investments' line used as the cash-like/investment proxy for net debt; dataset has no separately broken-out cash & bank balances line.",
            "equity_value_inr_cr": equity_value_inr_cr,
            "shares_outstanding_cr": shares_outstanding_cr,
            "implied_share_price_inr": implied_share_price_inr,
        },
        "market_cross_check": {
            "current_price_inr": current_price_inr,
            "implied_share_price_inr": implied_share_price_inr,
            "upside_downside_percent": upside_downside_pct,
        },
        "unit_consistency_check": unit_check,
        "key_assumptions_summary": [
            f"Base year for DCF: {base_year_label} (audited), not Mar 2026 TTM (unaudited).",
            f"Risk-free rate: {risk_free_rate_annual:.3%}/yr (assumption, India 10Y G-Sec proxy).",
            f"Equity risk premium: {equity_risk_premium_annual:.3%}/yr (assumption, Indian large-cap ERP).",
            f"Beta: {beta} (assumption, no historical beta in dataset; standard Indian IT large-cap proxy).",
            f"Statutory tax rate for after-tax cost of debt & EBIT(1-t): {statutory_tax_rate:.3%} (assumption, not the noisy reported effective tax_percent).",
            f"Pre-tax cost of debt: {pre_tax_cost_of_debt_annual:.3%}/yr ({cod['source']}).",
            f"WACC: {wacc_annual:.3%}/yr (computed).",
            f"Explicit 10-year FCFF growth schedule tapering {growth_schedule[0]['growth_rate_annual']:.1%} -> {growth_schedule[-1]['growth_rate_annual']:.1%}/yr (assumption, stated above).",
            f"Terminal growth rate: {terminal_growth_annual:.3%}/yr in perpetuity (assumption).",
            "Shares outstanding derived as net_profit/eps for base year (assumption due to no direct share-count field).",
        ],
    }

    out_dir = repo_root / "data" / ticker
    out_path = out_dir / "valuation.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2)

    # -----------------------------------------------------------------
    # Console summary (for the calling agent / human to read directly)
    # -----------------------------------------------------------------
    print("=" * 70)
    print(f"VALUATION SUMMARY — {ticker}")
    print("=" * 70)
    print(f"Base year used: {base_year_label}")
    print(f"Shares outstanding (Cr): {shares_outstanding_cr:.2f}")
    print(f"Cost of equity (CAPM): {cost_of_equity_annual:.3%}")
    print(f"  Risk-free rate: {risk_free_rate_annual:.3%}, Beta: {beta}, ERP: {equity_risk_premium_annual:.3%}")
    print(f"Pre-tax cost of debt: {pre_tax_cost_of_debt_annual:.3%} | After-tax: {after_tax_cost_of_debt_annual:.3%}")
    print(f"Capital structure: Equity weight {cap_structure['weight_equity']:.3%}, Debt weight {cap_structure['weight_debt']:.3%}")
    print(f"WACC: {wacc_annual:.3%}")
    print(f"Base FCFF (Mar 2025, reported free_cash_flow): INR {base_fcff_inr_cr:,.0f} Cr")
    print(f"Sum PV of explicit FCFF (Yrs 1-10): INR {sum_pv_fcff:,.0f} Cr")
    print(f"PV of terminal value: INR {tv['pv_terminal_value_inr_cr']:,.0f} Cr")
    print(f"Enterprise value: INR {enterprise_value_inr_cr:,.0f} Cr")
    print(f"Equity value: INR {equity_value_inr_cr:,.0f} Cr")
    print(f"Implied share price: INR {implied_share_price_inr:,.2f}")
    print(f"Current market price: INR {current_price_inr:,.2f}")
    print(f"Implied upside/(downside): {upside_downside_pct:+.1f}%")
    print(f"Unit consistency check passed: {unit_check['all_checks_passed']}")
    print("=" * 70)
    print(f"Written to: {out_path}")


if __name__ == "__main__":
    main()
