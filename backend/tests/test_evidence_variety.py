"""Evidence variety: one long PDF must not take every evidence slot. Run:  python -m pytest backend/tests -q"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from app import retrieval  # noqa: E402

# fake index: chunks 0-3 from doc A, 4-5 from doc B, 6 from doc C
FAKE = [{"source_url": u, "text": "", "scheme_id": "X"} for u in "AAAABBC"]


def _set(monkeypatch):
    monkeypatch.setattr(retrieval, "CHUNKS", FAKE)


def test_cap_two_per_document(monkeypatch):
    _set(monkeypatch)
    # A dominates the ranking; the cap lets B and C in, best-first order kept
    assert retrieval.diverse([0, 1, 2, 3, 4, 6, 5], 4, per_doc=2) == [0, 1, 4, 6]


def test_backfill_when_few_documents(monkeypatch):
    _set(monkeypatch)
    # only doc A matched: still return k chunks (a scheme with a single PDF)
    assert retrieval.diverse([0, 1, 2, 3], 4, per_doc=2) == [0, 1, 2, 3]
    # A and one B: 2 from A + 1 from B, then the best leftover A chunk fills the last slot, in rank order
    assert retrieval.diverse([0, 1, 2, 4, 3], 4, per_doc=2) == [0, 1, 2, 4]


def test_cap_off(monkeypatch):
    _set(monkeypatch)
    assert retrieval.diverse([0, 1, 2, 3, 4], 4, per_doc=0) == [0, 1, 2, 3]


def test_default_cap_is_two():
    assert retrieval.MAX_PER_DOC == 2
