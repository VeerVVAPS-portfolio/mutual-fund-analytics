"""
allocation_engine.py
Calls the Grok API (OpenAI-compatible) and returns a parsed allocation dict.
Falls back to a hardcoded demo allocation when no API key is available.
"""

from __future__ import annotations

import json
import os

from prompts import SYSTEM_PROMPT, build_user_message
from risk_profiler import get_base_allocation

# ── Demo allocation (used when no API key is provided) ───────────────────────

def _demo_allocation(risk_label: str, monthly_income: int | None) -> dict:
    """Return a realistic hardcoded allocation for portfolio demo purposes."""
    base = get_base_allocation(risk_label)
    sip = round((monthly_income * 0.15) / 500) * 500 if monthly_income else None

    reasoning_map = {
        "Conservative": {
            "equity": "A small equity allocation provides inflation-beating growth potential while keeping risk low. At this risk level, stability and capital protection are the priority.",
            "debt": "A large debt allocation — spread across PPF, FDs, and short-duration debt funds — ensures steady returns with minimal volatility.",
            "gold": "Gold serves as a safe-haven asset and performs well during periods of market stress, making it a valuable addition for conservative investors.",
            "alternatives": "A small alternatives allocation via Sovereign Gold Bonds or liquid REITs adds a layer of diversification without significant risk.",
        },
        "Moderate Conservative": {
            "equity": "A moderate equity allocation through Large Cap and hybrid funds provides growth potential while keeping downside risk manageable over your horizon.",
            "debt": "Debt funds and bonds form the core, providing stability and regular income to balance the equity exposure.",
            "gold": "Gold acts as a hedge against inflation and currency risk — important in India's macroeconomic environment.",
            "alternatives": "A small international or REIT allocation improves diversification beyond domestic markets.",
        },
        "Moderate Aggressive": {
            "equity": "Given your horizon and risk appetite, a higher equity allocation is suitable. A mix of Large Cap, Flexi Cap, and some Mid Cap funds balances growth with reasonable risk.",
            "debt": "Debt provides a stability buffer — when equity markets correct, this portion protects your overall portfolio from steep drawdowns.",
            "gold": "Gold's low correlation with equities improves your portfolio's risk-adjusted returns over long periods.",
            "alternatives": "Alternatives such as REITs or international funds provide geographic and sectoral diversification beyond Indian equities.",
        },
        "Aggressive": {
            "equity": "With a long horizon and high risk tolerance, a dominant equity allocation maximises compounding potential. Diversify across market caps — Large, Mid, and Small Cap.",
            "debt": "Even aggressive portfolios benefit from a small debt cushion to rebalance during market downturns and reduce overall volatility.",
            "gold": "A small gold allocation of 5–10% has historically improved Sharpe ratio even in aggressive portfolios due to its low correlation with equity.",
            "alternatives": "International funds and InvITs provide diversification benefits that are increasingly important as Indian markets mature.",
        },
    }

    return {
        "risk_profile_confirmed": risk_label,
        "allocation": base,
        "reasoning": reasoning_map[risk_label],
        "monthly_sip_suggestion": sip,
        "key_considerations": [
            "Build an emergency fund covering 6 months of expenses before investing.",
            "Start a SIP — investing a fixed amount monthly reduces timing risk (rupee cost averaging).",
            "Review your allocation annually or whenever your life situation changes significantly.",
            "Keep investment costs low — choose direct plans over regular plans for mutual funds.",
        ],
        "_demo": True,
    }


# ── Live Grok API call ────────────────────────────────────────────────────────

def get_allocation(
    age: str,
    horizon: str,
    goal: str,
    reaction: str,
    debt: str,
    risk_score: int,
    risk_label: str,
    monthly_income: int | None,
    api_key: str | None,
) -> dict:
    """
    Returns a parsed allocation dict.
    If api_key is None or empty, returns demo allocation instead of crashing.
    """
    if not api_key:
        return _demo_allocation(risk_label, monthly_income)

    try:
        from openai import OpenAI

        client = OpenAI(api_key=api_key, base_url="https://api.x.ai/v1")

        user_message = build_user_message(
            age=age,
            horizon=horizon,
            goal=goal,
            reaction=reaction,
            debt=debt,
            risk_score=risk_score,
            risk_label=risk_label,
            monthly_income=monthly_income,
        )

        response = client.chat.completions.create(
            model="grok-3-mini",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_message},
            ],
            response_format={"type": "json_object"},
            temperature=0.3,
        )

        raw = response.choices[0].message.content
        result = json.loads(raw)

        # Validate that allocation sums to 100 (correct silently if off by 1 due to rounding)
        alloc = result.get("allocation", {})
        total = sum(alloc.values())
        if total != 100 and alloc:
            diff = 100 - total
            alloc["debt"] = alloc.get("debt", 0) + diff

        result["_demo"] = False
        return result

    except Exception as e:
        # On any API error, fall back to demo rather than crashing the app
        fallback = _demo_allocation(risk_label, monthly_income)
        fallback["_error"] = str(e)
        return fallback
