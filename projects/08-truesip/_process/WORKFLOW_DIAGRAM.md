# TrueSIP — Workflow & Agent Hierarchy (graphical)

Two diagrams: **(1)** the Lean Six Sigma DMAIC process this product was built with, and **(2)** the agent hierarchy (orchestrator + council + build team + QA), with the model tier delegated to each role. Rendered in Mermaid so they display as real diagrams on GitHub.

---

## 1. The build workflow — Lean Six Sigma (DMAIC)

```mermaid
flowchart TD
    START(["Veer's ask: productize Projects 1 + 2 + 6 into one tool"]) --> DEF

    subgraph DEF["① DEFINE"]
        direction TB
        DEF1["Reframe the problem — not 3 apps to stack,<br/>but 1 journey with 2 manual seams"]
        DEF2["7 CTQs + Six-Sigma goal:<br/>2 handoffs → 0 · 3 entry points → 1 · LLM numbers stay 0"]
        DEF1 --> DEF2
    end

    subgraph ANA["② MEASURE / ANALYZE — Council debate"]
        direction TB
        ANA1["6 critics give independent positions (Round 1)"]
        ANA2["Chair synthesis: 5/6 build · 3 build mandates surfaced"]
        ANA3["Round 2 cross-examination:<br/>compliance resolved into a two-mode design"]
        ANA1 --> ANA2 --> ANA3
    end

    DEC{"③ Veer locks direction:<br/>Streamlit · goal-first · flagship-on-top ·<br/>name TrueSIP · lean core + Advanced"}

    subgraph IMP["④ IMPROVE — Build (model-delegated)"]
        direction TB
        IMP1["Recruit 7-agent team via /agent-architect"]
        IMP2["Data seed (Haiku) → shared core + scaffold (Sonnet)"]
        IMP3["Engine (Opus) → explainer (Sonnet) → UI (Sonnet)"]
        IMP1 --> IMP2 --> IMP3
    end

    subgraph CON["⑤ CONTROL — QA gate"]
        direction TB
        CON1["finance-correctness (Opus) ∥ compliance (Sonnet)"]
        CON2["ux-audit skill — browser-level UX gate"]
        CON3["fix loop until all gates PASS"]
        CON1 --> CON2 --> CON3
    end

    FIN(["Deploy · README · diagrams · distill the PROCESS_LOG into a skill"])

    DEF --> ANA --> DEC --> IMP --> CON --> FIN
```

---

## 2. The agent hierarchy

The **main session (Opus 4.8) is the orchestrator** — it runs DMAIC and sequences every other agent; none of the leaf agents invoke each other. Models are delegated by task complexity: **Haiku** = mechanical · **Sonnet** = standard build / fixed-criteria checks · **Opus** = heavy finance reasoning + judgment.

```mermaid
flowchart TD
    ORCH["ORCHESTRATOR — main session · Opus 4.8<br/>runs DMAIC, makes every handoff"]

    subgraph COUNCIL["Council — critique & debate (Analyze phase)"]
        direction LR
        PC["Product Strategist<br/>Opus"]
        UXC["UX / Journey<br/>Opus"]
        TAC["Technical Architect<br/>Sonnet"]
        FDC["Finance Domain<br/>Opus"]
        RPC["Recruiter / Portfolio<br/>Sonnet"]
        DAC["Risk / Devil's Advocate<br/>Opus"]
    end

    subgraph BUILD["Build team — recruited via /agent-architect (Improve phase)"]
        direction LR
        DP["data-pipeline-runner<br/>Haiku"]
        SC["shared-core-engineer<br/>Sonnet"]
        IL["integration-logic-architect<br/>Opus"]
        LL["llm-reasoning-engineer<br/>Sonnet"]
        UB["streamlit-ux-builder<br/>Sonnet"]
    end

    subgraph QA["QA gate — auditors (Control phase)"]
        direction LR
        FA["finance-correctness-auditor<br/>Opus"]
        CA["compliance-guardrail-checker<br/>Sonnet"]
    end

    ORCH ==> COUNCIL
    ORCH ==> BUILD
    ORCH ==> QA

    DP --> SC --> IL
    IL --> LL
    IL --> UB
    LL --> UB
    UB --> FA
    UB --> CA
    FA -. "fix loop" .-> ORCH
    CA -. "fix loop" .-> ORCH
```

---

## 3. (bonus) The product's runtime data-flow — what the council made cohere

How a user's inputs flow through the merged engine. The point of the whole build: **0 manual handoffs**, every number deterministic, the LLM only explaining.

```mermaid
flowchart LR
    G["Goal(s):<br/>target + horizon"] --> PE
    R["Risk quiz<br/>→ risk label"] --> PE
    I["Income / expenses<br/>+ SIP step-up"] --> PE

    PE["planning_engine.build_plan()"]

    PE --> HB["Horizon sets each goal's<br/>equity BAND; risk label = tilt + cap"]
    HB --> BR["Blended expected return<br/>per goal (honest fix)"]
    BR --> SIP["Deterministic SIP<br/>(annuity-due solver)"]
    SIP --> SPLIT["Split SIP across<br/>equity / debt / gold"]
    SPLIT --> EQ["Equity slice → CATEGORY only"]
    SPLIT --> NEQ["Debt / Gold → named but UNRANKED"]

    EQ -. "opt-in, neutral weights" .-> SCR["Explore Funds screener<br/>(the only fund-naming surface)"]
    PE --> EXP["explainer.explain_plan()<br/>— prose only, zero numbers"]

    style PE fill:#1E293B,stroke:#818CF8,color:#fff
    style SCR fill:#1E293B,stroke:#818CF8,color:#fff
```
