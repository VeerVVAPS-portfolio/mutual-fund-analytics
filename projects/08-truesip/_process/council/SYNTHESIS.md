# Council Synthesis — Round 1

Six critics, independent opening positions. I (orchestrator) act as chair. Full individual critiques are the sibling files in this folder.

## Verdict & decision tally

| Member | Model | Verdict | D1 Stack | D2 Depth | D3 Portfolio |
|---|---|---|---|---|---|
| Product Strategist | Opus | YES-BUT | Unified Streamlit | Full flow, **goal-first** | Flagship on top |
| UX / Journey Architect | Opus | YES | Unified Streamlit | Full single-flow wizard | Flagship on top |
| Technical Architect | Sonnet | YES | Unified Streamlit (shared lib) | Full flow via `session_state` | Flagship on top |
| Finance Domain | Opus | YES-BUT | Unified Streamlit | Full flow **+ reconciliation rule** | Flagship on top |
| Recruiter / Portfolio | Sonnet | YES-BUT | Unified Streamlit | Full flow | Flagship on top *(but RAG first)* |
| Risk / Devil's Advocate | Opus | **DON'T / BUILD-THIN** | Streamlit (thin) | **Linked hub, not chained** | Flagship on top |

## Unanimous (6/6)
- **D1 — Unified Streamlit.** Nobody wants React/FastAPI: it adds zero finance/domain signal, breaks the "Veer can deploy & maintain it" CTQ6, and the three apps already share one dark CSS system. Even the dissenter says "stay on Streamlit."
- **D3 — Flagship on top.** Keep all three apps live (their LinkedIn URLs must not break) and all three resume lines. The unified app is a *fifth* deployment / *fourth* resume entry — the integration layer — not a replacement. Collapsing three independent proofs into one *loses* surface area.
- **Integrity spine is sacred.** Every rupee figure stays deterministic; the LLM only explains "why."

## Strong majority — D2 (5/6): full automated single-flow
One continuous journey, zero manual handoffs. The lone dissent (Devil's Advocate) is on **compliance + opportunity cost**, not on UX or feasibility — see Tension A.

## The three BUILD MANDATES the council surfaced (would have been silent bugs)
1. **Kill the LLM-suggested SIP.** Project 2 currently prints `monthly_sip_suggestion` (an LLM number, "+10%/yr"). Project 6's entire thesis is the SIP must be *solved* deterministically. In one flow both render → the product visibly contradicts its own integrity spine. **Only SIZE's annuity-due solver may output a SIP.** *(UX critic, code-verified)*
2. **Horizon-authoritative allocation** *(Finance Domain — the reconciliation rule)*. The paradigm clash is real: PROFILE makes ONE whole-person risk mix; SIZE plans per-goal, and a goal's correct equity weight depends on its *horizon* (2-yr money ≠ 15-yr money). Resolution: **each goal's time horizon sets its baseline equity band; the risk-profile mix is demoted to a tilt-within-the-band + a top cap** (panic-prone investors capped at band midpoint) — never a competing person-level allocation. Bands: `<3y: 0–10%` · `3–7y: 20–40%` · `7–15y: 50–70%` · `>15y: 70–85%`.
3. **Show the equity-only gap honestly.** PROFILE recommends 4 asset classes; PICK only ranks EQUITY funds (Sharpe/Alpha computed vs NIFTY 50 — meaningless off-equity). Resolution: split each goal's SIP across asset classes by its tilted mix; **route only the equity rupees to the screener; show Debt/Gold/Alts as *named but explicitly un-ranked* categories** (e.g. SGB/gold-ETF, short-duration/PPF). Silently dropping the slices is dishonest; fabricating metrics is worse.

## Genuine tensions
- **A — COMPLIANCE (the crux, → Round 2).** Devil's Advocate: chaining *risk-profile + specific named fund + exact rupee amount + directive* on one personalized screen is a **category change** under SEBI's 2025 finfluencer rules — it *behaves* like personalized specific-security advice from a non-RIA, and a disclaimer can't reclassify conduct. His mandatory guardrail: **the personalized flow must not name/rank specific funds — terminate at asset-class + methodology; quarantine the named-fund ranking inside the standalone Project 1.** Notably, Finance Domain *independently* arrived next door (only the equity slice reaches the screener; framed as methodology). → Cross-examine whether a bounded, opt-in, methodology-framed screener satisfies the guardrail.
- **B — OPPORTUNITY COST (→ Veer's call).** Recruiter + Devil's Advocate: a SQL/RAG project fills a *visible* skill gap; this deepens the "wealth specialist" impression he already has. Counter (Technical): it's an **8–12h build, zero new deps** — a small bet, not a month-long detour. Veer has already directed that we build it now; the honest move is to surface the dissent, frame the cost, and queue RAG next.
- **C — Wizard vs native multipage (resolved by chair).** Technical proposed Streamlit's native `pages/` (exposes a jump-anywhere sidebar); UX wants an *enforced linear* flow. **Resolution: single entry-point app with `st.session_state`-driven step rendering; hide the native page switcher.** Keeps the guided "can't get lost" feel while reusing the shared library.

## Chair's provisional direction (pending Round 2 + Veer)
Build the unified **goal-first** flow on Streamlit, flagship-on-top, with mandates 1–3 baked in, the compliance design from Round 2, and the RAG project queued next.
