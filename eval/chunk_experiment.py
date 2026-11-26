"""Chunking experiment (Track B part III): which chunk size finds the right documents best?

Re-splits the same 33 PDFs with 3 chunk sizes, embeds them with the course embedding API, swaps each
index into the live search code (BM25 + embeddings + RRF + reranker) and measures retrieval recall:

  recall@k = share of questions where a chunk of the expected scheme is in the top k results
             (search over ALL chunks, no scheme filter, raw question).

Two question sets:
  - the 15 search questions from eval/retrieval_eval.py (written without scheme names)
  - every eval_set.csv query that has gold schemes (last turn of the conversation)

Run from the repo root (~10 minutes: embedding ~6,000 chunks + reranking):
    backend/.venv/Scripts/python eval/chunk_experiment.py
Writes eval/results/chunking.md. The live index is NOT changed.
"""
import csv
import statistics
import sys
import time
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT.parent / "backend"))
sys.path.insert(0, str(ROOT.parent / "scripts"))
sys.path.insert(0, str(ROOT))

from rank_bm25 import BM25Okapi  # noqa: E402

import ingest  # noqa: E402
from app import embed, retrieval  # noqa: E402
from retrieval_eval import QUESTIONS  # noqa: E402

SIZES = [(150, 25), (300, 50), (500, 80)]  # (words per chunk, overlap); 300/50 is what we ship
CACHE = Path(__file__).resolve().parent / "results" / ".chunk_cache"  # embeddings per size (gitignored)


def eval_questions() -> list[tuple[str, list[str]]]:
    out = []
    for r in csv.DictReader(open(ROOT / "eval_set.csv", encoding="utf-8")):
        gold = [g for g in r["gold_scheme_ids"].split(";") if g.strip()]
        if gold:
            out.append((r["query"].split("||")[-1].strip(), gold))
    return out


def build_index(words: int, overlap: int):
    ingest.CHUNK_WORDS, ingest.OVERLAP = words, overlap
    chunks = ingest.build_chunks()
    CACHE.mkdir(parents=True, exist_ok=True)
    f = CACHE / f"emb_{words}_{overlap}_{len(chunks)}.npy"
    if f.exists():
        vecs = np.load(f)
    else:
        t0 = time.time()
        vecs = embed.embed([c["text"] for c in chunks], timeout=60)
        np.save(f, vecs)
        print(f"  embedded {len(chunks)} chunks in {time.time() - t0:.0f}s via {embed.last_source}", flush=True)
    return chunks, vecs


def use_index(chunks, vecs):
    retrieval.CHUNKS = chunks
    retrieval._bm25 = BM25Okapi([c["text"].lower().split() for c in chunks])
    retrieval._vectors = vecs


def recall(questions, k_list=(1, 4, 10)):
    hits = {k: [] for k in k_list}
    ms = []
    for q, gold in questions:
        t0 = time.perf_counter()
        top = [c["scheme_id"] for c in retrieval.search(q, None, k=max(k_list))]
        ms.append((time.perf_counter() - t0) * 1000)
        for k in k_list:
            hits[k].append(sum(g in top[:k] for g in gold) / len(gold))
    return {k: 100 * statistics.mean(v) for k, v in hits.items()}, statistics.median(ms)


def main():
    search_qs = [(q, [sid]) for q, sid in QUESTIONS]
    eval_qs = eval_questions()
    rows = []
    for words, overlap in SIZES:
        print(f"chunk size {words} words, overlap {overlap}", flush=True)
        chunks, vecs = build_index(words, overlap)
        use_index(chunks, vecs)
        r_search, ms1 = recall(search_qs)
        r_eval, ms2 = recall(eval_qs)
        lens = [len(c["text"].split()) for c in chunks]
        rows.append({"size": f"{words} / {overlap}", "chunks": len(chunks), "avg_words": statistics.mean(lens),
                     "s": r_search, "e": r_eval, "ms": statistics.median([ms1, ms2]),
                     "mb": vecs.nbytes / 1e6})
        print(f"  search set r@1/4/10 = {r_search}  eval set = {r_eval}", flush=True)

    best = max(rows, key=lambda r: (r["e"][4] + r["s"][4], r["e"][10]))
    L = [f"# Chunking experiment ({time.strftime('%Y-%m-%d %H:%M')})", "",
         "Same 33 PDFs, same search (BM25 + embeddings + RRF + reranker), only the chunk size changes. "
         "Search runs over all chunks with no scheme filter. Made by `eval/chunk_experiment.py`.", "",
         f"- **Search set:** {len(search_qs)} questions written without scheme names (`eval/retrieval_eval.py`)",
         f"- **Eval set:** {len(eval_qs)} queries from `eval/eval_set.csv` that have gold schemes (last turn)", "",
         "| Chunk size (words / overlap) | Chunks | Avg words | Search set recall@1 / @4 / @10 | Eval set recall@1 / @4 / @10 | Search time p50 | Index size |",
         "|---|---|---|---|---|---|---|"]
    for r in rows:
        tag = " **(shipped)**" if r["size"].startswith("300") else ""
        L.append(f"| {r['size']}{tag} | {r['chunks']:,} | {r['avg_words']:.0f} | "
                 f"{r['s'][1]:.0f}% / {r['s'][4]:.0f}% / {r['s'][10]:.0f}% | "
                 f"{r['e'][1]:.0f}% / {r['e'][4]:.0f}% / {r['e'][10]:.0f}% | {r['ms'] / 1000:.1f} s | {r['mb']:.1f} MB |")
    L += ["", f"Best recall@4 overall: **{best['size']} words**.", "",
          "Notes: chunks are also capped at 500 tokens (the embedding model's limit), so some long chunks are split "
          "further. The reranker reads the first 1,500 characters of each chunk to fit in Render's 512 MB memory, "
          "so it sees only part of a 500-word chunk."]
    md = "\n".join(L) + "\n"
    (ROOT / "results" / "chunking.md").write_text(md, encoding="utf-8")
    print("\n" + md)


if __name__ == "__main__":
    main()
