"""Search quality check: does document search find the right scheme's PDF?

Each question below is written WITHOUT the scheme's name, so search has to understand it.
We search all 1,884 chunks (no scheme filter) and check if the expected scheme is in the results.
It compares 3 setups, so you can see what each search layer adds.

Run from the repo root (needs backend/.env for the embedding API):
    backend/.venv/Scripts/python eval/retrieval_eval.py
Run it again after adding PDFs. If "top 4" drops, look at the MISS lines.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))
from app import embed, retrieval  # noqa: E402

# (question, scheme whose PDF should come up). Add a line when you add a scheme.
QUESTIONS = [
    ("crop damaged by unseasonal rain, how to claim insurance", "FARM-02"),
    ("6000 rupees per year income support to farmer families", "FARM-01"),
    ("monthly pension of 3000 for small farmers after 60", "FARM-04"),
    ("subsidy for drip and sprinkler irrigation", "FARM-05"),
    ("buy tractor or farm machinery with subsidy", "FARM-06"),
    ("women self help group drone for spraying", "FARM-07"),
    ("horticulture development fruits vegetables", "FARM-10"),
    ("agriculture graduates set up agri clinic", "FARM-09"),
    ("scholarship for girl students in technical degree AICTE", "STU-02"),
    ("scholarship for differently abled students in diploma", "STU-03"),
    ("orphan students scholarship tuition fee", "STU-04"),
    ("class 8 merit scholarship for economically weaker students", "STU-10"),
    ("seed funding for early stage startup incubator", "ENT-04"),
    ("collateral free loan guarantee for MSME", "ENT-02"),
    ("micro food processing unit credit linked subsidy", "ENT-03"),
]

SETUPS = [("Keywords only (BM25)", False, False),
          ("Keywords + meaning", True, False),
          ("Keywords + meaning + re-rank (live)", True, True)]


def run(use_dense: bool, use_rerank: bool, show_misses: bool) -> tuple[int, int]:
    saved = retrieval._vectors, retrieval._reranker
    if not use_dense:
        retrieval._vectors = None
    if not use_rerank:
        retrieval._reranker = None
    top1 = top4 = 0
    try:
        for q, want in QUESTIONS:
            got = [c["scheme_id"] for c in retrieval.search(q, None, k=4)]
            top1 += got[:1] == [want]
            top4 += want in got
            if show_misses and want not in got:
                print(f"   MISS  {q!r}: wanted {want}, got {got}")
    finally:
        retrieval._vectors, retrieval._reranker = saved
    return top1, top4


if __name__ == "__main__":
    n = len(QUESTIONS)
    print(f"{n} questions, {len(retrieval.CHUNKS)} chunks\n")
    print(f"{'Setup':38s} {'right scheme 1st':>17s} {'in top 4':>9s}")
    for name, dense, rerank in SETUPS:
        t1, t4 = run(dense, rerank, show_misses=rerank)
        print(f"{name:38s} {f'{t1}/{n}':>17s} {f'{t4}/{n}':>9s}")
    print(f"\nquestion embeddings came from: {embed.last_source}")
