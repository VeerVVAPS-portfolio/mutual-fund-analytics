"""
formatting.py — Indian-style currency formatting (lakh/crore grouping),
shared by the dashboard and the Excel report.
"""

from __future__ import annotations


def _indian_grouped_int(n: int) -> str:
    """Group digits as 'X,XX,XX,XXX' (last 3, then pairs) instead of Western 'X,XXX,XXX'."""
    sign = "-" if n < 0 else ""
    s = str(abs(n))
    if len(s) <= 3:
        return sign + s
    last3 = s[-3:]
    rest = s[:-3]
    parts = []
    while len(rest) > 2:
        parts.insert(0, rest[-2:])
        rest = rest[:-2]
    if rest:
        parts.insert(0, rest)
    return sign + ",".join(parts) + "," + last3


def format_inr(value: float) -> str:
    """₹55,18,063 style — full Indian digit grouping, no abbreviation."""
    grouped = _indian_grouped_int(round(value))
    sign, digits = ("-", grouped[1:]) if grouped.startswith("-") else ("", grouped)
    return f"{sign}₹{digits}"


def format_inr_compact(value: float) -> str:
    """₹55.18 L / ₹1.51 Cr for large values; falls back to format_inr below 1 lakh."""
    abs_value = abs(value)
    sign = "-" if value < 0 else ""
    if abs_value >= 1_00_00_000:
        return f"{sign}₹{abs_value / 1_00_00_000:.2f} Cr"
    if abs_value >= 1_00_000:
        return f"{sign}₹{abs_value / 1_00_000:.2f} L"
    return format_inr(value)
