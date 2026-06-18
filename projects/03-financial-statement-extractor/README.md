# Financial Statement Extractor

Extracts P&L, Balance Sheet, and Cash Flow statements from annual report PDFs and outputs a formatted, analysis-ready Excel file — no copy-pasting required.

## What It Does

1. Upload 1–5 annual report PDFs (one per financial year — name files with the full 4-digit year, e.g. `infosys-ar-2025.pdf`, so the year is detected correctly)
2. The tool automatically finds the financial statement pages (PyMuPDF scans the full document fast; pdfplumber extracts the actual tables on just those pages)
3. Tables are extracted and normalized to a standard schema
4. A 4-sheet Excel is generated: P&L · Balance Sheet · Cash Flow · Ratios

## Ratios Calculated Automatically

| Ratio | Category |
|---|---|
| Gross Margin, Operating Margin, Net Margin | Profitability |
| ROE, ROA | Profitability |
| Current Ratio | Liquidity |
| D/E Ratio | Leverage |
| Interest Coverage | Coverage |

## Run Locally

```bash
pip install -r requirements.txt
streamlit run dashboard/app.py
```

## Tested Against

Validated against 6 Indian companies across 5 sectors: Infosys, TCS, Maruti Suzuki, Asian Paints, Dr. Reddy's, and Page Industries. P&L and Balance Sheet extraction reconciles exactly (Assets = Liabilities + Equity) for all of these. Cash Flow reconciles for 4 of 6.

## Limitations

- Works with **text-based PDFs** only (not scanned/image PDFs)
- **Banks and financial conglomerates are not supported** — confirmed on HDFC Bank, where the report's size and an embedded insurance subsidiary make "Balance Sheet" / "Profit and Loss" / "Cash Flow" turn up too often in unrelated prose for page-finding to work reliably
- Complex merged-cell tables may partially extract — always verify numbers against the source
- Works best with Indian company annual reports (Ind AS format)

## Tech Stack

- Python · Streamlit · PyMuPDF · pdfplumber · pandas · openpyxl

---

*Built by Veer Pratap Singh as part of a Finance + Python portfolio.*
