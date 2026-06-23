"""
goal_calculator.py — core goal-based SIP math.

Every goal is solved, not guessed: given a future value target, the
required monthly SIP is derived directly from the annuity formula (fixed
SIP) or from a month-by-month contribution simulation (step-up SIP).
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class GoalResult:
    future_value_required: float
    monthly_sip: float
    total_invested: float
    wealth_gained: float
    schedule: list[dict]  # one row per year: {"year", "contribution", "balance"}


def future_value_required(present_value: float, inflation_rate: float, years: float) -> float:
    """Inflation-adjust today's cost of a goal to its value at the goal date."""
    return present_value * (1 + inflation_rate) ** years


def required_fixed_sip(future_value: float, annual_return: float, years: float) -> float:
    """
    Solve PMT in the future-value-of-an-annuity-due formula:
        FV = PMT * ((1+r)^n - 1) * (1+r) / r
    where r is the monthly return and n is the number of months.
    Annuity-due (not ordinary annuity) because SIPs in India are typically
    debited at the start of the month.
    """
    n = round(years * 12)
    r = annual_return / 12
    if r == 0:
        return future_value / n
    growth = ((1 + r) ** n - 1) * (1 + r) / r
    return future_value / growth


def _stepup_future_value(monthly_sip_year1: float, annual_return: float, years: float, step_up_pct: float) -> float:
    """
    Simulate month-by-month: the SIP amount is constant within a year and
    increases by step_up_pct at each year boundary. Each contribution
    compounds monthly at annual_return/12 until the goal date.
    """
    n_months = round(years * 12)
    r = annual_return / 12
    total = 0.0
    for m in range(1, n_months + 1):
        year_index = (m - 1) // 12
        contribution = monthly_sip_year1 * (1 + step_up_pct) ** year_index
        months_to_grow = n_months - m
        total += contribution * (1 + r) ** months_to_grow
    return total


def required_stepup_sip(future_value: float, annual_return: float, years: float, step_up_pct: float) -> float:
    """
    Future value is linear in the starting SIP amount, so solve by running
    the simulation once with a unit SIP (₹1/month in year 1) and scaling.
    """
    fv_per_unit = _stepup_future_value(1.0, annual_return, years, step_up_pct)
    return future_value / fv_per_unit


def build_schedule_fixed(monthly_sip: float, annual_return: float, years: float) -> list[dict]:
    """Year-by-year contribution and running balance for a flat SIP."""
    n_months = round(years * 12)
    r = annual_return / 12
    balance = 0.0
    schedule = []
    for year in range(1, round(years) + 1):
        year_contribution = 0.0
        for _ in range(12):
            balance = (balance + monthly_sip) * (1 + r)
            year_contribution += monthly_sip
        schedule.append({"year": year, "contribution": year_contribution, "balance": balance})
    return schedule


def build_schedule_stepup(monthly_sip_year1: float, annual_return: float, years: float, step_up_pct: float) -> list[dict]:
    """Year-by-year contribution and running balance for a step-up SIP."""
    r = annual_return / 12
    balance = 0.0
    schedule = []
    for year in range(1, round(years) + 1):
        sip_this_year = monthly_sip_year1 * (1 + step_up_pct) ** (year - 1)
        year_contribution = 0.0
        for _ in range(12):
            balance = (balance + sip_this_year) * (1 + r)
            year_contribution += sip_this_year
        schedule.append({"year": year, "contribution": year_contribution, "balance": balance})
    return schedule


def solve_goal(
    present_value: float,
    inflation_rate: float,
    years: float,
    annual_return: float,
    target_is_future_value: bool = False,
    step_up_pct: float = 0.0,
) -> GoalResult:
    """
    Solve a single goal end-to-end. If target_is_future_value is True,
    present_value is already the future-date target and inflation is ignored.
    """
    fv_required = present_value if target_is_future_value else future_value_required(
        present_value, inflation_rate, years
    )

    if step_up_pct > 0:
        sip = required_stepup_sip(fv_required, annual_return, years, step_up_pct)
        schedule = build_schedule_stepup(sip, annual_return, years, step_up_pct)
    else:
        sip = required_fixed_sip(fv_required, annual_return, years)
        schedule = build_schedule_fixed(sip, annual_return, years)

    total_invested = sum(row["contribution"] for row in schedule)
    final_balance = schedule[-1]["balance"] if schedule else 0.0

    return GoalResult(
        future_value_required=fv_required,
        monthly_sip=sip,
        total_invested=total_invested,
        wealth_gained=final_balance - total_invested,
        schedule=schedule,
    )
