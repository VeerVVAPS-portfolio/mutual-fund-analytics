# TrueSIP — Agent Workflow & Coordination Graph

The build/maintenance team for TrueSIP (`projects/08-truesip/`). Designed via `/agent-architect` after a 6-member product council locked the direction (see `../_process/council/SYNTHESIS.md`). The **MAIN Claude Code session is the orchestrator** — it sequences these leaf agents; none of them invoke each other (no agent holds the `Agent` tool).

## Roster
| Agent | Model | One-line purpose |
|---|---|---|
| `data-pipeline-runner` | haiku | Fetch AMFI data → committed seed `scored_funds.csv` |
| `shared-core-engineer` | sonnet | `shared/` package + `data_store` + Streamlit wizard scaffold + theme |
| `integration-logic-architect` | opus | Reconciliation engine: horizon allocation, deterministic SIP, asset split, two-mode compliance |
| `llm-reasoning-engineer` | sonnet | Groq explain-why layer (prose only, demo fallback) |
| `streamlit-ux-builder` | sonnet | Goal-first front door, wizard, results, Explore-Funds, Advanced |
| `finance-correctness-auditor` | opus | Pre-ship: determinism + math-correctness gate |
| `compliance-guardrail-checker` | sonnet | Pre-ship: SEBI acceptance-criterion + disclaimers gate |

## Trigger points
- **data-pipeline-runner** — at build start, or "fund data stale/missing".
- **shared-core-engineer** — after the data seed exists; foundational.
- **integration-logic-architect** — after the `shared/` scaffold; any cross-tool finance composition.
- **llm-reasoning-engineer** — after the engine API exists.
- **streamlit-ux-builder** — after engine + explainer exist.
- **finance-correctness-auditor** + **compliance-guardrail-checker** — before calling any screen/finance change done.

## Coordination graph (handoffs via fixed artifacts)
```
data-pipeline-runner
  └─ data/scored_funds.csv ──────────────────────────┐
shared-core-engineer                                 │
  └─ shared/ (data_store, theme), dashboard/app.py skeleton, .streamlit/config.toml
        └─ integration-logic-architect
              └─ shared/planning_engine.py  (documented API; personalized fields flagged)
                    ├─ llm-reasoning-engineer ─→ shared/explainer.py  (prose only)
                    └─ streamlit-ux-builder ──→ dashboard/app.py (filled) + views
                          ├─ finance-correctness-auditor ─→ _process/audits/finance-correctness.md  (GATE: PASS/FAIL)
                          └─ compliance-guardrail-checker ─→ _process/audits/compliance.md  (GATE: PASS/FAIL)
                                └─ main orchestrator runs the `ux-audit` skill → fix loop until both gates PASS
```

## Model-delegation principle
Defaults shown above. The orchestrator may bump any agent to Opus for a single unusually hard task at spawn time. **Haiku** = mechanical (data) · **Sonnet** = standard build / criteria-checks · **Opus** = heavy finance reasoning + correctness judgment.

## Note for this session
These files are manually created, so they auto-load only after a Claude Code restart. For the initial build, the orchestrator executes by spawning agents that *read their own persona file here* and run at the assigned model — so the personas + coordination contracts above are the single source of truth either way.
