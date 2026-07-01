"""
app.py — Financial Document Intelligence (RAG)
Ask natural-language questions about company annual reports and get answers
grounded in — and citing — the actual pages of the filings.

Pipeline per question:  embed question → semantic search (ChromaDB) →
retrieve top passages → LLM synthesises a cited answer (Groq / demo fallback).
"""

from __future__ import annotations

import html
import os
import re
import sys
from pathlib import Path

import streamlit as st

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from demo_data import EXAMPLE_QUESTIONS
from document_processor import process_pdf_bytes
from synthesizer import synthesize
from vector_store import VectorStore, build_store_from_corpus

INDEX_DIR = PROJECT_ROOT / "data" / "index"


# ── Minimal, safe markdown → HTML (answers are injected into a styled card) ───

def _inline(s: str) -> str:
    """Escape HTML, then apply inline **bold** / *italic* / `code`."""
    s = html.escape(s)
    s = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", s)
    s = re.sub(r"(?<!\*)\*(?!\*)(.+?)(?<!\*)\*(?!\*)", r"<em>\1</em>", s)
    s = re.sub(r"`(.+?)`", r"<code>\1</code>", s)
    return s


def _md_to_html(text: str) -> str:
    """Convert the small markdown subset our answers use into safe HTML."""
    blocks = re.split(r"\n\s*\n", text.strip())
    out: list[str] = []
    for block in blocks:
        lines = [ln.strip() for ln in block.splitlines() if ln.strip()]
        if not lines:
            continue
        if all(ln.startswith(("- ", "* ")) for ln in lines):
            items = "".join(f"<li>{_inline(ln[2:])}</li>" for ln in lines)
            out.append(f"<ul>{items}</ul>")
        elif all(ln.startswith(">") for ln in lines):
            quote = " ".join(_inline(ln.lstrip("> ").strip()) for ln in lines)
            out.append(f"<blockquote>{quote}</blockquote>")
        else:
            out.append("<p>" + "<br>".join(_inline(ln) for ln in lines) + "</p>")
    return "".join(out)


# ── Page config ───────────────────────────────────────────────────────────────

