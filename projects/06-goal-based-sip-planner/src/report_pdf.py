"""
report_pdf.py — assembles the full wealth plan (goals, funding sequence,
protection gaps, loan schedule, advisor's note) into one printable PDF.

Built with reportlab (pure-Python, no system dependencies — safe on Windows,
unlike WeasyPrint/wkhtmltopdf). White-background, print-friendly layout,
deliberately not matching the dashboard's dark theme.
"""

from __future__ import annotations

import io
from datetime import date
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle,
)

from formatting import format_inr, format_inr_compact
from protection import outstanding_loan_balance

# reportlab's built-in fonts (Helvetica etc.) don't include the ₹ glyph — it
# renders as a missing-glyph box. Noto Sans does, and is bundled in assets/
# rather than relying on Windows-only system fonts, so this also works on a
# Linux deployment (e.g. Streamlit Community Cloud).
_FONT_PATH = Path(__file__).resolve().parent.parent / "assets" / "NotoSans.ttf"
pdfmetrics.registerFont(TTFont("NotoSans", str(_FONT_PATH)))
# Variable font, single weight available via this basic registration — used
# for both "regular" and "bold" slots. Table header contrast (white-on-navy)
# carries the emphasis instead of font weight.
pdfmetrics.registerFont(TTFont("NotoSans-Bold", str(_FONT_PATH)))
pdfmetrics.registerFontFamily("NotoSans", normal="NotoSans", bold="NotoSans-Bold", italic="NotoSans", boldItalic="NotoSans-Bold")

NAVY = colors.HexColor("#1F2937")
ACCENT = colors.HexColor("#4338CA")
GREEN = colors.HexColor("#047857")
AMBER = colors.HexColor("#B45309")
RED = colors.HexColor("#B91C1C")
LIGHT_GREY = colors.HexColor("#F3F4F6")

PRIORITY_ORDER = {"Must-have": 0, "Good-to-have": 1, "Dream goal": 2}

_styles = getSampleStyleSheet()
TITLE_STYLE = ParagraphStyle("Title2", parent=_styles["Title"], fontName="NotoSans-Bold", textColor=NAVY, fontSize=22, spaceAfter=4)
SUBTITLE_STYLE = ParagraphStyle("Subtitle", parent=_styles["Normal"], fontName="NotoSans", textColor=colors.HexColor("#6B7280"), fontSize=10, spaceAfter=14)
H2_STYLE = ParagraphStyle("H2", parent=_styles["Heading2"], fontName="NotoSans-Bold", textColor=NAVY, fontSize=14, spaceBefore=14, spaceAfter=8)
H3_STYLE = ParagraphStyle("H3", parent=_styles["Heading3"], fontName="NotoSans-Bold", textColor=ACCENT, fontSize=12, spaceBefore=10, spaceAfter=4)
BODY_STYLE = ParagraphStyle("Body2", parent=_styles["Normal"], fontName="NotoSans", fontSize=9.5, leading=14, spaceAfter=6)
CAPTION_STYLE = ParagraphStyle("Caption", parent=_styles["Normal"], fontName="NotoSans", fontSize=8, textColor=colors.HexColor("#6B7280"), leading=11)


def _kv_table(rows: list[tuple[str, str]], col_widths=(7 * cm, 6 * cm)) -> Table:
    t = Table(rows, colWidths=list(col_widths))
    t.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (-1, -1), "NotoSans"),
        ("FONTSIZE", (0, 0), (-1, -1), 9.5),
        ("TEXTCOLOR", (0, 0), (0, -1), NAVY),
        ("FONTNAME", (0, 0), (0, -1), "NotoSans-Bold"),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("LINEBELOW", (0, 0), (-1, -1), 0.4, colors.HexColor("#E5E7EB")),
    ]))
    return t


_STATUS_HEX = {"Safe": "#047857", "Caution": "#B45309", "High": "#B91C1C"}


