"""
demo_data.py
────────────
Polished, pre-written answers for the handful of "showcase" questions, used
when the app runs WITHOUT a Groq API key (so a portfolio reviewer sees a clean
result immediately). Retrieval still runs for real — only the LLM synthesis
step is substituted — so the source excerpts shown alongside these answers are
the genuine retrieved passages.

⚠️ INTEGRITY RULE: every figure below must match the indexed source PDFs. These
are verified against the actual FY2024 annual reports during the offline build
(see scripts/build_index.py → --verify). Do not add a claim you cannot point to
on a real page. When in doubt, keep the answer qualitative.
"""

from __future__ import annotations

# Each entry: keyword triggers (all-lowercase, ANY match wins after the primary
# keyword) → a polished answer string. Ordered most-specific first.
_DEMO_ANSWERS: list[dict] = [
    {
        "keywords": ["gnpa", "npa", "non-performing", "bad loan", "asset quality"],
        "must_include": ["hdfc"],
        "answer": (
            "HDFC Bank reported strong asset quality for FY2024. Its gross "
            "non-performing assets (GNPA) ratio stood at 1.24% of gross advances "
            "(versus 1.12% a year earlier), with net NPAs at 0.33% (versus "
            "0.27%) — among the lowest in the Indian banking sector. Net profit "
            "grew 37.9% to ₹60,812 crore, though the year-on-year comparison is "
            "amplified by the amalgamation of HDFC Ltd into the Bank effective "
            "1 July 2023 [HDFC Bank, Annual Report FY2024]."
        ),
    },
    {
        "keywords": ["margin", "operating margin", "ebit"],
        "must_include": ["infosys"],
        "answer": (
            "Infosys reported a consolidated operating margin of 20.7% for "
            "FY2024, down from 21.1% the previous year. The modest decline came "
            "against a challenging demand environment, with operational "
            "efficiencies under its cost-optimisation programme partially "
            "offsetting the pressure [Infosys, Annual Report FY2024]."
        ),
    },
    {
        "keywords": ["revenue", "geography", "geographic", "geographical", "segment"],
        "must_include": ["infosys"],
        "answer": (
            "For FY2024 Infosys reported its revenue by geography as North "
            "America 60.1%, Europe 27.6%, Rest of the World 9.8%, and India 2.5% "
            "— North America remaining by far its largest market [Infosys, "
            "Annual Report FY2024]."
        ),
    },
    {
        "keywords": ["dividend"],
        "must_include": ["hdfc"],
        "answer": (
            "For FY2024 HDFC Bank's Board recommended a dividend on its equity "
            "shares, subject to shareholder approval at the AGM. The exact "
            "per-share amount and record date are stated in the report's "
            "Directors' Report / dividend section [HDFC Bank, Annual Report "
            "FY2024]. (Enable a Groq API key for the exact figure from the "
            "retrieved excerpt.)"
        ),
    },
    {
        "keywords": ["risk", "risk factor", "risks"],
        "answer": (
            "Both companies devote a dedicated section to risk management. "
            "Infosys highlights risks including client concentration, "
            "cybersecurity, talent supply, and macroeconomic/geopolitical "
            "uncertainty affecting technology spending. HDFC Bank, as a lender, "
            "emphasises credit risk, market and liquidity risk, operational and "
            "technology risk, and regulatory/compliance risk [Infosys & HDFC "
            "Bank, Annual Reports FY2024]."
        ),
    },
]


def match_demo_answer(query: str) -> str | None:
    """Return a pre-written answer if the query clearly matches a showcase
    topic, else None (caller then falls back to an extractive response)."""
    q = query.lower()
    for entry in _DEMO_ANSWERS:
        if not any(k in q for k in entry["keywords"]):
            continue
        # If the entry is company-specific, require that company be named
        # (prevents "Infosys margin" matching an HDFC-only canned answer).
        must = entry.get("must_include")
        if must and not any(m in q for m in must):
            continue
        return entry["answer"]
    return None


# The questions surfaced as clickable examples in the UI. Kept here so the demo
# answers and the suggested questions never drift apart.
EXAMPLE_QUESTIONS = [
    "What was HDFC Bank's GNPA ratio in FY24?",
    "How did Infosys explain its operating margin in FY24?",
    "What is Infosys's revenue split by geography?",
    "Compare the key risk factors disclosed by both companies.",
    "What dividend did HDFC Bank declare for FY24?",
]
