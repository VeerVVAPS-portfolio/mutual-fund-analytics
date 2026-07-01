"""
shared/protection.py — insurance adequacy and debt-obligation math.

Adapted from projects/06-goal-based-sip-planner/src/protection.py.
CHANGES FROM ORIGINAL:
  - Zero changes to methodology or math.
  - Docstrings expanded to clarify role in TrueSIP's Advanced wealth check section.
  - All public functions and dataclasses exported at module level.

Methodology sourced from standard Indian financial-planning practice:
  - Life cover:    DIME-style needs-based method (Debt + Income replacement + Goals).
  - Health cover:  Indian city-tier sum-insured benchmarks, family-size scaled.
  - Emergency fund: Months-of-expenses guidance, scaled by dependents.
  - FOIR:          Fixed Obligation to Income Ratio — Indian bank lending gate.

Usage in TrueSIP: the streamlit-ux-builder fills the "Advanced wealth check"
expander with insurance gap cards and FOIR gauge, using inputs from
session_state['income'] and session_state['advanced'].
"""

from __future__ import annotations

from dataclasses import dataclass, field

# ── Health insurance benchmarks (Indian city-tier) ────────────────────────────
# Recommended sum insured for a family of 4 (standard floater plan).
HEALTH_COVER_BY_TIER: dict[str, int] = {
    "Metro / Tier-1": 30_00_000,
    "Tier-2": 20_00_000,
    "Tier-3": 12_00_000,
}
# Recommended sum insured for an individual (single person).
HEALTH_COVER_INDIVIDUAL_BY_TIER: dict[str, int] = {
    "Metro / Tier-1": 10_00_000,
    "Tier-2": 7_00_000,
    "Tier-3": 5_00_000,
}
HEALTH_COVER_PER_EXTRA_DEPENDENT = 5_00_000
HEALTH_COVER_BASE_FAMILY_SIZE = 4

EMERGENCY_FUND_BASE_MONTHS = 6
EMERGENCY_FUND_MAX_MONTHS = 12

FOIR_SAFE_THRESHOLD = 0.40
FOIR_CAUTION_THRESHOLD = 0.55


def outstanding_loan_balance(emi: float, annual_rate: float, remaining_months: int) -> float:
    """
    Standard loan amortization formula: P = EMI * [1-(1+r)^-n] / r.
    Returns 0 when remaining_months <= 0.

    Args:
        emi:               Monthly EMI amount (₹).
        annual_rate:       Annual interest rate as decimal (e.g. 0.085 for 8.5%).
        remaining_months:  Months left on the loan.
    """
    if remaining_months <= 0:
        return 0.0
    monthly_rate = annual_rate / 12
    if monthly_rate == 0:
        return emi * remaining_months
    return emi * (1 - (1 + monthly_rate) ** -remaining_months) / monthly_rate


@dataclass
class LifeCoverResult:
    debt_component: float
    goals_component: float
    income_replacement_component: float
    total_need: float
    current_cover: float
    gap: float
    replacement_years: int