def build_pdf_report(
    results: list[dict],
    income_inputs: dict,
    loans: list[dict],
    protection_inputs: dict,
    staggered_plan: list,
    advisory_note: dict,
    life,
    health,
    ef,
    foir,
) -> bytes:
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer, pagesize=A4,
        leftMargin=2 * cm, rightMargin=2 * cm, topMargin=1.8 * cm, bottomMargin=1.8 * cm,
        title="Wealth Plan Report",
    )
    story = []

    total_sip = sum(g["result"].monthly_sip for g in results)

    story.append(Paragraph("Goal-Based Wealth Plan", TITLE_STYLE))
    story.append(Paragraph(f"Generated {date.today().strftime('%d %B %Y')} · Educational/portfolio tool, not financial advice", SUBTITLE_STYLE))

    story.append(_kv_table([
        ["Total Required Monthly SIP", format_inr(total_sip)],
        ["Number of Goals", str(len(results))],
        ["Debt Load (FOIR)", f"{foir.level} ({foir.ratio*100:.0f}%)"],
    ]))

    story.append(Paragraph("Advisor's Note", H2_STYLE))
    story.append(Paragraph(f"<b>{advisory_note['headline']}</b>", BODY_STYLE))
    for para in advisory_note["paragraphs"]:
        story.append(Paragraph(para, BODY_STYLE))
    for risk in advisory_note["risk_notes"]:
        story.append(Paragraph(f"<b>Risk:</b> {risk}", ParagraphStyle("risk", parent=BODY_STYLE, textColor=AMBER)))

    story.append(Paragraph("Goal Plan", H2_STYLE))
    sorted_results = sorted(results, key=lambda g: PRIORITY_ORDER.get(g.get("priority", "Dream goal"), 99))
    for g in sorted_results:
        r = g["result"]
        story.append(Paragraph(f"{g['name']} <font color='#6B7280' size=9>({g.get('category','Other')} · {g.get('priority','Dream goal')})</font>", H3_STYLE))
        rows = [
            ["Target Amount", format_inr(g["amount"]) + (" (future value)" if g["amount_is_future_value"] else " (today's value)")],
            ["Years to Goal", f"{g['years']:.0f}"],
            ["Future Value Required", format_inr(r.future_value_required)],
            ["Monthly SIP Required" + (" (Year 1)" if g["step_up"] > 0 else ""), format_inr(r.monthly_sip)],
            ["Total Invested", format_inr(r.total_invested)],
            ["Wealth Gained", format_inr(r.wealth_gained)],
        ]
        story.append(_kv_table(rows))

    story.append(Paragraph("Recommended Funding Order", H2_STYLE))
    if all(p.start_year == 0 for p in staggered_plan):
        story.append(Paragraph("Income covers every goal's SIP starting today — no sequencing needed.", BODY_STYLE))
    else:
        seq_rows = [["Goal", "Priority", "Start", "Monthly SIP"]]
        for p in staggered_plan:
            start_label = "At risk" if p.at_risk else ("Now" if p.start_year == 0 else f"Year {p.start_year}")
            sip_label = "—" if p.monthly_sip_at_start is None else format_inr(p.monthly_sip_at_start)
            seq_rows.append([p.name, p.priority, start_label, sip_label])
        seq_table = Table(seq_rows, colWidths=[5 * cm, 3.5 * cm, 2.5 * cm, 3 * cm])
        seq_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), NAVY),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, -1), "NotoSans"),
            ("FONTNAME", (0, 0), (-1, 0), "NotoSans-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 9),
            ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#E5E7EB")),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, LIGHT_GREY]),
        ]))
        story.append(seq_table)

    story.append(Paragraph("Protection Summary", H2_STYLE))

    def _gap_table(title, current, recommended, gap, note):
        story.append(Paragraph(title, H3_STYLE))
        rows = [
            ["Current", format_inr(current)],
            ["Recommended", format_inr(recommended)],
            ["Gap", format_inr(gap)],
        ]
        story.append(_kv_table(rows))
        story.append(Paragraph(note, CAPTION_STYLE))
        story.append(Spacer(1, 6))

    _gap_table(
        "Life Insurance", life.current_cover, life.total_need, life.gap,
        f"Recommended = outstanding loans ({format_inr_compact(life.debt_component)}) + goal lump-sum equivalents "
        f"({format_inr_compact(life.goals_component)}) + {life.replacement_years} years of income replacement "
        f"({format_inr_compact(life.income_replacement_component)}) for {protection_inputs.get('dependents', 0)} dependent(s).",
    )
    _gap_table(
        "Health Insurance", health.current_cover, health.recommended, health.gap,
        f"Based on {protection_inputs.get('city_tier', 'Metro / Tier-1')} benchmarks for a family of "
        f"{1 + protection_inputs.get('dependents', 0)}.",
    )
    _gap_table(
        "Emergency Fund", ef.current_savings, ef.recommended, ef.gap,
        f"Target = {ef.recommended_months} months of household expenses.",
    )

    story.append(Paragraph("Debt Load (FOIR)", H3_STYLE))
    story.append(Paragraph(
        f"<font color='{_STATUS_HEX.get(foir.level, '#1F2937')}'><b>{foir.level}</b></font> — EMIs are "
        f"{foir.ratio*100:.0f}% of monthly income ({format_inr(foir.total_monthly_emi)} of {format_inr(foir.monthly_income)}). "
        f"Indian banks treat 40% or below as safe and rarely lend past 55%.",
        BODY_STYLE,
    ))

    if loans:
        story.append(Paragraph("Loan / EMI Schedule", H2_STYLE))
        loan_rows = [["Purpose", "EMI/month", "Months Left", "Rate", "Outstanding Balance"]]
        for loan in loans:
            balance = outstanding_loan_balance(loan["emi"], loan["rate"], loan["remaining_months"])
            loan_rows.append([
                loan["purpose"], format_inr(loan["emi"]), str(loan["remaining_months"]),
                f"{loan['rate']*100:.1f}%", format_inr(balance),
            ])
        loan_table = Table(loan_rows, colWidths=[4 * cm, 3 * cm, 2.5 * cm, 2 * cm, 3.5 * cm])
        loan_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), NAVY),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, -1), "NotoSans"),
            ("FONTNAME", (0, 0), (-1, 0), "NotoSans-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 9),
            ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#E5E7EB")),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, LIGHT_GREY]),
        ]))
        story.append(loan_table)

    story.append(Spacer(1, 16))
    story.append(Paragraph(
        "Disclaimer: Educational/portfolio tool, not financial advice. Return, inflation, and insurance-adequacy "
        "assumptions are editable estimates based on common planning heuristics, not guarantees. Mutual fund and "
        "insurance decisions should be made with a SEBI-registered investment adviser / licensed insurance advisor.",
        CAPTION_STYLE,
    ))

    doc.build(story)
    return buffer.getvalue()
