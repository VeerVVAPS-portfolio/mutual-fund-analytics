# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Status

This project is a **Claude Code subagent pipeline**, not a standalone Python app — there is no top-level `requirements.txt`, and none is planned. The deliverable IS the `.claude/agents/` pipeline: invoking `research-orchestrator` for a ticker produces `data/<ticker>/<TICKER>_Equity_Research_Report.pdf` plus its supporting JSON/Markdown artifacts. `data/<ticker>/` output is gitignored (regenerable by re-running the pipeline). `src/` does get real Python files (`valuation.py`, `build_report_pdf.py`, `report_charts.py`), written and reused by the agents that need deterministic computation or rendering — they're tooling for the subagents, not a package meant to be run standalone.

Validated end-to-end on a real ticker (Infosys/INFY). That run surfaced and fixed three real spec bugs, now reflected in the agent files below:
- `report-writer` cannot Write — the harness blocks subagents from writing report-shaped files directly. It returns the Markdown draft as response text; `research-orchestrator` (which holds the only `Write` tool besides `Agent`) persists it to `report_draft.md`.
- `screener-scraper` defaults to plain HTTP + BeautifulSoup (screener.in is server-rendered) rather than Playwright/Chromium, falling back to a browser only if that fails.
- `valuation-engine` must compute any growth-rate commentary (e.g. trailing CAGR) directly from the data in its script, not state it from memory — a hardcoded figure once drifted from the source data and was only caught by the fact-checker.

## Architecture: multi-agent equity research pipeline

This is a project-specific Claude Code subagent system (`.claude/agents/`), not a Python package to run directly. A user requests a full report for a ticker; `research-orchestrator` sequences seven specialist subagents, each reading/writing a JSON, Markdown, or PDF artifact under `data/<ticker>/` rather than passing data through chat context (keeps large financial datasets out of context windows and makes every stage independently re-runnable).

Full coordination graph and rationale: [.claude/agents/WORKFLOW.md](.claude/agents/WORKFLOW.md).

### Pipeline order and artifacts

```
screener-scraper        -> data/<ticker>/raw_financials.json
financial-data-validator -> data/<ticker>/validated_financials.json
industry-research        -> data/<ticker>/industry_notes.json   (runs in parallel with the two stages above)
valuation-engine          -> data/<ticker>/valuation.json
report-writer             -> data/<ticker>/report_draft.md
narrative-fact-checker     -> data/<ticker>/factcheck_report.json
report-pdf-builder         -> data/<ticker>/<TICKER>_Equity_Research_Report.pdf
```

- `report-writer` and `narrative-fact-checker` loop: on `approved: false`, the orchestrator routes flags back to `report-writer` for a correction pass (max 2 retries), then re-runs the fact-checker. If still unresolved, the report proceeds to PDF rendering with flagged sections marked `[UNVERIFIED]` rather than silently dropping the issue.
- `report-writer` must never compute or estimate a number itself — every figure cited must trace back to `validated_financials.json`, `industry_notes.json`, or `valuation.json`. `narrative-fact-checker` exists specifically to catch violations of this rule.
- `valuation-engine` computes DCF/WACC/CAPM deterministically in Python (a script under `src/valuation.py`), never via LLM arithmetic — this guards against the kind of unit-mismatch bug (annualized returns compared against monthly volatility) that shipped in a prior portfolio project (Project 4, Black-Litterman).
- `financial-data-validator` exists because a prior project (PDF statement extraction, Project 3) shipped headline-correct totals with noisy detail rows underneath (signature-block text captured as line items, cash-flow rows merged in from an adjacent table). Treat every scraped number as unverified until checked for unit consistency, year-column alignment, and internal consistency (e.g. Assets = Liabilities + Equity).
- `screener-scraper` pulls from screener.in via plain HTTP + BeautifulSoup by default (falls back to Playwright/Chromium only if that fails), capturing units exactly as labeled (₹ Crore) — never silently converts. Missing/unparseable rows go into a `warnings` array rather than failing silently.
- `report-pdf-builder` renders the approved Markdown draft into a brand-themed PDF (HTML+CSS via WeasyPrint, matplotlib charts at 200 DPI, embedded as base64 so paths never break) — it researches the subject company's brand colors via web search, but semantic colors (green for upside, red for downside) are always fixed regardless of brand. It is the final pipeline stage; its PDF is the deliverable. Its canonical build instructions live in the **global, domain-agnostic** skill `~/.claude/skills/pdf-report-builder/SKILL.md` (used across multiple unrelated projects for any kind of branded PDF report, not just equity research) — the project agent file is a thin pointer to it plus this project's specific wiring (artifact paths, Indian digit grouping, screener.in statement-basis line). `src/report_charts.py` and `src/build_report_pdf.py` here are this project's adapted copy of that skill's bundled reference implementation; both were built and visually debugged against a real INFY run (fixed a WeasyPrint flexbox bug that silently drops `<img>` children, a missing cover-page break, and Western-vs-Indian digit grouping). The skill also ships generic `report_components.py` building blocks and a separate equity-research worked example, in case this project's script is ever rebuilt from scratch.

### Per-agent tool scoping

`research-orchestrator` has `Agent` plus `Write` (the `Write` is solely to persist `report-writer`'s text-only output — see above). Every other agent is scoped to just the tools its stage needs: `industry-research` has `WebSearch`/`WebFetch`/`Write` only, no `Bash`; `report-writer` has `Read` only — no `Write`, no compute tools, reinforcing that it must not write files or do arithmetic; `narrative-fact-checker` has `Read`/`Write` for its JSON findings only; `report-pdf-builder` has `Read`, `Write`, `Bash`, `WebSearch`, `WebFetch` — the only agent with both file-write and shell access, because rendering (matplotlib/WeasyPrint) and brand-color research both require it. Unlike `report-writer`'s blocked narrative-file write, this agent's `Write`/`Bash` access is for mechanical rendering of already-approved content, not for authoring findings.

## Working in this repo

- This is one subfolder of a larger multi-project portfolio repo, but unlike the other projects it has no per-project `requirements.txt` and is not deployed to Streamlit Cloud — it runs entirely inside a Claude Code session.
- When editing the agent specs, follow each agent's stated workflow and output schema exactly — they were each written as a contract for the *next* agent in the chain, so changing one artifact's shape without updating the consuming agent's spec will break the handoff.
- screener.in's free tier doesn't expose historical year-by-year ROE/Debt-to-Equity series (snapshot only) — `financial-data-validator` and `report-writer` should treat this as an expected gap to flag, not a scraping failure to debug.
