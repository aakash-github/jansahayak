"""Hybrid retrieval: BM25 + dense (embeddings, see embed.py) fused with RRF, then optional reranker.

Index is built offline by scripts/ingest.py into data/chunks.json (+ data/embeddings.npy).
If dense/reranker models are not installed, it falls back to BM25 only.
"""
import json
from pathlib import Path

from rank_bm25 import BM25Okapi

DATA = Path(__file__).parent.parent / "data"
CHUNKS = json.loads((DATA / "chunks.json").read_text(encoding="utf-8")) if (DATA / "chunks.json").exists() else []
_bm25 = BM25Okapi([c["text"].lower().split() for c in CHUNKS]) if CHUNKS else None

RERANK_MODEL = "Xenova/ms-marco-MiniLM-L-6-v2"
_vectors = _reranker = None
try:
    import numpy as np

    from . import embed
    if (DATA / "embeddings.npy").exists():
        _vectors = np.load(DATA / "embeddings.npy")
    from fastembed.rerank.cross_encoder import TextCrossEncoder
    _reranker = TextCrossEncoder(RERANK_MODEL)
except Exception as e:  # keep the app alive on small hosts
    print("dense/rerank disabled:", e)


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
    if _vectors is not None:
        try:
            sims = _vectors @ embed.embed([query])[0]
            rankings.append(sorted(allowed, key=lambda i: -sims[i])[:20])
        except Exception as e:  # dense search is a bonus; BM25 still works
            print("dense search skipped:", e)
    cand = _rrf(rankings)[:12]
    if _reranker is not None and cand:
        scores = list(_reranker.rerank(query, [CHUNKS[i]["text"] for i in cand]))
        cand = [i for _, i in sorted(zip(scores, cand), reverse=True)]
    return [CHUNKS[i] for i in cand[:k]]
