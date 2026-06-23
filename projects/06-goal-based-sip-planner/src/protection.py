"""
protection.py — insurance adequacy and debt-obligation math.

Methodology is deliberately sourced from standard financial-planning
practice rather than invented:
  - Life cover: DIME-style needs-based method (Debt + Income replacement +
    goals, in place of Mortgage/Education since those already show up as
    goals or loans in this app) minus existing cover.
  - Health cover: Indian city-tier sum-insured benchmarks, scaled by family size.
  - Emergency fund: months-of-expenses guidance, scaled by dependents.
  - FOIR: the ratio Indian banks use to gate loan eligibility.
"""

from __future__ import annotations

from dataclasses import dataclass, field

# Health insurance: recommended sum insured by city tier, for an individual
# and for a family of 4 (commonly cited Indian benchmarks). Family sizes in
# between are interpolated rather than handing a solo person the full family
# figure — a single person doesn't need the same floater as a family of 4.
HEALTH_COVER_BY_TIER = {
    "Metro / Tier-1": 30_00_000,
    "Tier-2": 20_00_000,
    "Tier-3": 12_00_000,
}
HEALTH_COVER_INDIVIDUAL_BY_TIER = {
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
    Standard loan amortization formula, solved for outstanding principal
    given the EMI, rate, and months remaining: P = EMI * [1-(1+r)^-n] / r.
    Lets us infer "how much debt is left" without asking for it directly.
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
    DIME-style need: outstanding debt + lump-sum equivalent of every goal +
    income replacement for dependents, minus what's already covered.

    Each goal's "lump-sum equivalent" is the amount that, invested today at
    the same return the goal already assumes, reaches the same future-value
    target without further contributions: future_value_required / (1+r)^years.
    This is not the goal's monthly-SIP present value (a different inflation
    rate may apply) — it's the amount a lump-sum insurance payout would need
    to grow at the *investment* return to still hit the goal.
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

    # With no dependents there's no one whose income needs replacing — cover
    # just debts and goals. Otherwise scale with how many people rely on the income.
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


def recommended_health_cover(dependents: int, city_tier: str, current_cover: float) -> HealthCoverResult:
    family_size = 1 + dependents
    individual = HEALTH_COVER_INDIVIDUAL_BY_TIER.get(city_tier, HEALTH_COVER_INDIVIDUAL_BY_TIER["Tier-2"])
    family_base = HEALTH_COVER_BY_TIER.get(city_tier, HEALTH_COVER_BY_TIER["Tier-2"])

    if family_size >= HEALTH_COVER_BASE_FAMILY_SIZE:
        extra_members = family_size - HEALTH_COVER_BASE_FAMILY_SIZE
        recommended = family_base + extra_members * HEALTH_COVER_PER_EXTRA_DEPENDENT
    else:
        # Interpolate between the solo-individual figure and the family-of-4
        # benchmark — a single person shouldn't be handed the full family cover.
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


def recommended_emergency_fund(monthly_expenses: float, dependents: int, current_savings: float) -> EmergencyFundResult:
    months = min(EMERGENCY_FUND_MAX_MONTHS, EMERGENCY_FUND_BASE_MONTHS + max(0, dependents - 2))
    recommended = monthly_expenses * months
    gap = max(0.0, recommended - current_savings)
    return EmergencyFundResult(
        recommended_months=months, recommended=recommended, current_savings=current_savings, gap=gap,
    )


@dataclass
class FoirResult:
    total_monthly_emi: float
    monthly_income: float
    ratio: float
    level: str  # "Safe" | "Caution" | "High"


def compute_foir(total_monthly_emi: float, monthly_income: float) -> FoirResult:
    ratio = total_monthly_emi / monthly_income if monthly_income > 0 else 0.0
    if ratio <= FOIR_SAFE_THRESHOLD:
        level = "Safe"
    elif ratio <= FOIR_CAUTION_THRESHOLD:
        level = "Caution"
    else:
        level = "High"
    return FoirResult(total_monthly_emi=total_monthly_emi, monthly_income=monthly_income, ratio=ratio, level=level)
