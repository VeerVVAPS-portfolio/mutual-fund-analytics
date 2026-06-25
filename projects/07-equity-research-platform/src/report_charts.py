"""
Matplotlib chart generation for equity research PDF reports.
Every chart is rendered at 200 DPI and returned as a base64 PNG data URI,
so the HTML that embeds it never depends on a file path staying valid.
"""

from __future__ import annotations

import base64
from io import BytesIO

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker

plt.rcParams["font.family"] = "DejaVu Sans"


def _to_data_uri(fig) -> str:
    buf = BytesIO()
    fig.savefig(buf, format="png", dpi=200, bbox_inches="tight")
    plt.close(fig)
    encoded = base64.b64encode(buf.getvalue()).decode("ascii")
    return f"data:image/png;base64,{encoded}"


def _strip_chart_junk(ax):
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["left"].set_color("#CCCCCC")
    ax.spines["bottom"].set_color("#CCCCCC")
    ax.grid(axis="y", color="#E5E5E5", linewidth=0.7, zorder=0)
    ax.set_axisbelow(True)
    ax.tick_params(colors="#444444", labelsize=9)


def chart_revenue_net_profit(years: list[str], revenue: list[float], net_profit: list[float], colors: dict) -> str:
    fig, ax = plt.subplots(figsize=(7.2, 3.4))
    x = range(len(years))
    width = 0.38
    ax.bar([i - width / 2 for i in x], revenue, width, label="Revenue", color=colors["primary"], zorder=2)
    ax.bar([i + width / 2 for i in x], net_profit, width, label="Net Profit", color=colors["accent"], zorder=2)
    ax.set_xticks(list(x))
    ax.set_xticklabels(years, fontsize=8)
    ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda v, _: f"{v/1000:.0f}k"))
    ax.set_ylabel("INR Crore", fontsize=9, color="#444444")
    ax.legend(frameon=False, fontsize=9, loc="upper left")
    _strip_chart_junk(ax)
    fig.tight_layout()
    return _to_data_uri(fig)


def chart_margin_roce(years: list[str], opm: list[float], roce: list[float], colors: dict) -> str:
    fig, ax = plt.subplots(figsize=(3.5, 2.9))
    ax.plot(years, opm, marker="o", markersize=3.5, color=colors["primary"], label="Operating Margin %", linewidth=1.8, zorder=3)
    ax.plot(years, roce, marker="o", markersize=3.5, color=colors["accent"], label="ROCE %", linewidth=1.8, zorder=3)
    ax.set_ylabel("Percent", fontsize=9, color="#444444")
    ax.legend(frameon=False, fontsize=7.5, loc="lower right")
    ax.set_xticks(range(len(years)))
    ax.set_xticklabels(years, rotation=45, ha="right", fontsize=6.5)
    _strip_chart_junk(ax)
    fig.tight_layout()
    return _to_data_uri(fig)


def chart_fcf(years: list[str], fcf: list[float], colors: dict) -> str:
    fig, ax = plt.subplots(figsize=(3.5, 2.9))
    ax.plot(years, fcf, marker="o", markersize=3.5, color=colors["primary"], linewidth=1.8, zorder=3)
    ax.fill_between(range(len(years)), fcf, color=colors["primary"], alpha=0.12, zorder=1)
    ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda v, _: f"{v/1000:.0f}k"))
    ax.set_ylabel("INR Crore", fontsize=9, color="#444444")
    ax.set_xticks(range(len(years)))
    ax.set_xticklabels(years, rotation=45, ha="right", fontsize=6.5)
    _strip_chart_junk(ax)
    fig.tight_layout()
    return _to_data_uri(fig)


def chart_price_vs_fair_value(current_price: float, fair_value: float, upside_pct: float, colors: dict) -> str:
    fig, ax = plt.subplots(figsize=(3.5, 2.9))
    bars = ax.bar(["Current\nPrice", "DCF Fair\nValue"], [current_price, fair_value],
                   color=["#9AA5B1", colors["primary"]], width=0.55, zorder=2)
    for bar, val in zip(bars, [current_price, fair_value]):
        ax.annotate(f"{val:,.0f}", (bar.get_x() + bar.get_width() / 2, val),
                    textcoords="offset points", xytext=(0, 4), ha="center", fontsize=9, fontweight="bold")
    upside_color = colors["positive"] if upside_pct >= 0 else colors["negative"]
    sign = "+" if upside_pct >= 0 else ""
    ax.annotate(f"{sign}{upside_pct:.1f}%\nupside" if upside_pct >= 0 else f"{sign}{upside_pct:.1f}%\ndownside",
                (1, fair_value), textcoords="offset points", xytext=(28, 0), ha="center",
                fontsize=9, fontweight="bold", color=upside_color)
    _strip_chart_junk(ax)
    fig.tight_layout()
    return _to_data_uri(fig)


def chart_dcf_bridge(labels: list[str], values: list[float], bar_kinds: list[str], colors: dict) -> str:
    """bar_kinds: one of 'base', 'subtract', 'add', 'final' per bar, controlling color and base/floating placement."""
    fig, ax = plt.subplots(figsize=(7.2, 3.6))
    cumulative = 0
    for i, (label, val, kind) in enumerate(zip(labels, values, bar_kinds)):
        if kind in ("base", "final"):
            bottom = 0
            height = val
            cumulative = val
        else:
            height = val
            if val >= 0:
                bottom = cumulative
                cumulative += val
            else:
                cumulative += val
                bottom = cumulative
        color = {
            "base": colors["primary"],
            "subtract": colors["negative"],
            "add": colors["positive"],
            "final": colors["accent"],
        }[kind]
        ax.bar(label, height, bottom=bottom, color=color, width=0.55, zorder=2)
        label_val = val if kind != "final" else val
        ax.annotate(f"{label_val:,.0f}" if kind == "base" or kind == "final" else f"{'+' if val >= 0 else ''}{val:,.0f}",
                    (i, bottom + height if height >= 0 else bottom), textcoords="offset points",
                    xytext=(0, 4), ha="center", fontsize=8, fontweight="bold")
    ax.set_xticks(range(len(labels)))
    ax.set_xticklabels(labels, fontsize=8)
    ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda v, _: f"{v/1000:.0f}k"))
    _strip_chart_junk(ax)
    fig.tight_layout()
    return _to_data_uri(fig)
