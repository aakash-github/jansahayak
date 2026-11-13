"""Offline pipeline: raw docs -> section-aware chunks -> (optional) embeddings.

Usage (from repo root):
    pip install -r backend/requirements.txt pypdf
    python scripts/ingest.py

Put source files in backend/data/raw/ named <SCHEME_ID>__anything.pdf / .txt
(e.g. FARM-01__pmkisan_guidelines.pdf). Without raw files, chunks are built from schemes.json.
Writes backend/data/chunks.json and backend/data/embeddings.npy.
"""
import json
import re
from pathlib import Path

DATA = Path(__file__).resolve().parent.parent / "backend" / "data"
SECTIONS = ["eligibility", "benefit", "document", "how to apply", "application", "exclusion", "faq"]
CHUNK_WORDS, OVERLAP = 300, 50  # ~400 tokens, under the embedding model's 512-token limit


def section_of(text: str) -> str:
    head = text[:200].lower()
    return next((s for s in SECTIONS if s in head), "general")


MAX_TOKENS = 500  # the embedding model accepts at most 512 tokens
_tok = None


def _tokens(text: str) -> int:
    global _tok
    if _tok is None:
        from fastembed import TextEmbedding
        _tok = TextEmbedding("BAAI/bge-small-en-v1.5").model.tokenizer
        _tok.no_truncation()
    return len(_tok.encode(text).ids)


def _fit(piece: str) -> list[str]:
    """Badly extracted PDF text (missing spaces, tables) can be huge in tokens: halve until it fits."""
    if _tokens(piece) <= MAX_TOKENS:
        return [piece]
    mid = len(piece) // 2
    return _fit(piece[:mid]) + _fit(piece[mid:])


def split(text: str) -> list[str]:
    words = text.split()
    pieces = [" ".join(words[i:i + CHUNK_WORDS]) for i in range(0, max(len(words), 1), CHUNK_WORDS - OVERLAP)]
    return [p for piece in pieces for p in _fit(piece)]


def main():
    schemes = {s["scheme_id"]: s for s in json.loads((DATA / "schemes.json").read_text(encoding="utf-8"))}
    # file name -> its entry in sources.json (for the exact PDF link and a readable title)
    from download_pdfs import file_name
    meta = {file_name(it): it for it in json.loads((DATA / "sources.json").read_text(encoding="utf-8"))}
    chunks = []
    for f in sorted((DATA / "raw").glob("*")):
        sid = f.name.split("__")[0]
        if sid not in schemes:
            continue
        pages = []
        if f.suffix.lower() == ".pdf":
            from pypdf import PdfReader
            pages = [(i + 1, p.extract_text() or "") for i, p in enumerate(PdfReader(f).pages)]
        elif f.suffix.lower() in (".txt", ".md"):
            pages = [(None, f.read_text(encoding="utf-8"))]
        src = meta.get(f.name, {})
        title = src.get("scheme_name") or f"{schemes[sid]['scheme_name']} - {f.stem}"
        for page, text in pages:
            text = re.sub(r"\s+", " ", text).strip()
            if len(text) < 80:  # blank or scanned page, nothing to search
                continue
            for piece in split(text):
                chunks.append({"scheme_id": sid, "title": title, "section": section_of(piece), "page": page,
                               "text": piece, "source_url": src.get("pdf_url") or schemes[sid]["source_url"]})
    # Fallback seed chunks from the catalogue so retrieval works on day 1.
    for sid, s in schemes.items():
        if not any(c["scheme_id"] == sid for c in chunks):
            for section, text in [("benefit", s["benefit"]),
                                  ("eligibility", "; ".join(r["text"] for r in s["rules"])),
                                  ("document", "Documents: " + ", ".join(s["required_documents"]))]:
                chunks.append({"scheme_id": sid, "title": s["scheme_name"], "section": section, "page": None,
                               "text": f"{s['scheme_name']} {section}: {text}", "source_url": s["source_url"]})
    for i, c in enumerate(chunks):
        c["id"] = i
    (DATA / "chunks.json").write_text(json.dumps(chunks, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"{len(chunks)} chunks written")
    try:
        import sys

        import numpy as np
        sys.path.insert(0, str(DATA.parent))
        from app import embed  # course embedding API, local model as fallback
        vecs = embed.embed([c["text"] for c in chunks], timeout=60)
        np.save(DATA / "embeddings.npy", vecs)
        print("embeddings:", vecs.shape, "via", embed.last_source)
    except ImportError as e:
        print("embedding skipped (BM25 only):", e)


if __name__ == "__main__":
    main()
