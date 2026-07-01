"""
shared/cashflow_projection.py — multi-year salary/expense affordability check.

Adapted from projects/06-goal-based-sip-planner/src/cashflow_projection.py.
CHANGES FROM ORIGINAL:
  - Zero changes to logic — identical formulas.
  - Docstrings expanded to clarify the "Advanced wealth check" role in TrueSIP
    (this powers the advanced expander in the Results step).
  - ProjectionYear and project_cashflow() exported at module level.

Usage in TrueSIP: the streamlit-ux-builder fills the "Advanced wealth check"
expander (step 3 Results) by calling project_cashflow() with income/expense
data from session_state['income'] and the total_monthly_sip from planning_engine.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class ProjectionYear:
    """One year of the salary/SIP affordability projection.

    Attributes:
        year_index:          0-based index (year_index=0 is the current year).
        salary:              Annual salary for this year (₹).
        expenses:            Annual living expenses for this year (₹).
        fixed_obligations:   Fixed annual outflows held constant (EMIs, etc.) (₹).
        disposable_income:   salary − expenses − fixed_obligations (₹).
        total_sip_outflow:   Annual SIP outflow = monthly_sip × 12 (₹).
        surplus_or_deficit:  disposable_income − total_sip_outflow (₹). Negative = shortfall.
        is_shortfall:        True when surplus_or_deficit < 0.
    """
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
    obligations (EMIs etc.) are held constant, matching the original Project 6 model.

    Args:
        starting_salary:       Current annual salary (₹/yr).
        salary_hike_pct:       Expected annual raise as a decimal (e.g. 0.08 for 8%).
        starting_expenses:     Current annual living expenses (₹/yr).
        expense_inflation_pct: Lifestyle inflation rate as a decimal (e.g. 0.06).
        fixed_obligations:     Fixed annual outflows that don't inflate (EMIs, rent, etc.) (₹/yr).
        total_monthly_sip:     Sum of all goal SIPs in ₹/month (from planning_engine output).
        horizon_years:         Number of years to project.

    Returns:
        List of ProjectionYear objects, one per year (length = horizon_years).
    """
    rows: list[ProjectionYear] = []
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
