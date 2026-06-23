"""
funding_sequencer.py — when income can't fund every goal's SIP starting today,
builds a priority-ordered staggered start plan: which goal gets 100% of
disposable income first, when the next goal's SIP can start, and what that
goal's SIP becomes once recomputed for its now-shorter remaining horizon.
"""

from __future__ import annotations

from dataclasses import dataclass

from cashflow_projection import project_cashflow
from goal_calculator import required_fixed_sip, required_stepup_sip

PRIORITY_RANK = {"Must-have": 0, "Good-to-have": 1, "Dream goal": 2}


@dataclass
class StaggeredGoal:
    name: str
    category: str
    priority: str
    start_year: int | None              # None if never started within the horizon
    monthly_sip_at_start: float | None
    original_monthly_sip: float
    years_remaining_at_start: float | None
    at_risk: bool


def _recompute_sip(g: dict, years_remaining: float) -> float:
    """Same future_value_required, but solved for the now-shorter remaining horizon."""
    future_value = g["result"].future_value_required
    if g["step_up"] > 0:
        return required_stepup_sip(future_value, g["return"], years_remaining, g["step_up"])
    return required_fixed_sip(future_value, g["return"], years_remaining)


def build_staggered_plan(results: list[dict], income_inputs: dict) -> list[StaggeredGoal]:
    """
    results: the same enriched goal list used by the dashboard (each dict has
        name/category/priority/years/return/step_up/result with .future_value_required).
    income_inputs: dict with salary, hike, expenses, expense_inflation,
        fixed_obligations, horizon (same shape as st.session_state.income_inputs).
    """
    ordered = sorted(
        results,
        key=lambda g: (PRIORITY_RANK.get(g.get("priority", "Dream goal"), 99), g["years"]),
    )

    horizon = max(income_inputs["horizon"], max((g["years"] for g in ordered), default=1))
    projection = project_cashflow(
        income_inputs["salary"], income_inputs["hike"], income_inputs["expenses"],
        income_inputs["expense_inflation"], income_inputs["fixed_obligations"],
        total_monthly_sip=0, horizon_years=int(horizon) + 1,
    )
    monthly_disposable_by_year = [p.disposable_income / 12 for p in projection]

    plan = {
        g["name"]: StaggeredGoal(
            name=g["name"], category=g.get("category", "Other"), priority=g.get("priority", "Dream goal"),
            start_year=None, monthly_sip_at_start=None, original_monthly_sip=g["result"].monthly_sip,
            years_remaining_at_start=None, at_risk=False,
        )
        for g in ordered
    }

    active: dict[str, dict] = {}  # name -> {sip_at_start, start_year, step_up}

    for year, monthly_disposable in enumerate(monthly_disposable_by_year):
        committed = sum(
            info["sip_at_start"] * (1 + info["step_up"]) ** (year - info["start_year"])
            for info in active.values()
        )
        available = monthly_disposable - committed

        for g in ordered:
            entry = plan[g["name"]]
            if entry.start_year is not None or entry.at_risk:
                continue  # already started, or already given up on

            years_remaining = g["years"] - year
            if years_remaining <= 0:
                entry.at_risk = True
                continue  # deadline passed before funding could start — move on to the next goal this year

            recomputed_sip = _recompute_sip(g, years_remaining)
            if available >= recomputed_sip:
                entry.start_year = year
                entry.monthly_sip_at_start = recomputed_sip
                entry.years_remaining_at_start = years_remaining
                active[g["name"]] = {"sip_at_start": recomputed_sip, "start_year": year, "step_up": g["step_up"]}
                available -= recomputed_sip
            else:
                break  # strict waterfall: don't skip ahead to fund a lower-priority goal this year

    for entry in plan.values():
        if entry.start_year is None:
            entry.at_risk = True

    return [plan[g["name"]] for g in ordered]
