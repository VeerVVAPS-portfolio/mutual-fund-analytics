# LinkedIn Post — Project 01: Mutual Fund Analytics Automation

---

## FORMAT NOTES (read once, delete later)
- Hook must land in the first 210 characters — that's what shows before "see more"
- Ideal length: 1,300–1,900 characters total
- No external links in the post body — LinkedIn suppresses reach for posts with links.
  Put the GitHub/dashboard link in the FIRST COMMENT (template below)
- Reply to the first 20–30 comments within the first hour — this triggers algorithm amplification
- Best time to post: Tuesday–Thursday, 8–10 AM IST

---

## SCREENSHOTS TO TAKE BEFORE POSTING

Take these in order before you post. Use the Streamlit dashboard at http://localhost:8501.

1. **Main screenshot (attach to post):**
   - Select "Large Cap" from the category dropdown
   - Set profile to "Balanced (Default)"
   - Screenshot the full page showing: title + top pick banner + ranked table
   - Crop tightly — remove browser chrome/address bar
   - Save as: `screenshot_01_dashboard_ranked_table.png`

2. **Optional second image (carousel or comment):**
   - Switch to any category, scroll to the radar chart
   - Screenshot just the radar chart section showing 3 funds overlaid
   - Save as: `screenshot_02_radar_chart.png`

3. **Optional third image:**
   - Screenshot the Excel output (`output/fund_rankings.xlsx`) open in Excel
   - Show the Summary sheet with top picks per category
   - Save as: `screenshot_03_excel_output.png`

> LinkedIn single-image posts get 2.77% engagement.
> If you want higher reach, turn these 3 screenshots into a PDF carousel
> (6.60% engagement) — upload as a PDF document, one slide per image.
> You can do this in Canva quickly.

---

## THE POST

*(Copy everything between the dashes below — nothing else)*

---

Most investors compare mutual funds by their 1-year return.

That's like hiring someone because they ran fast in 2022.

I ranked 184 Indian equity funds using a completely different framework. Here's how — and what it revealed.

—

**The problem with return-based rankings:**

Sharpe Ratio already captures return relative to risk. If you also weight raw returns separately, you're counting the same thing twice. The ranking looks rigorous but isn't.

I rebuilt the logic from scratch with a 2-stage approach:

**Stage 1 — Eligibility (pass/fail, not scored):**
→ AUM ≥ ₹1,000 Cr — is the fund stable enough to recommend?
→ 5-year track record — do we have enough history to trust the numbers?

93 of 184 funds passed.

**Stage 2 — 3 independent metrics, ranked as percentiles within category:**

1/ Sharpe Ratio — return per unit of volatility. How smooth was the ride?

2/ Jensen's Alpha — return beyond what the fund's market exposure alone explains. Did the manager actually add value, or just ride the index?

3/ Consistency — % of rolling 3-year windows where the fund beat its category average. Was good performance a one-time fluke, or sustained across market cycles?

Each metric measures a completely different dimension. That's intentional.

—

**The finding I didn't expect:**

Multi Cap and Flexi Cap funds have almost no 5-year eligible funds.

Not because they're recent — but because SEBI redefined these categories in 2020. Funds were forced to restructure, which effectively reset their track records.

Most fund screeners don't flag this. The data gap looks like bad performance.

Knowing the regulation is as important as knowing the numbers.

—

**The output:**

An interactive Streamlit dashboard where you pick a category and adjust the metric weights based on your priority.

Conservative investor? Load up on Consistency.
Chasing alpha? Weight manager skill higher.
Want the smoothest ride? Prioritise Sharpe.

The rankings update live. Same data, different perspective.

Built with Python · pandas · yfinance · mfapi.in · Streamlit · openpyxl

—

What's one metric you look at when picking a fund that most people skip?

#MutualFunds #Python #FinTech #PersonalFinance #DataAnalytics

---

*(End of post)*

---

## FIRST COMMENT (post this immediately after publishing)

> Dashboard and full pipeline code:
> [paste your GitHub repo link here once the repo is public]
>
> Tools used: Python, pandas, yfinance (NIFTY 50 data), mfapi.in (NAV history), Streamlit, openpyxl

---

## CHECKLIST BEFORE HITTING POST

- [ ] Screenshot taken and cropped cleanly (no browser address bar visible)
- [ ] Character count is 1,300–1,900 (paste into wordcounter.net to check)
- [ ] First comment text is ready to paste immediately after posting
- [ ] You're posting between 8–10 AM on a weekday
- [ ] You'll be free for 60 minutes after posting to reply to comments

---

## POST PERFORMANCE LOG

| Date Posted | Platform | Impressions | Likes | Comments | Reposts | Notes |
|-------------|----------|-------------|-------|----------|---------|-------|
|             |          |             |       |          |         |       |

*(Fill this in after posting — track what works over time)*
