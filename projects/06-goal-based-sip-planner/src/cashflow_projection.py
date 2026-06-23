"""
cashflow_projection.py — multi-year salary/expense affordability check.

Generalizes the original Excel's "Projection" sheet: instead of assuming
the required SIPs are affordable, this projects disposable income
year-over-year and flags any year where total required SIPs exceed it.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class ProjectionYear:
    year_index: int
    salary: float
    expenses: float
    fixed_obligations: float
    disposable_income: float
    total_sip_outflow: float
    surplus_or_deficit: float
    is_shortfall: bool


def project_cashflow(
    starting_salary: float,
    salary_hike_pct: float,
    starting_expenses: float,
    expense_inflation_pct: float,
    fixed_obligations: float,
    total_monthly_sip: float,
    horizon_years: int,
) -> list[ProjectionYear]:
    """
    Year-by-year disposable income vs. total required SIP outflow.
    Salary and expenses grow at their respective annual rates; fixed
    obligations (EMI etc.) are held constant, matching the original model.
    """
    rows = []
    salary = starting_salary
    expenses = starting_expenses
    annual_sip = total_monthly_sip * 12

    for year in range(horizon_years):
        if year > 0:
            salary *= (1 + salary_hike_pct)
            expenses *= (1 + expense_inflation_pct)

        disposable = salary - expenses - fixed_obligations
        surplus = disposable - annual_sip

        rows.append(ProjectionYear(
            year_index=year,
            salary=salary,
            expenses=expenses,
            fixed_obligations=fixed_obligations,
            disposable_income=disposable,
            total_sip_outflow=annual_sip,
            surplus_or_deficit=surplus,
            is_shortfall=surplus < 0,
        ))

    return rows
