# Financial Document Intelligence (RAG)

**Ask natural-language questions about company annual reports and get answers grounded in — and citing — the actual pages of the filings.**

A Retrieval-Augmented Generation (RAG) tool over Indian annual reports. Type a question in plain English; the app searches the reports, retrieves the most relevant passages, and has an LLM write an answer where **every figure cites the company and page it came from** — so nothing is a hallucinated number you can't check.

> Works on **any PDF** (10-Ks, filings, earnings-call transcripts, research notes). Two annual reports — **Infosys FY2024** and **HDFC Bank FY2024** — come pre-indexed as a live demo, and you can upload your own PDF in the sidebar.

---

## Why this project

The rest of this portfolio is deep on Indian mutual-fund investing but shows no **document intelligence** — embeddings, vector search, and grounded LLM synthesis, the skills most "Finance Analyst + GenAI" roles name explicitly. This project adds exactly that layer, using primary-source filings instead of clean APIs.

It also pairs naturally with **Project 7 (Autonomous Equity Research)**: that one analyses a company from live market data; this one mines the company's own official disclosures.

---

## What it does

- **Semantic Q&A** over 900+ pages of annual reports — ask in plain English, no keyword matching.
- **Grounded answers with citations** — the LLM may only use the retrieved excerpts and must cite `[Company, p.PAGE]` for every claim; if the answer isn't in the documents, it says so rather than guessing.
- **Multi-document comparison** — one question can pull context from several reports at once ("compare the risk factors of both companies").
- **Bring your own PDF** — upload any filing and query it live in the same session.
- **Runs without an API key** — retrieval is fully local; a demo mode returns pre-written answers for the showcase questions plus the real retrieved passages. Add a free Groq key for live LLM synthesis of any question.

---

## How it works (the RAG pipeline)

```
                         OFFLINE (once, committed to git)
   PDFs ──► extract text ──► chunk (300-word, 40-word overlap, page-tagged)
   (fitz)                        │
                                 ▼
                          embed each chunk ─────► corpus_vectors.npy  ┐  portable
                          (fastembed / bge-small)  corpus_meta.json   ┘  index artifacts

                         AT RUNTIME (per question)
   question ──► embed ──► semantic search (ChromaDB, cosine) ──► top-k passages
                                                                     │
                                        ┌────────────────────────────┘
                                        ▼
                          LLM synthesis (Groq / Llama 3.3)
                          "answer ONLY from these excerpts, cite every figure"
                                        │
                                        ▼
                          grounded answer + the exact source passages
```

Four core ideas, one per module:

| Module | RAG concept | What it does |
|---|---|---|
| `document_processor.py` | **Chunking** | PDF → page-tagged, overlapping text chunks (`fitz`) |
| `vector_store.py` | **Embeddings + semantic search** | local ONNX embeddings (`fastembed`, bge-small) in an in-memory `ChromaDB` collection with company filtering |
| `synthesizer.py` | **Grounded generation** | Groq/Llama reads only the retrieved passages and cites each claim; graceful demo fallback |
| `demo_data.py` | — | pre-written, source-verified answers for the showcase questions (no-API-key mode) |

### Two engineering decisions worth calling out

1. **Grounding + citations over a raw chatbot.** The system prompt forbids outside knowledge and requires a `[Company, p.PAGE]` citation for every fact. The UI shows the retrieved passages next to the answer, so any number is one click from its source. This is the difference between a demo that *sounds* smart and a tool you'd actually trust with a filing.

2. **A portable index, not a committed database.** ChromaDB's on-disk format is tied to its library version — a DB built locally can fail to load on a differently-versioned host. Instead the offline build saves two version-proof artifacts (`corpus_vectors.npy` + `corpus_meta.json`, ~6 MB total) and the app rebuilds a fresh in-memory collection from them at startup. Loading precomputed vectors is instant; the app never re-embeds the 900+ pages at runtime, only the one short question the user typed.

---

## Tech stack

- **Python** · **Streamlit** (same dark design system as Projects 1/2/6)
- **PyMuPDF** (`fitz`) — PDF text extraction
- **fastembed** — local ONNX embeddings (`BAAI/bge-small-en-v1.5`), no PyTorch, no paid API, runs on CPU
- **ChromaDB** — vector store with metadata filtering
- **Groq** (Llama 3.3 70B) via the OpenAI-compatible SDK — optional; demo mode works without it

---

## Project structure

```
09-financial-document-intelligence-rag/
├── src/
│   ├── document_processor.py   # PDF → page-tagged chunks
│   ├── vector_store.py         # fastembed + ChromaDB; portable index save/load
│   ├── synthesizer.py          # Groq grounded answer + demo fallback
│   └── demo_data.py            # source-verified showcase answers
├── scripts/
│   └── build_index.py          # OFFLINE: build the committed index (run once)
├── dashboard/
│   └── app.py                  # Streamlit UI
├── data/
│   ├── docs/                   # raw PDFs (gitignored — downloaded separately)
│   └── index/                  # corpus_vectors.npy + corpus_meta.json (committed)
└── requirements.txt
```

---

## Running locally

```bash
cd projects/09-financial-document-intelligence-rag
pip install -r requirements.txt
streamlit run dashboard/app.py
```

The app works immediately in **demo mode** using the committed index. For **live LLM synthesis**, add a free key from [console.groq.com](https://console.groq.com):

```bash
cp .env.example .env      # then paste your GROQ_API_KEY
```

### Rebuilding the index (only if you change the source PDFs)

The index is already committed, so this is optional. To rebuild or add documents:

```bash
# 1. Put the annual-report PDFs in data/docs/ (see MANIFEST in build_index.py)
# 2. Build + sanity-check retrieval:
python scripts/build_index.py --verify
```

This chunks and embeds the PDFs and writes `data/index/`. First run downloads the ~130 MB embedding model once (cached thereafter).

---

## Sample questions (verified against the source reports)

| Question | Grounded answer (abridged) |
|---|---|
| *What was HDFC Bank's GNPA ratio in FY24?* | GNPA **1.24%** (vs 1.12%), net NPA **0.33%** — among the lowest in the sector `[HDFC Bank, p.211/217]` |
| *How did Infosys explain its operating margin in FY24?* | Consolidated operating margin **20.7%**, down from 21.1% `[Infosys, p.100]` |
| *What is Infosys's revenue split by geography?* | North America **60.1%**, Europe **27.6%**, RoW 9.8%, India 2.5% `[Infosys, p.10]` |
| *Compare the key risk factors disclosed by both companies.* | Infosys: client concentration, cybersecurity, talent; HDFC Bank: credit, liquidity, operational, regulatory |

---

## Honest notes / limitations

- **Citations use the PDF's physical page number** (page 1 = first page of the file), which can differ from the report's *printed* page number by a fixed offset per section. The cited page is always a real, findable location in the source PDF.
- **Retrieval quality depends on the embedding model.** `bge-small` is a strong, lightweight CPU model, but for a specific figure the answer is only as good as the top-k passages it surfaces — which is exactly why the app always shows those passages for you to verify.
- **Demo-mode answers** are pre-written for the five showcase questions (and their figures were verified against the actual reports); any other question in demo mode returns the top retrieved passage. A Groq key unlocks live synthesis for *any* question.
- Source PDFs are not committed (they're large and publicly available from the companies' investor-relations pages / annualreports.com); the committed index artifacts are all the app needs to run.

---

*Project 9 of Veer Pratap Singh's finance + GenAI portfolio.*
