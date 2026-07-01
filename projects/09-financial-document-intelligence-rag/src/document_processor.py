"""
document_processor.py
─────────────────────
Turns a raw PDF (an annual report) into a list of small, searchable text
"chunks", each tagged with where it came from (company / document / page).

WHY THIS STEP EXISTS (RAG concept #1 — "chunking"):
An LLM cannot read a 300-page annual report in one go — it has a limited
context window, and even if it fit, stuffing the whole report into every
question would be slow and expensive. Instead we split the report into many
small passages ("chunks") ahead of time. Later, when the user asks a question,
we only retrieve the handful of chunks that are actually relevant and send
*those* to the LLM. This file does the splitting; vector_store.py does the
retrieving.

WHY WE KEEP PAGE NUMBERS:
Every chunk remembers which page it came from. That is what lets the final
answer say "[Infosys, p.142]" — the citation that makes the tool trustworthy
instead of a black box that could be hallucinating.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import fitz  # PyMuPDF — fast, pure-python PDF text extraction


# ── Data structure for one chunk ─────────────────────────────────────────────

@dataclass
class Chunk:
    """One retrievable passage of text plus where it came from."""
    text: str
    metadata: dict = field(default_factory=dict)  # company, document, page, year


# ── Tuning knobs ─────────────────────────────────────────────────────────────
# The embedding model (bge-small) accepts up to 512 tokens. We aim well under
# that. We size chunks in *words* because that's cheap to compute and a decent
# proxy: English averages ~1.3 tokens per word, so ~300 words ≈ ~390 tokens —
# comfortably inside the limit with headroom for the model's special tokens.
WORDS_PER_CHUNK = 300
WORD_OVERLAP = 40  # each chunk repeats the last 40 words of the previous one
MIN_CHUNK_WORDS = 20  # drop tiny fragments (page numbers, isolated headings)


def _clean(text: str) -> str:
    """Collapse the ragged whitespace PDFs produce into single spaces."""
    return " ".join(text.split())


def _chunk_page_text(words: list[str]) -> list[str]:
    """
    Slide a fixed-size window across one page's words to produce overlapping
    chunks.

    WHY OVERLAP: a fact can straddle a chunk boundary (e.g. "...net profit rose
    to" | "₹61,000 crore..."). Without overlap, neither chunk contains the whole
    fact and retrieval misses it. Repeating a few words at each seam means any
    single fact lands intact inside at least one chunk.
    """
    if len(words) <= WORDS_PER_CHUNK:
        return [" ".join(words)] if len(words) >= MIN_CHUNK_WORDS else []

    chunks: list[str] = []
    step = WORDS_PER_CHUNK - WORD_OVERLAP  # how far the window advances each time
    for start in range(0, len(words), step):
        window = words[start : start + WORDS_PER_CHUNK]
        if len(window) >= MIN_CHUNK_WORDS:
            chunks.append(" ".join(window))
        if start + WORDS_PER_CHUNK >= len(words):
            break  # last window already reached the end; don't emit a dupe tail
    return chunks


def process_pdf(
    pdf_path: str | Path,
    company: str,
    year: str,
    document_label: str | None = None,
) -> list[Chunk]:
    """
    Read a PDF and return a flat list of Chunk objects.

    Parameters
    ----------
    pdf_path : path to the PDF on disk
    company  : e.g. "Infosys" — shown in citations and used to filter searches
    year     : e.g. "FY2024"
    document_label : human name for the source, defaults to "<company> <year> Annual Report"
    """
    pdf_path = Path(pdf_path)
    if not pdf_path.exists():
        raise FileNotFoundError(f"PDF not found: {pdf_path}")

    document_label = document_label or f"{company} {year} Annual Report"
    chunks: list[Chunk] = []

    with fitz.open(pdf_path) as doc:
        for page_index, page in enumerate(doc):
            page_num = page_index + 1  # humans count pages from 1, not 0
            raw = page.get_text("text")
            cleaned = _clean(raw)
            if not cleaned:
                continue  # blank / image-only page — nothing to embed

            words = cleaned.split()
            for passage in _chunk_page_text(words):
                chunks.append(
                    Chunk(
                        text=passage,
                        metadata={
                            "company": company,
                            "document": document_label,
                            "page": page_num,
                            "year": year,
                        },
                    )
                )

    return chunks


def process_pdf_bytes(
    data: bytes,
    company: str,
    year: str,
    document_label: str | None = None,
) -> list[Chunk]:
    """
    Same as process_pdf but reads from raw bytes instead of a file path.

    WHY: the Streamlit uploader hands us an in-memory file, not a path on disk.
    This lets a user drop in their own PDF and query it without us ever writing
    it to disk.
    """
    document_label = document_label or f"{company} {year}"
    chunks: list[Chunk] = []

    with fitz.open(stream=data, filetype="pdf") as doc:
        for page_index, page in enumerate(doc):
            page_num = page_index + 1
            cleaned = _clean(page.get_text("text"))
            if not cleaned:
                continue
            words = cleaned.split()
            for passage in _chunk_page_text(words):
                chunks.append(
                    Chunk(
                        text=passage,
                        metadata={
                            "company": company,
                            "document": document_label,
                            "page": page_num,
                            "year": year,
                        },
                    )
                )

    return chunks
