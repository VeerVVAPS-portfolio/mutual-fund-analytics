"""
vector_store.py
───────────────
The "retrieval" half of RAG. Two jobs:

  1. EMBEDDING (RAG concept #2): turn text into a vector of numbers that
     captures its *meaning*. Two passages about "bad loans" and
     "non-performing assets" end up as nearby vectors even though they share
     no words. We use the `fastembed` library running the BAAI/bge-small-en
     model. It runs locally on CPU (ONNX) — no paid API, no PyTorch.

  2. SEARCH (RAG concept #3 — "semantic search"): given the user's question,
     embed it the same way, then ask a vector database (ChromaDB) for the
     chunks whose vectors are closest. Those are the passages most likely to
     contain the answer.

DEPLOYMENT NOTE — why we don't commit ChromaDB's own database files:
ChromaDB's on-disk format is tied to its library version; a DB built locally
can fail to load on Streamlit Cloud if the installed version differs. Instead
the offline build step (scripts/build_index.py) saves two portable, version-
proof artifacts — `corpus_vectors.npy` (the embeddings) and `corpus_meta.json`
(the text + citations) — and we rebuild a fresh *in-memory* Chroma collection
from them at startup. Loading precomputed vectors is instant; we never re-embed
the whole corpus at runtime, only the one short question the user typed.
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np

from document_processor import Chunk

EMBED_MODEL_NAME = "BAAI/bge-small-en-v1.5"
EMBED_DIM = 384  # bge-small outputs 384-dimensional vectors

# Module-level cache so the ~130MB ONNX model is loaded once per process.
_model = None


def get_model():
    """Lazily load (and cache) the fastembed model.

    Loaded lazily because the first call triggers a one-time model download;
    we don't want to pay that at import time (e.g. during tests that only
    touch chunking)."""
    global _model
    if _model is None:
        from fastembed import TextEmbedding

        _model = TextEmbedding(model_name=EMBED_MODEL_NAME)
    return _model


def embed_texts(texts: list[str]) -> np.ndarray:
    """Embed a list of strings → an (N, 384) float32 array."""
    model = get_model()
    vectors = list(model.embed(texts))  # fastembed yields one np.array per text
    return np.array(vectors, dtype=np.float32)


# ── The store ────────────────────────────────────────────────────────────────

class VectorStore:
    """A thin wrapper over an in-memory ChromaDB collection.

    We use ChromaDB (a real vector database) rather than hand-rolled numpy math
    because it gives us metadata filtering (search only inside the companies the
    user selected) and a clean add/query API — the same primitives a production
    RAG system uses."""

    def __init__(self, collection_name: str = "financial_docs"):
        import chromadb

        # EphemeralClient == lives in RAM only, gone when the process exits.
        # Perfect here: we rebuild it from committed artifacts at startup, and
        # user-uploaded PDFs should NOT persist between sessions anyway.
        self._client = chromadb.EphemeralClient()
        # We pass embeddings in ourselves, so Chroma needs no embedding function.
        self._collection = self._client.get_or_create_collection(
            name=collection_name,
            metadata={"hnsw:space": "cosine"},  # cosine similarity for text embeddings
        )
        self._next_id = 0

    # -- building the store --

    def add_chunks(self, chunks: list[Chunk], embeddings: np.ndarray) -> None:
        """Add chunks whose embeddings are already computed."""
        if not chunks:
            return
        ids = [str(self._next_id + i) for i in range(len(chunks))]
        self._next_id += len(chunks)
        self._collection.add(
            ids=ids,
            embeddings=[e.tolist() for e in embeddings],
            documents=[c.text for c in chunks],
            metadatas=[c.metadata for c in chunks],
        )

    def add_chunks_and_embed(self, chunks: list[Chunk]) -> None:
        """Embed chunks on the fly, then add them (used for uploaded PDFs)."""
        if not chunks:
            return
        vectors = embed_texts([c.text for c in chunks])
        self.add_chunks(chunks, vectors)

    # -- searching --

    def search(
        self,
        query: str,
        top_k: int = 5,
        companies: list[str] | None = None,
    ) -> list[dict]:
        """Return the top_k most relevant chunks for the query.

        If `companies` is given, restrict the search to those companies (this is
        what makes "compare Infosys and HDFC" pull only from those two docs)."""
        query_vec = embed_texts([query])[0].tolist()

        where = None
        if companies:
            # Chroma's filter DSL: match any of the selected companies.
            where = {"company": {"$in": companies}} if len(companies) > 1 else {"company": companies[0]}

        result = self._collection.query(
            query_embeddings=[query_vec],
            n_results=top_k,
            where=where,
        )

        # Chroma returns parallel lists nested one level deep (one per query).
        hits: list[dict] = []
        docs = result.get("documents", [[]])[0]
        metas = result.get("metadatas", [[]])[0]
        dists = result.get("distances", [[]])[0]
        for text, meta, dist in zip(docs, metas, dists):
            hits.append(
                {
                    "text": text,
                    "company": meta.get("company", "Unknown"),
                    "document": meta.get("document", ""),
                    "page": meta.get("page", "?"),
                    "year": meta.get("year", ""),
                    "similarity": round(1 - dist, 3),  # cosine distance → similarity
                }
            )
        return hits

    def count(self) -> int:
        return self._collection.count()

    def companies(self) -> list[str]:
        """Distinct company names currently in the store (for UI labels)."""
        got = self._collection.get(include=["metadatas"])
        names = {m.get("company") for m in got.get("metadatas", []) if m.get("company")}
        return sorted(names)


# ── Persistence of the precomputed corpus (portable artifacts) ───────────────

def save_corpus(chunks: list[Chunk], embeddings: np.ndarray, out_dir: str | Path) -> None:
    """Write the embedded corpus to disk as version-proof artifacts."""
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    np.save(out_dir / "corpus_vectors.npy", embeddings)
    meta = [{"text": c.text, **c.metadata} for c in chunks]
    (out_dir / "corpus_meta.json").write_text(
        json.dumps(meta, ensure_ascii=False), encoding="utf-8"
    )


def load_corpus(in_dir: str | Path) -> tuple[list[Chunk], np.ndarray]:
    """Load the committed corpus artifacts back into chunks + embeddings."""
    in_dir = Path(in_dir)
    vectors = np.load(in_dir / "corpus_vectors.npy")
    meta = json.loads((in_dir / "corpus_meta.json").read_text(encoding="utf-8"))
    chunks = [
        Chunk(
            text=m["text"],
            metadata={k: m[k] for k in ("company", "document", "page", "year") if k in m},
        )
        for m in meta
    ]
    return chunks, vectors


def build_store_from_corpus(in_dir: str | Path) -> VectorStore:
    """Load committed artifacts and return a ready-to-query in-memory store."""
    chunks, vectors = load_corpus(in_dir)
    store = VectorStore()
    store.add_chunks(chunks, vectors)
    return store