st.set_page_config(
    page_title="Financial Document Intelligence",
    page_icon="📑",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── CSS (shared dark design system with Projects 1/2/6) ───────────────────────

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@400;500;600;700&family=Inter:wght@400;500;600&display=swap');
@import url('https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.3/font/bootstrap-icons.min.css');

html, body, [class*="css"] {
    font-family: 'Inter', sans-serif;
    background-color: #0A0A0E !important;
    color: #E4E4E7 !important;
}
:root {
    --bg:#0A0A0E; --surf:#111116; --surf2:#18181F;
    --bdr:rgba(255,255,255,0.06); --bdr2:rgba(255,255,255,0.12);
    --rule:rgba(255,255,255,0.05);
    --t1:#F4F4F5; --t2:#A1A1AA; --t3:#71717A; --t4:#52525B;
    --acc:#818CF8; --gold:#E4C76B; --green:#10B981; --amber:#F59E0B;
}
@keyframes fadeUp { from{opacity:0;transform:translateY(14px)} to{opacity:1;transform:translateY(0)} }
@keyframes fadeIn { from{opacity:0} to{opacity:1} }

[data-testid="stAppViewContainer"], [data-testid="stMain"], [data-testid="stHeader"] {
    background-color: var(--bg) !important;
}
[data-testid="stHeader"] { background-color: transparent !important; }
[data-testid="stSidebar"] { background: var(--surf) !important; border-right:1px solid var(--bdr) !important; }
[data-testid="stWidgetLabel"] p, .stRadio label p, .stCheckbox label p {
    color: var(--t2) !important;
}
[data-testid="stCaptionContainer"] { opacity:1 !important; }
[data-testid="stCaptionContainer"] p { color: var(--t3) !important; }
.block-container { padding-top: 2.2rem !important; max-width: 940px; }

/* header */
.app-header { animation: fadeUp .6s ease both; margin-bottom: 1.6rem; }
.app-eyebrow {
    font-size:.68rem; font-weight:600; letter-spacing:.14em; text-transform:uppercase;
    color:var(--acc); margin-bottom:.5rem;
}
.app-title {
    font-family:'Space Grotesk',sans-serif; font-size:2.3rem; font-weight:700;
    letter-spacing:-.02em; color:var(--t1); line-height:1.1; margin-bottom:.4rem;
}
.app-sub { font-size:.95rem; color:var(--t3); line-height:1.6; max-width:640px; }

/* sidebar brand */
.brand { font-family:'Space Grotesk',sans-serif; font-weight:700; font-size:1.05rem;
    color:var(--t1); display:flex; align-items:center; gap:.5rem; margin-bottom:.2rem; }
.brand i { color:var(--acc); }
.brand-sub { font-size:.72rem; color:var(--t4); margin-bottom:1.2rem; }

/* status pill */
.status-pill { display:inline-flex; align-items:center; gap:.4rem; border-radius:999px;
    padding:.28rem .7rem; font-size:.72rem; font-weight:500; margin-bottom:.4rem; }
.status-live { background:rgba(16,185,129,.1); border:1px solid rgba(16,185,129,.25); color:var(--green); }
.status-demo { background:rgba(245,158,11,.1); border:1px solid rgba(245,158,11,.25); color:var(--amber); }

/* answer card */
.answer-card {
    background:var(--surf); border:1px solid var(--bdr2); border-radius:14px;
    padding:1.5rem 1.7rem; margin-top:.4rem; animation:fadeUp .5s ease both;
    line-height:1.7; color:var(--t1); font-size:.98rem;
}
.answer-card p { margin-bottom:.7rem; }
.answer-card p:last-child { margin-bottom:0; }
.answer-card strong { color:var(--t1); font-weight:600; }
.answer-card em { color:var(--t2); }
.answer-card code { background:var(--surf2); border:1px solid var(--bdr);
    border-radius:5px; padding:.05rem .3rem; font-size:.85em; color:var(--gold); }
.answer-card ul { margin:.2rem 0 .7rem 1.1rem; }
.answer-card li { margin-bottom:.3rem; }
.answer-card blockquote { border-left:2px solid var(--acc); margin:.6rem 0;
    padding:.2rem 0 .2rem .9rem; color:var(--t2); font-style:normal; }
.answer-label { font-size:.68rem; font-weight:600; letter-spacing:.12em; text-transform:uppercase;
    color:var(--acc); margin-bottom:.8rem; display:flex; align-items:center; gap:.4rem; }

/* source card */
.src-head { font-size:.68rem; font-weight:600; letter-spacing:.1em; text-transform:uppercase;
    color:var(--t3); margin:1.6rem 0 .6rem; }
.src-cite { font-family:'Space Grotesk',sans-serif; font-weight:600; font-size:.82rem; color:var(--acc); }
.src-sim { font-size:.7rem; color:var(--t4); float:right; }
.src-text { font-size:.85rem; color:var(--t2); line-height:1.6; margin-top:.3rem; }

/* empty state */
.empty { text-align:center; padding:3rem 1rem; color:var(--t3); animation:fadeIn .6s ease both; }
.empty i { font-size:2.2rem; color:var(--t4); }
.empty h3 { font-family:'Space Grotesk',sans-serif; color:var(--t2); font-weight:600;
    font-size:1.1rem; margin:.8rem 0 .4rem; }
.empty p { font-size:.85rem; max-width:420px; margin:0 auto; line-height:1.6; }
</style>
""", unsafe_allow_html=True)


# ── API key resolution (same pattern as Project 2) ────────────────────────────

def resolve_api_key() -> str | None:
    try:
        key = st.secrets.get("GROQ_API_KEY")
        if key:
            return key
    except Exception:
        pass
    try:
        from dotenv import load_dotenv
        load_dotenv(PROJECT_ROOT / ".env")
    except ImportError:
        pass
    return os.environ.get("GROQ_API_KEY") or None


# ── Load the committed index once per container ───────────────────────────────

@st.cache_resource(show_spinner=False)
def get_base_store() -> VectorStore | None:
    """Load the pre-built annual-report index. None if it hasn't been built."""
    if not (INDEX_DIR / "corpus_meta.json").exists():
        return None
    return build_store_from_corpus(INDEX_DIR)


def run_search(query: str, selected: list[str], top_k: int = 5) -> list[dict]:
    """Search the committed store and any uploaded docs, merge, keep the best."""
    hits: list[dict] = []
    base = get_base_store()
    upload: VectorStore | None = st.session_state.get("upload_store")

    base_names = set(base.companies()) if base else set()
    upload_names = set(upload.companies()) if upload else set()

    sel_base = [c for c in selected if c in base_names]
    sel_upload = [c for c in selected if c in upload_names]

    if base and sel_base:
        hits += base.search(query, top_k=top_k, companies=sel_base)
    if upload and sel_upload:
        hits += upload.search(query, top_k=top_k, companies=sel_upload)

    hits.sort(key=lambda h: h["similarity"], reverse=True)
    return hits[:top_k]


# ── Session state ─────────────────────────────────────────────────────────────

if "query_box" not in st.session_state:
    st.session_state.query_box = ""
if "do_search" not in st.session_state:
    st.session_state.do_search = False

api_key = resolve_api_key()
base_store = get_base_store()


# ── Sidebar: documents + uploader + status ────────────────────────────────────

with st.sidebar:
    st.markdown(
        '<div class="brand"><i class="bi bi-file-earmark-text"></i>FinDocIQ</div>'
        '<div class="brand-sub">RAG over annual reports</div>',
        unsafe_allow_html=True,
    )

    if api_key:
        st.markdown('<span class="status-pill status-live">'
                    '<i class="bi bi-broadcast"></i>Live AI synthesis</span>',
                    unsafe_allow_html=True)
    else:
        st.markdown('<span class="status-pill status-demo">'
                    '<i class="bi bi-info-circle"></i>Demo mode · add GROQ_API_KEY</span>',
                    unsafe_allow_html=True)

    st.markdown("###### Documents")

    selected: list[str] = []
    base_companies = base_store.companies() if base_store else []
    for name in base_companies:
        if st.checkbox(name, value=True, key=f"doc_{name}"):
            selected.append(name)

    # uploaded docs (this session only)
    upload_store: VectorStore | None = st.session_state.get("upload_store")
    if upload_store:
        for name in upload_store.companies():
            if st.checkbox(f"{name} (uploaded)", value=True, key=f"up_{name}"):
                selected.append(name)

    st.markdown("---")
    st.markdown("###### Add your own PDF")
    up = st.file_uploader("Upload an annual report / filing", type="pdf",
                          label_visibility="collapsed")
    if up is not None and st.session_state.get("last_upload") != up.name:
        with st.spinner("Indexing your PDF…"):
            chunks = process_pdf_bytes(up.read(), company=up.name.replace(".pdf", ""),
                                       year="", document_label=up.name)
            store = st.session_state.get("upload_store") or VectorStore("uploads")
            store.add_chunks_and_embed(chunks)
            st.session_state.upload_store = store
            st.session_state.last_upload = up.name
        st.success(f"Indexed {len(chunks)} passages from {up.name}")
        st.rerun()


# ── Header ────────────────────────────────────────────────────────────────────

st.markdown(
    '<div class="app-header">'
    '<div class="app-eyebrow">Retrieval-Augmented Generation</div>'
    '<div class="app-title">Financial Document Intelligence</div>'
    '<div class="app-sub">Ask a question in plain English. The tool searches the '
    'selected annual reports, retrieves the most relevant passages, and answers '
    'with a citation to the exact company and page — no hallucinated numbers.</div>'
    '</div>',
    unsafe_allow_html=True,
)

if base_store is None:
    st.markdown(
        '<div class="empty"><i class="bi bi-database-exclamation"></i>'
        '<h3>Index not built yet</h3><p>Run '
        '<code>python scripts/build_index.py</code> after placing the annual-report '
        'PDFs in <code>data/docs/</code>. You can still upload a PDF in the sidebar '
        'to try the tool now.</p></div>',
        unsafe_allow_html=True,
    )

# status line
total_docs = len(base_companies) + (len(upload_store.companies()) if upload_store else 0)
total_chunks = (base_store.count() if base_store else 0) + \
               (upload_store.count() if upload_store else 0)
if total_chunks:
    st.caption(f"🔎 {total_chunks:,} passages indexed across {total_docs} document(s)")

# ── Example questions ─────────────────────────────────────────────────────────

st.markdown("###### Try an example")
ex_cols = st.columns(len(EXAMPLE_QUESTIONS[:3]))
for i, q in enumerate(EXAMPLE_QUESTIONS[:3]):
    if ex_cols[i].button(q, key=f"ex_{i}", use_container_width=True):
        st.session_state.query_box = q
        st.session_state.do_search = True

# ── Query input ───────────────────────────────────────────────────────────────

st.text_input(
    "Your question",
    key="query_box",
    placeholder="e.g. How did Infosys explain its operating margin in FY24?",
)
if st.button("Ask", type="primary"):
    st.session_state.do_search = True


# ── Run + render ──────────────────────────────────────────────────────────────

query = st.session_state.query_box.strip()

if st.session_state.do_search and query:
    st.session_state.do_search = False

    if not selected:
        st.warning("Select at least one document in the sidebar first.")
    else:
        with st.spinner("Searching the reports…"):
            hits = run_search(query, selected, top_k=5)
            result = synthesize(query, hits, api_key)

        # answer
        badge = ""
        if result.get("_demo"):
            badge = ' · <span style="color:var(--amber)">demo answer</span>'
        st.markdown(
            f'<div class="answer-card"><div class="answer-label">'
            f'<i class="bi bi-stars"></i>Answer{badge}</div>{_md_to_html(result["answer"])}</div>',
            unsafe_allow_html=True,
        )
        if result.get("_error"):
            st.caption(f"⚠️ Live synthesis unavailable ({result['_error'][:80]}…) — showing demo answer.")

        # sources
        sources = result.get("sources", [])
        if sources:
            st.markdown('<div class="src-head">Sources · retrieved passages</div>',
                        unsafe_allow_html=True)
            for h in sources:
                label = f"{h['company']} · p.{h['page']}  —  relevance {h['similarity']}"
                with st.expander(label):
                    st.markdown(
                        f'<div class="src-text">{html.escape(h["text"])}</div>',
                        unsafe_allow_html=True,
                    )
elif not query:
    st.markdown(
        '<div class="empty"><i class="bi bi-chat-square-quote"></i>'
        '<h3>Ask a question to begin</h3>'
        '<p>Every answer is grounded in the retrieved pages and cites its source, '
        'so you can verify each figure against the original filing.</p></div>',
        unsafe_allow_html=True,
    )
