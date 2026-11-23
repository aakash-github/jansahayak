"""Hybrid retrieval: BM25 + dense (embeddings, see embed.py) fused with RRF, then optional reranker.

Index is built offline by scripts/ingest.py into data/chunks.json (+ data/embeddings.npy).
If dense/reranker models are not available, it falls back to BM25 only.

Model compliance: the reranker (a small MiniLM cross-encoder, run on our server) is NOT one of the
IIT KGP models. It is disclosed in /health and eval results and can be switched off with RERANKER=off
(search then uses BM25 + course embeddings only). See docs/MODEL_COMPLIANCE.md.
"""
import json
import os
from pathlib import Path

from rank_bm25 import BM25Okapi

from . import trace

DATA = Path(__file__).parent.parent / "data"
CHUNKS = json.loads((DATA / "chunks.json").read_text(encoding="utf-8")) if (DATA / "chunks.json").exists() else []
_bm25 = BM25Okapi([c["text"].lower().split() for c in CHUNKS]) if CHUNKS else None

RERANK_MODEL = "Xenova/ms-marco-MiniLM-L-6-v2"
# evidence variety: at most this many of the k evidence chunks may come from one PDF (0 = no cap)
MAX_PER_DOC = int(os.environ.get("MAX_CHUNKS_PER_DOC", "2"))


def reranker_enabled(env=os.environ) -> bool:
    return env.get("RERANKER", "on").strip().lower() not in ("off", "0", "false", "no")


RERANKER_ON = reranker_enabled()
_vectors = _reranker = embed = None
try:
    import numpy as np

    from . import embed
    if (DATA / "embeddings.npy").exists():
        _vectors = np.load(DATA / "embeddings.npy")
        if _vectors.shape != (len(CHUNKS), 384):  # index must match the chunks row for row, bge-small = 384
            print(f"dense search disabled: embeddings.npy is {_vectors.shape}, expected ({len(CHUNKS)}, 384)")
            _vectors = None
except Exception as e:  # keep the app alive on small hosts
    print("dense search disabled:", e)
if RERANKER_ON:
    try:
        from fastembed.rerank.cross_encoder import TextCrossEncoder
        _reranker = TextCrossEncoder(RERANK_MODEL, threads=1)  # 1 thread keeps memory low on Render free (512 MB)
    except Exception as e:
        print("reranker disabled:", e)


def status() -> dict:
    """What search is running with (for /health and eval results)."""
    return {"bm25": _bm25 is not None, "chunks": len(CHUNKS),
            "dense_index": None if _vectors is None else list(_vectors.shape),
            "reranker": RERANK_MODEL if _reranker is not None else "off"}


def _rrf(rankings: list[list[int]], k: int = 60) -> list[int]:
    score: dict[int, float] = {}
    for ranking in rankings:
        for pos, idx in enumerate(ranking):
            score[idx] = score.get(idx, 0) + 1 / (k + pos + 1)
    return sorted(score, key=score.get, reverse=True)


def search(query: str, scheme_ids: list[str] | None = None, k: int = 4) -> list[dict]:
    """Tool 2: return top-k evidence chunks with source metadata."""
    if not CHUNKS:
        return []
    allowed = [i for i, c in enumerate(CHUNKS) if not scheme_ids or c["scheme_id"] in scheme_ids]
    bm = _bm25.get_scores(query.lower().split())
    rankings = [sorted(allowed, key=lambda i: -bm[i])[:20]]
    source = "off"  # which embedding source served this search: api | local | failed | off (no index)
    if _vectors is not None:
        try:
            sims = _vectors @ embed.embed([query])[0]
            rankings.append(sorted(allowed, key=lambda i: -sims[i])[:20])
            source = embed.last_source
        except Exception as e:  # dense search is a bonus; BM25 still works
            source = "failed"
            print("dense search skipped:", e)
    trace.put("embed_source", source)
    cand = _rrf(rankings)[:12]
    trace.put("reranker", _reranker is not None)
    if _reranker is not None and cand:
        # small batches + first ~1500 chars of each chunk: scoring 12 full chunks at once used ~270 MB
        scores = list(_reranker.rerank(query, [CHUNKS[i]["text"][:1500] for i in cand], batch_size=2))
        cand = [i for _, i in sorted(zip(scores, cand), reverse=True)]
    return [CHUNKS[i] for i in diverse(cand, k)]


def diverse(ranked: list[int], k: int, per_doc: int | None = None) -> list[int]:
    """Pick the top k, but at most per_doc chunks from one document, so one long PDF cannot take
    every evidence slot. Best-first order is kept. If there are too few other documents, the slots
    are back-filled with the next best chunks (so a scheme with a single PDF still gets k chunks)."""
    per_doc = MAX_PER_DOC if per_doc is None else per_doc
    if per_doc <= 0:
        return ranked[:k]
    picked, extra, count = [], [], {}
    for i in ranked:
        doc = CHUNKS[i].get("source_url") or CHUNKS[i].get("title")
        if count.get(doc, 0) < per_doc:
            count[doc] = count.get(doc, 0) + 1
            picked.append(i)
        else:
            extra.append(i)
        if len(picked) == k:
            break
    if len(picked) < k:
        keep = set(picked + extra[: k - len(picked)])
        picked = [i for i in ranked if i in keep]
    return picked
