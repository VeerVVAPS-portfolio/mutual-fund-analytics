"""
advisory.py — turns the staggered funding plan into a consultant-style
written note: a headline verdict, reasoning paragraphs (including the
quantified cost of deferring a goal), and explicit risk flags.

Deliberately rule-based, not LLM-generated: every sentence traces back to a
specific computed number, so the advice is exactly as auditable as the math
that produced it.
"""

from __future__ import annotations

from formatting import format_inr_compact
from funding_sequencer import StaggeredGoal


def build_advisory_note(staggered_plan: list[StaggeredGoal], income_inputs: dict) -> dict:
    started_now = [p for p in staggered_plan if p.start_year == 0 and not p.at_risk]
    deferred = [p for p in staggered_plan if p.start_year is not None and p.start_year > 0 and not p.at_risk]
    at_risk = [p for p in staggered_plan if p.at_risk]

    paragraphs: list[str] = []

    if not deferred and not at_risk:
        headline = "Your income comfortably funds every goal from today — no sequencing trade-offs needed."
        paragraphs.append(
            "With your current income and expense assumptions, every goal's SIP can start immediately "
            "without compromising on any of them. The main risk now isn't affordability — it's discipline. "
            "Automate each SIP and revisit this plan once a year or after any meaningful income change."
        )
    else:
        n_total = len(staggered_plan)
        headline = (
            f"Your income funds {len(started_now)} of {n_total} goal(s) immediately — "
            "here's how I'd sequence the rest."
        )
        if started_now:
            names = ", ".join(p.name for p in started_now)
            paragraphs.append(
                f"Start with {names} right away — these are your highest-priority, most time-sensitive "
                "commitments, and every year a long-horizon goal is delayed compounds against you."
            )
        for p in deferred:
            delay_pct = (p.monthly_sip_at_start / p.original_monthly_sip - 1) * 100
            paragraphs.append(
                f"{p.name} waits until Year {p.start_year}, once your higher-priority goals are fully "
                f"funded out of rising income. Waiting has a price: the required SIP rises from "
                f"{format_inr_compact(p.original_monthly_sip)} to {format_inr_compact(p.monthly_sip_at_start)}/month "
                f"(+{delay_pct:.0f}%) because there's less time left to compound. That's worth knowing "
                "before you commit to this sequence rather than discovering it later."
            )
        for p in at_risk:
            paragraphs.append(
                f"{p.name} doesn't fit anywhere in this plan at your current income and assumptions. "
                "To make it work you'd need one of: a longer timeline, a smaller target, higher income, "
                "or accepting it ranks below your other goals entirely. I wouldn't recommend leaving it "
                "as-is — an unfunded goal sitting quietly on a plan tends to become a missed goal."
            )

    risk_notes: list[str] = []
    if income_inputs["hike"] <= income_inputs["expense_inflation"]:
        risk_notes.append(
            "Your assumed salary growth doesn't outpace your assumed expense growth — disposable income "
            "won't actually improve over time under these numbers, which makes any deferred goal above "
            "fragile. Worth stress-testing with a more conservative expense growth assumption."
        )

    return {"headline": headline, "paragraphs": paragraphs, "risk_notes": risk_notes}
