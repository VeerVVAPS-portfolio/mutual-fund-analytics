# Equity Research Platform — Agent Workflow

## Roster

| Agent | Purpose |
|---|---|
| `research-orchestrator` | Sequences all other agents for a given ticker; only agent with `tools: Agent` (also holds `Write`, solely to persist `report-writer`'s text output) |
| `screener-scraper` | Scrapes screener.in for raw financials (plain HTTP+BeautifulSoup by default, Playwright fallback) |
| `financial-data-validator` | Sanity-checks scraped data (units, year alignment, internal consistency) before it's trusted |
| `industry-research` | Web search for industry overview, competitors, news, and risks |
| `valuation-engine` | Deterministic Python DCF/WACC computation — no LLM arithmetic |
| `report-writer` | Drafts the analyst report narrative from validated data only; Read-only, returns Markdown as text |
| `narrative-fact-checker` | Cross-checks every claim in the draft against source data before delivery |
| `report-pdf-builder` | Renders the approved draft into a brand-themed PDF (HTML+CSS via WeasyPrint, matplotlib charts) — final pipeline stage |

## Trigger points

- **research-orchestrator**: fires when the user requests a full report for a ticker/company.
- **screener-scraper**: invoked by the orchestrator at the start of the pipeline.
- **financial-data-validator**: invoked immediately after the scraper produces raw data.
- **industry-research**: invoked in parallel with scraping/validation (independent of financial data).
- **valuation-engine**: invoked after validation completes successfully.
- **report-writer**: invoked once validated financials, industry notes, and valuation are all available. Re-invoked for correction passes. Returns the Markdown draft as response text — it has no Write tool, since the harness blocks subagents from writing report-shaped files directly (confirmed in the first end-to-end run). `research-orchestrator` is the one that persists the returned text to `report_draft.md`.
- **narrative-fact-checker**: invoked after every report-writer draft, including correction passes.
- **report-pdf-builder**: invoked once the fact-checker approves the draft (or after retries are exhausted and `[UNVERIFIED]` markers are accepted). Final stage — its PDF is the deliverable returned to the user.

## Coordination graph

```
                          ┌─────────────────────┐
                          │ research-orchestrator│
                          └──────────┬───────────┘
                                     │
                 ┌───────────────────┼───────────────────┐
                 ▼                                       ▼
        screener-scraper                         industry-research
                 │ raw_financials.json                    │ industry_notes.json
                 ▼                                         │
     financial-data-validator                              │
                 │ validated_financials.json                │
                 ▼                                         │
         valuation-engine                                  │
                 │ valuation.json                          │
                 └───────────────┬─────────────────────────┘
                                 ▼
                          report-writer
                                 │ report_draft.md
                                 ▼
                     narrative-fact-checker
                                 │ factcheck_report.json
                     ┌───────────┴───────────┐
              approved: true          approved: false
                     │                       │
                     │                       ▼
                     │              back to report-writer
                     │             (max 2 retries, then
                     │              mark [UNVERIFIED])
                     │                       │
                     ▼                       ▼
                     └──────────┬────────────┘
                                 ▼
                        report-pdf-builder
                                 │ <TICKER>_Equity_Research_Report.pdf
                                 ▼
                          deliver to user
```

## Artifact contracts (all under `data/<ticker>/`)

- `raw_financials.json` — scraper output, includes `warnings` array
- `validated_financials.json` — validator output, includes `validation_notes` array
- `industry_notes.json` — industry research output, every claim source-linked
- `valuation.json` — DCF/WACC output with full assumption trail
- `report_draft.md` — narrative draft; written by `research-orchestrator` from `report-writer`'s returned text, not by `report-writer` itself
- `factcheck_report.json` — `{verified_count, flagged[], approved}`
- `<TICKER>_Equity_Research_Report.pdf` — final deliverable; brand-themed PDF built by `report-pdf-builder` from the approved draft and the same three source artifacts

Why files instead of chat context: keeps each agent's input/output traceable and re-runnable independently, and avoids blowing context on large financial datasets passed through the orchestrator.
