"""
build_index.py — OFFLINE, run-once indexing (not deployed).
───────────────────────────────────────────────────────────
Reads the annual-report PDFs from data/docs/, chunks + embeds them, and writes
the portable index artifacts to data/index/ (corpus_vectors.npy +
corpus_meta.json). Those artifacts ARE committed to git; the raw PDFs are not.

Usage (from the project folder):
    python scripts/build_index.py            # build the index
    python scripts/build_index.py --verify   # build, then run retrieval checks

To add a document: drop the PDF in data/docs/ and add a line to MANIFEST below.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

# Windows consoles default to cp1252 and choke on the box-drawing / ✓ glyphs
# used below; force UTF-8 so this script runs cleanly cross-platform.
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from document_processor import process_pdf  # noqa: E402
from vector_store import (  # noqa: E402
    build_store_from_corpus,
    embed_texts,
    save_corpus,
)

DOCS_DIR = PROJECT_ROOT / "data" / "docs"
INDEX_DIR = PROJECT_ROOT / "data" / "index"

# filename in data/docs/  →  (company, year, human label)
MANIFEST = {
    "infosys_fy2024.pdf": ("Infosys", "FY2024", "Infosys Annual Report FY2024"),
    "hdfc_bank_fy2024.pdf": ("HDFC Bank", "FY2024", "HDFC Bank Annual Report FY2024"),
}

# Sanity-check queries for --verify: (query, company we expect to dominate).
VERIFY_QUERIES = [
    ("What was the bank's gross NPA ratio?", "HDFC Bank"),
    ("operating margin for the year", "Infosys"),
    ("revenue by geography", "Infosys"),
    ("dividend declared", None),
    ("key risk factors", None),
]


def build() -> None:
    all_chunks = []
    missing = []
    for filename, (company, year, label) in MANIFEST.items():
        pdf_path = DOCS_DIR / filename
        if not pdf_path.exists():
            missing.append(filename)
            continue
        print(f"  • {company} {year}: reading {filename} …")
        chunks = process_pdf(pdf_path, company=company, year=year, document_label=label)
        print(f"      {len(chunks)} chunks")
        all_chunks.extend(chunks)

    if missing:
        print("\n  ⚠️  Missing PDFs (skipped):")
        for m in missing:
            print(f"      - data/docs/{m}")
        print("     Download the annual reports into data/docs/ and re-run.")

    if not all_chunks:
        print("\n  ✗ No chunks produced — nothing to index. Add PDFs first.")
        sys.exit(1)

    print(f"\n  Embedding {len(all_chunks)} chunks (first run downloads the model)…")
    vectors = embed_texts([c.text for c in all_chunks])
    print(f"      embeddings shape: {vectors.shape}")

    save_corpus(all_chunks, vectors, INDEX_DIR)
    print(f"\n  ✓ Saved index → {INDEX_DIR.relative_to(PROJECT_ROOT)}/")
    print("      corpus_vectors.npy + corpus_meta.json  (commit these)")


def verify() -> None:
    print("\n  Verifying retrieval against the built index…")
    store = build_store_from_corpus(INDEX_DIR)
    print(f"      store holds {store.count()} chunks from {store.companies()}")
    for query, expected in VERIFY_QUERIES:
        hits = store.search(query, top_k=3)
        top = hits[0] if hits else None
        tag = f"{top['company']} p.{top['page']} (sim {top['similarity']})" if top else "—"
        flag = ""
        if expected and top and top["company"] != expected:
            flag = f"  ⚠️ expected {expected}"
        print(f"      Q: {query!r}\n         → {tag}{flag}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--verify", action="store_true", help="run retrieval checks after building")
    args = ap.parse_args()

    print("Building financial-document index\n" + "─" * 40)
    build()
    if args.verify:
        verify()
    print("\nDone.")
