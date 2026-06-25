"""
Renders an approved equity-research Markdown draft + its source JSON artifacts
into a brand-themed PDF (HTML+CSS via WeasyPrint, matplotlib charts at 200 DPI).

Usage: python src/build_report_pdf.py <TICKER>
Reads from data/<TICKER>/, writes data/<TICKER>/<TICKER>_Equity_Research_Report.pdf

Brand colors are looked up from BRAND_COLORS below. A new ticker needs its
primary/accent researched (logo / brand guidelines) and added here before
running — this script does not do the web research itself.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from report_charts import (
    chart_dcf_bridge,
    chart_fcf,
    chart_margin_roce,
    chart_price_vs_fair_value,
    chart_revenue_net_profit,
)

SEMANTIC = {"positive": "#1F7A5A", "negative": "#9E2B25"}

# Researched from each company's logo/brand guidelines. Fallback used if absent.
BRAND_COLORS = {
    "INFY": {
        "primary": "#14354F",  # darkened Infosys Mediterranean Blue (#3781C2) for header/cover contrast
        "accent": "#3781C2",   # Infosys's actual brand blue (Pantone 285C / #3781C2), used as accent
        "source": "Infosys brand blue #3781C2 (Pantone 285C), darkened for primary to keep white text readable on the cover band.",
    },
}
FALLBACK_COLORS = {"primary": "#0B2545", "accent": "#C9A227", "source": "fallback (brand unclear)"}


def fmt_cr(v: float) -> str:
    """Indian digit grouping (e.g. 4,28,620 not 428,620) — standard convention for INR figures."""
    n = int(round(v))
    sign = "-" if n < 0 else ""
    s = str(abs(n))
    if len(s) <= 3:
        return sign + s
    last3, rest = s[-3:], s[:-3]
    parts = []
    while len(rest) > 2:
        parts.insert(0, rest[-2:])
        rest = rest[:-2]
    if rest:
        parts.insert(0, rest)
    return sign + ",".join(parts) + "," + last3


def parse_markdown_sections(md_text: str) -> dict:
    sections = {}
    parts = re.split(r"^## \d+\.\s*(.+)$", md_text, flags=re.MULTILINE)
    # parts[0] is preamble before first ##; then alternating [title, body, title, body, ...]
    for i in range(1, len(parts), 2):
        title = parts[i].strip()
        body = parts[i + 1].strip() if i + 1 < len(parts) else ""
        sections[title] = body
    return sections


def parse_risks(risks_body: str) -> list[dict]:
    risks = []
    for line in risks_body.splitlines():
        line = line.strip()
        if not line.startswith("- **"):
            continue
        m = re.match(r"-\s+\*\*(.+?)\s*\(([^)]+)\):\*\*\s*(.+)", line)
        if m:
            title, category, text = m.groups()
            risks.append({"tag": category.split("/")[0].strip().upper(), "title": title.strip(), "text": text.strip()})
    return risks


def markdown_inline_to_html(text: str) -> str:
    text = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", text)
    text = re.sub(r"`(.+?)`", r"<code>\1</code>", text)
    return text


def paragraphs_html(body: str) -> str:
    paras = [p.strip() for p in body.split("\n\n") if p.strip() and not p.strip().startswith("Snapshot at a Glance")]
    return "\n".join(f"<p>{markdown_inline_to_html(p)}</p>" for p in paras)


def build(ticker: str):
    base = Path(__file__).parent.parent / "data" / ticker
    validated = json.loads((base / "validated_financials.json").read_text(encoding="utf-8"))
    valuation = json.loads((base / "valuation.json").read_text(encoding="utf-8"))
    industry = json.loads((base / "industry_notes.json").read_text(encoding="utf-8"))
    draft_md = (base / "report_draft.md").read_text(encoding="utf-8")

    colors = {**BRAND_COLORS.get(ticker, FALLBACK_COLORS), **SEMANTIC}
    company_name = validated.get("company_name", ticker)

    pl = validated["profit_loss"]
    cf = validated["cash_flow"]
    rt = validated["ratios"]
    years_all = list(pl.keys())
    snap = rt["current_snapshot"]

    current_price = snap["Current Price"]
    fair_value = valuation["dcf_valuation"]["implied_share_price_inr"]
    upside_pct = valuation["market_cross_check"]["upside_downside_percent"]
    rating = "BUY" if upside_pct > 15 else ("HOLD" if upside_pct > -10 else "SELL")

    revenue = [pl[y]["revenue"] for y in years_all]
    net_profit = [pl[y]["net_profit"] for y in years_all]
    opm = [pl[y]["opm_percent"] for y in years_all]
    roce = [rt[y]["roce_percent"] for y in years_all]
    fcf = [cf[y]["free_cash_flow"] for y in years_all]
    short_years = [y.replace("Mar 20", "FY") for y in years_all]
    short_years[-1] += "\nTTM" if "warnings" in validated and "TTM" in " ".join(validated["warnings"]) else ""

    revenue_chart = chart_revenue_net_profit(short_years, revenue, net_profit, colors)
    margin_chart = chart_margin_roce(short_years, opm, roce, colors)
    fcf_chart = chart_fcf(short_years, fcf, colors)
    price_chart = chart_price_vs_fair_value(current_price, fair_value, upside_pct, colors)

    dcf = valuation["dcf_valuation"]
    bridge_labels = ["PV Explicit\nFCFF", "PV Terminal\nValue", "Enterprise\nValue", "(-) Debt", "(+) Cash &\nInvest.", "Equity\nValue"]
    bridge_values = [
        dcf["sum_pv_explicit_fcff_inr_cr"],
        dcf["pv_terminal_value_inr_cr"],
        dcf["enterprise_value_inr_cr"],
        -dcf["total_debt_inr_cr"],
        dcf["cash_and_investments_inr_cr"],
        dcf["equity_value_inr_cr"],
    ]
    bridge_kinds = ["base", "add", "final", "subtract", "add", "final"]
    bridge_chart = chart_dcf_bridge(bridge_labels, bridge_values, bridge_kinds, colors)

    sections = parse_markdown_sections(draft_md)
    risks = parse_risks(sections.get("Risks", ""))

    selected_years = [years_all[i] for i in [0, 3, 5, 7, 8, 9, 10, 11] if i < len(years_all)]
    fin_rows = ""
    for metric, key, fmt in [
        ("Revenue (INR Cr)", "revenue", fmt_cr),
        ("Operating Profit (INR Cr)", "operating_profit", fmt_cr),
        ("Operating Margin (%)", "opm_percent", lambda v: f"{v:.0f}"),
        ("Net Profit (INR Cr)", "net_profit", fmt_cr),
        ("EPS (INR)", "eps", lambda v: f"{v:.2f}"),
    ]:
        cells = "".join(f"<td>{fmt(pl[y][key])}</td>" for y in selected_years)
        fin_rows += f"<tr><td class='label'>{metric}</td>{cells}</tr>\n"
    fcf_row_cells = "".join(f"<td>{fmt_cr(cf[y]['free_cash_flow'])}</td>" for y in selected_years)
    fin_rows += f"<tr><td class='label'>Free Cash Flow (INR Cr)</td>{fcf_row_cells}</tr>\n"
    roce_row_cells = "".join(f"<td>{rt[y]['roce_percent']:.0f}</td>" for y in selected_years)
    fin_rows += f"<tr><td class='label'>ROCE (%)</td>{roce_row_cells}</tr>\n"
    fin_header = "".join(f"<th>{y.replace('Mar 20','FY')}</th>" for y in selected_years)

    fcff_rows = "".join(
        f"<tr><td>{p['year']}</td><td>{p['growth_rate_annual']*100:.1f}%</td>"
        f"<td>{fmt_cr(p['fcff_inr_cr'])}</td><td>{p['discount_factor']:.3f}</td><td>{fmt_cr(p['pv_fcff_inr_cr'])}</td></tr>"
        for p in valuation["fcff_projections"]
    )

    ke = valuation["capm_cost_of_equity"]
    cs = valuation["capital_structure"]
    risk_tags_html = "\n".join(
        f"<div class='risk-item'><span class='tag'>{r['tag']}</span> <strong>{r['title']}.</strong> {r['text']}</div>"
        for r in risks
    )

    sources_line = (
        f"Statement basis: Consolidated, INR Crore (per-share in INR). Source: screener.in consolidated financials "
        f"& cited public news. This document is for informational purposes only and is not investment advice."
    )

    html = f"""
