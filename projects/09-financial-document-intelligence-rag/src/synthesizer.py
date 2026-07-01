"""
synthesizer.py
──────────────
The "generation" half of RAG (concept #4). Retrieval (vector_store.py) has
already found the most relevant passages; this file hands those passages plus
the user's question to an LLM and asks it to write a grounded, cited answer.

THE KEY DISCIPLINE — "grounding":
The system prompt forbids the model from using outside knowledge. It must
answer ONLY from the excerpts we supply and cite the company + page for every
claim. This is what turns a chatbot (which can confidently make things up) into
a document-Q&A tool you can trust: every sentence traces back to a real page of
a real filing, and if the answer isn't in the retrieved text, the model is told
to say so rather than guess.

Same Groq (Llama 3.3) + demo-fallback pattern as Project 2's allocation_engine.
When no API key is present the tool still runs: retrieval is fully local, so we
show the real retrieved passages with a lightly-templated answer.
"""

from __future__ import annotations

from demo_data import match_demo_answer

GROQ_MODEL = "llama-3.3-70b-versatile"

SYSTEM_PROMPT = """You are a financial-analyst assistant that answers questions \
strictly from excerpts of financial documents provided to you (annual reports, \
regulatory filings, earnings-call transcripts, research notes, and similar).

RULES:
1. Use ONLY the information in the numbered excerpts below. Do not use any \
outside knowledge or make assumptions.
2. Cite the source of every factual claim inline, using the format \
[Company, p.PAGE] taken from the excerpt's header.
3. If the excerpts do not contain enough information to answer, say so plainly: \
"The provided excerpts do not contain this information." Do not guess.
4. When the question compares two companies, structure the answer so each \
company's figures are clearly attributed.
5. Be concise and precise with numbers. Quote figures exactly as they appear.
6. Write in plain, professional prose — no preamble like "Based on the excerpts"."""


def _format_excerpts(hits: list[dict]) -> str:
    """Render retrieved chunks as a numbered, citation-tagged block."""
    lines = []
    for i, h in enumerate(hits, 1):
        header = f"[{h['company']}, p.{h['page']}]"
        lines.append(f"Excerpt {i} {header}:\n{h['text']}")
    return "\n\n".join(lines)


def build_user_message(query: str, hits: list[dict]) -> str:
    excerpts = _format_excerpts(hits)
    return (
        f"EXCERPTS:\n{excerpts}\n\n"
        f"QUESTION: {query}\n\n"
        f"Answer the question using only the excerpts above, citing "
        f"[Company, p.PAGE] for each fact."
    )


def _demo_answer(query: str, hits: list[dict]) -> dict:
    """Answer without an LLM. Retrieval is local, so the sources are REAL —
    only the synthesis step is skipped. For the showcased questions we return a
    polished pre-written answer; otherwise we stitch the top excerpts with a
    note explaining that a Groq key unlocks true synthesis."""
    canned = match_demo_answer(query)
    if canned:
        return {"answer": canned, "sources": hits, "_demo": True}

    if hits:
        top = hits[0]
        snippet = top["text"]
        if len(snippet) > 400:
            snippet = snippet[:400].rsplit(" ", 1)[0] + "…"
        answer = (
            f"**Demo mode** (no Groq API key set — showing the top retrieved "
            f"passage instead of an AI-synthesised answer).\n\n"
            f"Most relevant passage for your question, from "
            f"**[{top['company']}, p.{top['page']}]**:\n\n> {snippet}\n\n"
            f"*Add a `GROQ_API_KEY` to have the AI read all retrieved excerpts "
            f"and write a single cited answer.*"
        )
    else:
        answer = (
            "**Demo mode.** No relevant passages were found for that question "
            "in the selected documents. Try selecting a different document or "
            "rephrasing."
        )
    return {"answer": answer, "sources": hits, "_demo": True}


def synthesize(query: str, hits: list[dict], api_key: str | None) -> dict:
    """
    Produce the final answer dict: {answer, sources, _demo, [_error]}.

    `hits` is the list returned by VectorStore.search — the retrieved,
    citation-tagged passages. `api_key` decides live vs demo.
    """
    if not hits:
        return {
            "answer": "No relevant passages were found in the selected "
            "documents. Try another document or rephrase the question.",
            "sources": [],
            "_demo": api_key is None,
        }

    if not api_key:
        return _demo_answer(query, hits)

    try:
        from openai import OpenAI

        client = OpenAI(api_key=api_key, base_url="https://api.groq.com/openai/v1")
        response = client.chat.completions.create(
            model=GROQ_MODEL,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": build_user_message(query, hits)},
            ],
            temperature=0.2,  # low: we want faithful extraction, not creativity
        )
        answer = response.choices[0].message.content.strip()
        return {"answer": answer, "sources": hits, "_demo": False}

    except Exception as e:
        # Never crash the app — degrade to the demo/extractive answer.
        fallback = _demo_answer(query, hits)
        fallback["_error"] = str(e)
        return fallback
