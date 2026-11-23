"""Model-compliance guards (no AI calls). Run:  python -m pytest backend/tests -q

  - embeddings come from the IIT KGP API only; the local model needs an explicit opt-in and is counted
  - production refuses to start with the mock LLM or a different model
  - the reranker (not an IIT KGP model) is disclosed and can be switched off
  - /health, traces and eval results show which models served each request; no keys are exposed
  - eval/run_eval.py refuses a non-compliant setup
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT.parent / "eval"))
import numpy as np  # noqa: E402
import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app import embed, llm, retrieval  # noqa: E402
from app.main import app  # noqa: E402


# ---------- embeddings: API only unless opted in ----------

def test_no_api_and_no_fallback_raises(monkeypatch):
    monkeypatch.setattr(embed, "BASE_URL", "")
    monkeypatch.setattr(embed, "LOCAL_FALLBACK", False)
    before = embed.STATS["failed"]
    with pytest.raises(embed.EmbeddingUnavailable):
        embed.embed(["query"])
    assert embed.last_source == "failed" and embed.STATS["failed"] == before + 1


def test_api_failure_never_switches_to_local_by_default(monkeypatch):
    monkeypatch.setattr(embed, "BASE_URL", "https://example.invalid/v1")
    monkeypatch.setattr(embed, "API_KEY", "k")
    monkeypatch.setattr(embed, "LOCAL_FALLBACK", False)

    def down(*a, **k):
        raise ConnectionError("VM02 down")

    def local(*a, **k):
        raise AssertionError("local model must not be used")
    monkeypatch.setattr(embed, "_api", down)
    monkeypatch.setattr(embed, "_local_embed", local)
    with pytest.raises(embed.EmbeddingUnavailable, match="VM02 down"):
        embed.embed(["query"])


def test_local_model_only_with_opt_in_and_is_counted(monkeypatch):
    monkeypatch.setattr(embed, "BASE_URL", "")
    monkeypatch.setattr(embed, "LOCAL_FALLBACK", True)
    monkeypatch.setattr(embed, "_local_embed", lambda texts: np.zeros((len(texts), 384), dtype=np.float32))
    before = embed.STATS["local"]
    assert embed.embed(["q"]).shape == (1, 384)
    assert embed.last_source == "local" and embed.STATS["local"] == before + 1


def test_api_calls_are_counted(monkeypatch):
    monkeypatch.setattr(embed, "BASE_URL", "https://example.invalid/v1")
    monkeypatch.setattr(embed, "API_KEY", "k")
    monkeypatch.setattr(embed, "_api", lambda texts, timeout: np.ones((len(texts), 384), dtype=np.float32))
    before = embed.STATS["api"]
    embed.embed(["q"])
    assert embed.last_source == "api" and embed.STATS["api"] == before + 1


def test_search_still_works_on_keywords_when_embeddings_unavailable(monkeypatch):
    monkeypatch.setattr(embed, "BASE_URL", "")
    monkeypatch.setattr(embed, "LOCAL_FALLBACK", False)
    assert retrieval.search("crop insurance premium", ["FARM-02"], k=4)


def test_index_matches_chunks_and_bge_small():
    assert retrieval.status()["dense_index"] == [len(retrieval.CHUNKS), 384]


# ---------- LLM: no mock or other model in production ----------

def test_production_refuses_mock_llm():
    with pytest.raises(RuntimeError, match="mock"):
        llm.require_real_llm({"RENDER": "true"}, mock=True)
    with pytest.raises(RuntimeError, match="mock"):
        llm.require_real_llm({"REQUIRE_REAL_LLM": "1"}, mock=True)


def test_production_refuses_other_model():
    with pytest.raises(RuntimeError, match="Qwen/Qwen3-8B"):
        llm.require_real_llm({"RENDER": "true", "MODEL_NAME": "gpt-4o"}, mock=False)


def test_production_ok_with_real_qwen_and_dev_allows_mock():
    llm.require_real_llm({"RENDER": "true", "MODEL_NAME": "Qwen/Qwen3-8B"}, mock=False)
    llm.require_real_llm({}, mock=True)                                  # laptop / unit tests
    llm.require_real_llm({"RENDER": "true", "REQUIRE_REAL_LLM": "0"}, mock=True)  # explicit override


# ---------- reranker disclosure ----------

def test_reranker_switch():
    assert retrieval.reranker_enabled({}) is True
    for off in ("off", "OFF", "0", "false", "no"):
        assert retrieval.reranker_enabled({"RERANKER": off}) is False


# ---------- visibility: /health, traces ----------

def test_health_reports_models_without_secrets(monkeypatch):
    monkeypatch.setattr(llm, "API_KEY", "sk-llm-secret")
    monkeypatch.setattr(embed, "API_KEY", "sk-embed-secret")
    h = TestClient(app).get("/health").json()
    m = h["models"]
    assert m["llm"]["model"] == llm.MODEL and m["embeddings"]["model"] == "bge-small-en-v1.5"
    assert set(m["embeddings"]["calls"]) == {"api", "local", "failed"}
    assert m["search"]["reranker"] in (retrieval.RERANK_MODEL, "off")
    assert "sk-llm-secret" not in str(h) and "sk-embed-secret" not in str(h)


def test_trace_records_embedding_source(monkeypatch):
    monkeypatch.setattr(embed, "BASE_URL", "")
    monkeypatch.setattr(embed, "LOCAL_FALLBACK", False)
    c = TestClient(app)
    r = c.post("/api/chat", json={"message": "I am a farmer in Bihar with 2 acres"}).json()
    assert r["trace"]["embed_source"] == "failed"  # no API in this test: shown honestly, never 'local'
    assert r["schemes"]  # still answered (keyword search)
    c.post("/api/reset", json={"session_id": r["session_id"], "message": ""})


# ---------- eval refuses non-compliant runs ----------

def test_eval_flags_noncompliant_setup(monkeypatch):
    import run_eval
    monkeypatch.setattr(llm, "MOCK", True)
    monkeypatch.setattr(embed, "LOCAL_FALLBACK", True)
    problems = " ".join(run_eval.compliance_problems())
    assert "MOCK" in problems and "EMBED_LOCAL_FALLBACK" in problems
    monkeypatch.setattr(llm, "MOCK", False)
    monkeypatch.setattr(llm, "MODEL", "Qwen/Qwen3-8B")
    monkeypatch.setattr(embed, "LOCAL_FALLBACK", False)
    monkeypatch.setattr(embed, "BASE_URL", "https://103.42.50.41:1035/v1")
    monkeypatch.setattr(embed, "API_KEY", "k")
    assert run_eval.compliance_problems() == []
