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
CHUNK_WORDS, OVERLAP = 350, 50  # tune via retrieval Recall@K experiments


def section_of(text: str) -> str:
    head = text[:200].lower()
    return next((s for s in SECTIONS if s in head), "general")


def split(text: str) -> list[str]:
    words = text.split()
    return [" ".join(words[i:i + CHUNK_WORDS]) for i in range(0, max(len(words), 1), CHUNK_WORDS - OVERLAP)]


def main():
    schemes = {s["scheme_id"]: s for s in json.loads((DATA / "schemes.json").read_text(encoding="utf-8"))}
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
        for page, text in pages:
            text = re.sub(r"\s+", " ", text).strip()
            for piece in split(text) if text else []:
                chunks.append({"scheme_id": sid, "title": f"{schemes[sid]['scheme_name']} - {f.stem}",
                               "section": section_of(piece), "page": page, "text": piece,
                               "source_url": schemes[sid]["source_url"]})
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
        import numpy as np
        from fastembed import TextEmbedding
        vecs = np.array(list(TextEmbedding("BAAI/bge-small-en-v1.5").embed([c["text"] for c in chunks])))
        np.save(DATA / "embeddings.npy", vecs)
        print("embeddings:", vecs.shape)
    except ImportError:
        print("fastembed not installed; BM25 only")


if __name__ == "__main__":
    main()