<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<style>
:root {{
  --primary: {colors['primary']};
  --accent: {colors['accent']};
  --positive: {colors['positive']};
  --negative: {colors['negative']};
}}
@page {{
  size: A4;
  margin: 18mm 16mm;
  @bottom-left {{ content: "{company_name} ({ticker}) \\2014 Equity Research"; font-size: 7.5pt; color: #666; }}
  @bottom-right {{ content: "Page " counter(page) " of " counter(pages); font-size: 7.5pt; color: #666; }}
}}
@page cover {{
  margin: 0;
  @bottom-left {{ content: none; }}
  @bottom-right {{ content: none; }}
}}
* {{ box-sizing: border-box; }}
body {{ font-family: 'DejaVu Sans', Arial, sans-serif; font-size: 9.5pt; color: #1A1A1A; line-height: 1.45; }}
p {{ text-align: justify; margin: 0 0 8px 0; }}
.cover {{ page: cover; break-after: page; page-break-after: always; }}
.cover-band {{ background: var(--primary); color: #fff; padding: 18mm 16mm 10mm 16mm; }}
.cover-eyebrow {{ font-size: 9pt; letter-spacing: 2px; color: var(--accent); text-transform: uppercase; font-weight: bold; }}
.cover-title {{ font-size: 30pt; font-weight: bold; margin: 6px 0 4px 0; }}
.cover-sub {{ font-size: 11pt; opacity: 0.9; }}
.rating-strip {{ display: flex; margin: 0 16mm; border: 1px solid #ddd; border-top: none; }}
.rating-cell {{ flex: 1; padding: 12px 10px; text-align: center; border-right: 1px solid #ddd; }}
.rating-cell:last-child {{ border-right: none; }}
.rating-label {{ font-size: 7.5pt; letter-spacing: 1px; color: #777; text-transform: uppercase; }}
.rating-value {{ font-size: 16pt; font-weight: bold; color: var(--primary); margin-top: 3px; }}
.rating-value.buy {{ color: var(--positive); }}
.rating-value.upside {{ color: var(--positive); }}
.metrics-table {{ margin: 14px 16mm 0 16mm; width: calc(100% - 32mm); border-collapse: collapse; }}
.metrics-table td {{ padding: 5px 4px; border-bottom: 1px solid #eee; font-size: 9pt; }}
.metrics-table td:first-child {{ font-weight: bold; color: var(--primary); }}
.metrics-table td:last-child {{ text-align: right; }}
.callout {{ margin: 14px 16mm 0 16mm; background: #F4F5F7; border-left: 3px solid var(--accent); padding: 10px 14px; font-size: 9pt; }}
.cover-footer {{ position: absolute; bottom: 0; left: 0; right: 0; background: var(--primary); color: #cdd6e0; padding: 8px 16mm; font-size: 7pt; }}
h2 {{ color: var(--primary); font-size: 14pt; border-bottom: 2.5px solid var(--accent); padding-bottom: 4px; margin: 18px 0 10px 0; break-after: avoid; page-break-after: avoid; }}
table.data, .chart-pair, img.full {{ break-inside: avoid; page-break-inside: avoid; }}
h2 .num {{ color: var(--accent); }}
h3 {{ color: var(--primary); font-size: 11pt; margin: 12px 0 6px 0; }}
table.data {{ width: 100%; border-collapse: collapse; margin: 8px 0; font-size: 8pt; }}
table.data th {{ background: var(--primary); color: #fff; text-align: right; padding: 5px 6px; }}
table.data th:first-child, table.data td.label {{ text-align: left; }}
table.data td {{ padding: 5px 6px; text-align: right; border-bottom: 1px solid #eee; }}
table.data tr:nth-child(even) {{ background: #F7F8FA; }}
.snapshot-row {{ display: table; width: 100%; table-layout: fixed; }}
.snapshot-table {{ display: table-cell; width: 58%; vertical-align: top; padding-right: 12px; }}
.snapshot-row .chart-box {{ display: table-cell; width: 42%; vertical-align: top; text-align: center; }}
.chart-box img {{ width: 100%; }}
img.full {{ width: 100%; }}
.chart-pair {{ display: table; width: 100%; table-layout: fixed; }}
.chart-pair .chart-box {{ display: table-cell; width: 50%; vertical-align: top; text-align: center; padding: 0 5px; }}
.chart-pair > table.data {{ display: table-cell; width: 50%; vertical-align: top; padding: 0 5px; }}
.risk-item {{ background: #F4F5F7; border-left: 3px solid var(--accent); padding: 8px 12px; margin-bottom: 7px; font-size: 9pt; }}
.tag {{ display: inline-block; background: var(--primary); color: #fff; font-size: 6.5pt; letter-spacing: 0.5px; padding: 2px 6px; border-radius: 3px; margin-right: 4px; }}
.disclaimer {{ font-size: 7.5pt; color: #555; border-top: 1px solid #ddd; padding-top: 8px; margin-top: 16px; }}
</style>
</head>
<body>

<div class="cover">
  <div class="cover-band">
    <div class="cover-eyebrow">Equity Research &middot; Initiating Coverage</div>
    <div class="cover-title">{company_name}</div>
    <div class="cover-sub">{ticker} &nbsp;|&nbsp; IT Services &mdash; Consolidated</div>
  </div>
  <div class="rating-strip">
    <div class="rating-cell"><div class="rating-label">Rating</div><div class="rating-value buy">{rating}</div></div>
    <div class="rating-cell"><div class="rating-label">Current Price</div><div class="rating-value">&#8377;{fmt_cr(current_price)}</div></div>
    <div class="rating-cell"><div class="rating-label">Fair Value (DCF)</div><div class="rating-value">&#8377;{fmt_cr(fair_value)}</div></div>
    <div class="rating-cell"><div class="rating-label">Upside</div><div class="rating-value upside">+{upside_pct:.1f}%</div></div>
  </div>
  <table class="metrics-table">
    <tr><td>Market Capitalisation</td><td>&#8377;{fmt_cr(snap['Market Cap'])} Cr</td></tr>
    <tr><td>52-Week High</td><td>&#8377;{fmt_cr(snap['High / Low'])}</td></tr>
    <tr><td>Stock P/E (TTM)</td><td>{snap['Stock P/E']:.1f}x</td></tr>
    <tr><td>Price / Book</td><td>~{current_price/snap['Book Value']:.1f}x (Book Value &#8377;{snap['Book Value']:.0f})</td></tr>
    <tr><td>Dividend Yield</td><td>{snap['Dividend Yield']:.2f}%</td></tr>
    <tr><td>ROE / ROCE (current)</td><td>{snap['ROE']:.1f}% / {snap['ROCE']:.1f}%</td></tr>
    <tr><td>Valuation Method</td><td>{len(valuation['fcff_projections'])}-yr DCF, base year FY{valuation['base_year_selection']['base_year_used_for_dcf'].split()[-1][-2:]} (audited)</td></tr>
  </table>
  <div class="callout">
    <strong>Investment view.</strong> {markdown_inline_to_html(sections.get('Executive Summary / Investment Thesis', '').split(chr(10)+chr(10))[0])}
  </div>
  <div class="cover-footer">{sources_line} See disclaimer on final page.</div>
</div>

<h2><span class="num">01</span> Executive Summary &amp; Investment Thesis</h2>
{paragraphs_html(sections.get('Executive Summary / Investment Thesis', ''))}
<div class="snapshot-row">
  <table class="data snapshot-table">
    <tr><th colspan="2">Snapshot at a Glance</th></tr>
    <tr><td class="label">Recommendation</td><td>{rating}</td></tr>
    <tr><td class="label">Fair Value / Current Price</td><td>&#8377;{fmt_cr(fair_value)} / &#8377;{fmt_cr(current_price)}</td></tr>
    <tr><td class="label">Implied Upside</td><td>+{upside_pct:.1f}%</td></tr>
    <tr><td class="label">WACC / Terminal Growth</td><td>{valuation['wacc']['wacc_annual']*100:.2f}% / {valuation['growth_assumptions']['terminal_growth_annual']*100:.1f}%</td></tr>
  </table>
  <div class="chart-box"><img src="{price_chart}"></div>
</div>

<h2><span class="num">02</span> Industry Overview &amp; Competitive Position</h2>
{paragraphs_html(sections.get('Industry Overview', ''))}

<h2><span class="num">03</span> Financial Analysis</h2>
{paragraphs_html(sections.get('Financial Analysis', ''))}
<img class="full" src="{revenue_chart}">
<div class="chart-pair">
  <div class="chart-box"><img src="{margin_chart}"></div>
  <div class="chart-box"><img src="{fcf_chart}"></div>
</div>
<table class="data">
  <tr><th class="label">Metric</th>{fin_header}</tr>
  {fin_rows}
</table>

<h2><span class="num">04</span> Valuation</h2>
<div class="chart-pair">
  <table class="data">
    <tr><th colspan="2">Key Assumptions</th></tr>
    <tr><td class="label">Risk-free rate</td><td>{ke['risk_free_rate_annual']*100:.2f}%</td></tr>
    <tr><td class="label">Equity risk premium</td><td>{ke['equity_risk_premium_annual']*100:.2f}%</td></tr>
    <tr><td class="label">Beta (proxy)</td><td>{ke['beta']:.2f}</td></tr>
    <tr><td class="label">Cost of equity (CAPM)</td><td>{ke['cost_of_equity_annual']*100:.2f}%</td></tr>
    <tr><td class="label">WACC</td><td>{valuation['wacc']['wacc_annual']*100:.2f}%</td></tr>
    <tr><td class="label">Terminal growth</td><td>{valuation['growth_assumptions']['terminal_growth_annual']*100:.2f}%</td></tr>
    <tr><td class="label">Capital structure (E / D)</td><td>{cs['weight_equity']*100:.1f}% / {cs['weight_debt']*100:.1f}%</td></tr>
  </table>
  <table class="data">
    <tr><th colspan="2">DCF Output (INR Cr)</th></tr>
    <tr><td class="label">PV of explicit FCFF</td><td>{fmt_cr(dcf['sum_pv_explicit_fcff_inr_cr'])}</td></tr>
    <tr><td class="label">PV of terminal value</td><td>{fmt_cr(dcf['pv_terminal_value_inr_cr'])}</td></tr>
    <tr><td class="label">Enterprise value</td><td>{fmt_cr(dcf['enterprise_value_inr_cr'])}</td></tr>
    <tr><td class="label">Less: total debt</td><td>({fmt_cr(dcf['total_debt_inr_cr'])})</td></tr>
    <tr><td class="label">Plus: cash &amp; investments</td><td>{fmt_cr(dcf['cash_and_investments_inr_cr'])}</td></tr>
    <tr><td class="label"><strong>Equity value</strong></td><td><strong>{fmt_cr(dcf['equity_value_inr_cr'])}</strong></td></tr>
    <tr><td class="label">Implied fair value / share</td><td>&#8377;{fmt_cr(fair_value)}</td></tr>
  </table>
</div>
<img class="full" src="{bridge_chart}">
<table class="data">
  <tr><th>Year</th><th>Growth %</th><th>FCFF (INR Cr)</th><th>Discount Factor</th><th>PV (INR Cr)</th></tr>
  {fcff_rows}
</table>

<h2><span class="num">05</span> Key Risks</h2>
{risk_tags_html}

<div class="disclaimer">
<strong>Disclaimer.</strong> This report has been prepared for informational and educational purposes only and does not constitute
investment advice, an offer, or a solicitation to buy or sell any security. Figures are sourced from screener.in consolidated
financials and cited public news. Valuation inputs including beta, the risk-free rate, and the equity risk premium are analyst
assumptions, not company-reported data, and the DCF output is highly sensitive to them. Past performance is not indicative of
future results. Readers should conduct their own due diligence and consult a licensed financial adviser before making any
investment decision.
</div>

</body>
</html>
"""
    return html


def main():
    ticker = sys.argv[1] if len(sys.argv) > 1 else "INFY"
    html = build(ticker)
    out_dir = Path(__file__).parent.parent / "data" / ticker
    out_dir.mkdir(parents=True, exist_ok=True)
    html_path = out_dir / f"{ticker}_report.html"
    html_path.write_text(html, encoding="utf-8")

    from weasyprint import HTML
    pdf_path = out_dir / f"{ticker}_Equity_Research_Report.pdf"
    HTML(filename=str(html_path)).write_pdf(str(pdf_path))
    print(f"Wrote {pdf_path}")


if __name__ == "__main__":
    main()