def recommended_life_cover(
    goals_results: list[dict],
    loans: list[dict],
    annual_expenses: float,
    dependents: int,
    current_cover: float,
) -> LifeCoverResult:
    """
    DIME-style life cover need: outstanding debt + goals lump-sum + income
    replacement, minus existing cover.

    Each goal's "lump-sum equivalent" is the PV of the goal's future-value target
    at its assumed return: fv / (1+r)^years — the amount an insurance payout
    would need to grow to still reach the target without further SIPs.

    Args:
        goals_results: List of dicts, each with keys:
                         'result' (GoalResult), 'return' (annual return decimal),
                         'years' (time horizon).
        loans:         List of dicts, each with keys:
                         'emi' (₹/month), 'rate' (annual decimal), 'remaining_months'.
        annual_expenses: Annual household expenses (₹).
        dependents:    Number of financial dependents.
        current_cover: Existing life insurance sum assured (₹).

    Returns:
        LifeCoverResult with debt/goals/income components, total need, and gap.
    """
    debt_component = sum(
        outstanding_loan_balance(loan["emi"], loan["rate"], loan["remaining_months"])
        for loan in loans
    )

    goals_component = 0.0
    for g in goals_results:
        r = g["result"]
        growth = (1 + g["return"]) ** g["years"]
        goals_component += r.future_value_required / growth if growth > 0 else r.future_value_required

    replacement_years = min(15, 5 + 2 * dependents) if dependents > 0 else 0
    income_replacement_component = annual_expenses * replacement_years

    total_need = debt_component + goals_component + income_replacement_component
    gap = max(0.0, total_need - current_cover)

    return LifeCoverResult(
        debt_component=debt_component,
        goals_component=goals_component,
        income_replacement_component=income_replacement_component,
        total_need=total_need,
        current_cover=current_cover,
        gap=gap,
        replacement_years=replacement_years,
    )


@dataclass
class HealthCoverResult:
    recommended: float
    current_cover: float
    gap: float


def recommended_health_cover(
    dependents: int,
    city_tier: str,
    current_cover: float,
) -> HealthCoverResult:
    """
    Recommended health insurance sum insured, interpolated by family size
    between individual and family-of-4 benchmarks for the given city tier.
    """
    family_size = 1 + dependents
    individual = HEALTH_COVER_INDIVIDUAL_BY_TIER.get(city_tier, HEALTH_COVER_INDIVIDUAL_BY_TIER["Tier-2"])
    family_base = HEALTH_COVER_BY_TIER.get(city_tier, HEALTH_COVER_BY_TIER["Tier-2"])

    if family_size >= HEALTH_COVER_BASE_FAMILY_SIZE:
        extra_members = family_size - HEALTH_COVER_BASE_FAMILY_SIZE
        recommended = family_base + extra_members * HEALTH_COVER_PER_EXTRA_DEPENDENT
    else:
        fraction = (family_size - 1) / (HEALTH_COVER_BASE_FAMILY_SIZE - 1)
        recommended = individual + fraction * (family_base - individual)

    gap = max(0.0, recommended - current_cover)
    return HealthCoverResult(recommended=recommended, current_cover=current_cover, gap=gap)


@dataclass
class EmergencyFundResult:
    recommended_months: int
    recommended: float
    current_savings: float
    gap: float


def recommended_emergency_fund(
    monthly_expenses: float,
    dependents: int,
    current_savings: float,
) -> EmergencyFundResult:
    """
    Emergency fund target: 6 months base + 1 month per dependent above 2,
    capped at 12 months.
    """
    months = min(EMERGENCY_FUND_MAX_MONTHS, EMERGENCY_FUND_BASE_MONTHS + max(0, dependents - 2))
    recommended = monthly_expenses * months
    gap = max(0.0, recommended - current_savings)
    return EmergencyFundResult(
        recommended_months=months,
        recommended=recommended,
        current_savings=current_savings,
        gap=gap,
    )


@dataclass
class FoirResult:
    total_monthly_emi: float
    monthly_income: float
    ratio: float
    level: str  # "Safe" | "Caution" | "High"


def compute_foir(total_monthly_emi: float, monthly_income: float) -> FoirResult:
    """
    Fixed Obligation to Income Ratio — the threshold Indian banks use to gate
    new loan eligibility.

    Returns:
        FoirResult.level: "Safe" (≤40%), "Caution" (41–55%), "High" (>55%).
    """
    ratio = total_monthly_emi / monthly_income if monthly_income > 0 else 0.0
    if ratio <= FOIR_SAFE_THRESHOLD:
        level = "Safe"
    elif ratio <= FOIR_CAUTION_THRESHOLD:
        level = "Caution"
    else:
        level = "High"
    return FoirResult(
        total_monthly_emi=total_monthly_emi,
        monthly_income=monthly_income,
        ratio=ratio,
        level=level,
    )
