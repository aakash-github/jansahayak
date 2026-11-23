# Model compliance

Which AI models JanSahayak uses, where they run, and how the code makes sure only the approved IIT KGP services are used. Covers the Track B requirement "use the provided Qwen3-8B and bge-small-en-v1.5 services".

---

## 1. Models in use

| Role | Model | Where it runs | Approved? |
|---|---|---|---|
| Understand the user, write replies | `Qwen/Qwen3-8B` | IIT KGP hosted API (OpenAI-compatible `/chat/completions`), team endpoint, key + CA certificate | ✅ IIT KGP |
| Meaning search (documents and questions) | `bge-small-en-v1.5`, 384 dimensions | IIT KGP embedding API (VM02, `103.42.50.41:1035`), shared key + `vm02-ca.crt` | ✅ IIT KGP |
| Re-order the top 12 search results | `Xenova/ms-marco-MiniLM-L-6-v2` (small cross-encoder, ~80 MB) | Our backend server (fastembed, downloaded from Hugging Face) | ⚠️ **Not an IIT KGP model.** Disclosed here and in `/health`; can be switched off (§3) |

No other model or AI service is called. A code search finds no OpenAI, Gemini, Anthropic, Cohere or other client. LangSmith (tracing only, no model) is off unless `LANGSMITH_TRACING=true`.

The search index (`backend/data/embeddings.npy`, 2,425 × 384) was rebuilt on 2026-11-22 entirely through the IIT KGP embedding API (`ingest.py` reported `via api`, local fallback off). Rebuilding the original 33 documents reproduced the previous 1,884 vectors exactly (cosine ≥ 0.9999998), and those had been checked against `bge-small-en-v1.5` (cosine 1.0).

---

## 2. How the code enforces it

| Loophole | Guard | Where |
|---|---|---|
| The app silently runs a **fake (mock) AI** if the LLM key is missing | On Render (`RENDER` is set automatically) or with `REQUIRE_REAL_LLM=1`, the server **refuses to start** without `MODEL_BASE_URL` + `MODEL_API_KEY`. Render then keeps the last working version. Mock mode is still allowed on laptops and in unit tests | `llm.require_real_llm()` |
| A config slip swaps in **another model** | The same guard refuses any `MODEL_NAME` other than `Qwen/Qwen3-8B` in production | `llm.require_real_llm()` |
| Embeddings silently come from a **locally run model** when the API fails | The local fallback is **off by default** everywhere. If the API is down, that query uses keyword search. `EMBED_LOCAL_FALLBACK=1` is an explicit opt-in for offline laptop work; every local call is counted and warned about | `embed.py` |
| An evaluation is run with the mock AI or local embeddings | `eval/run_eval.py` **refuses to run** unless Qwen3-8B and the IIT KGP embedding API are configured and the local fallback is off (`--allow-noncompliant` forces a dry run, labelled in the results) | `run_eval.compliance_problems()` |
| A stale or wrong index is searched | Search refuses `embeddings.npy` unless it is exactly (number of chunks × 384); `ingest.py` writes the chunks and vectors together or not at all | `retrieval.py`, `scripts/ingest.py` |

---

## 3. The reranker decision

The reranker improves search ordering (see [RAG_AND_EMBEDDINGS.md](RAG_AND_EMBEDDINGS.md#7-how-good-is-it)), but it is a third model running on our own server.

- **Turn it off:** set `RERANKER=off` (Render env var, already listed in `render.yaml` as `"on"`). Search then uses keyword search + IIT KGP embeddings + RRF only. No code change is needed.
- **Status:** awaiting confirmation from the course team whether it is allowed. If not, set `RERANKER=off` and re-run `eval/run_eval.py` and `eval/retrieval_eval.py` to report the effect.

---

## 4. How to check it (evidence)

| Where | What it shows |
|---|---|
| `GET /health` → `models` | LLM model + endpoint host + mock flag; embedding model + endpoint host, local fallback on/off, call counts (`api` / `local` / `failed`); index size; reranker on/off. **No keys.** |
| Every chat reply → `trace` | `embed_source` (`api` / `local` / `failed` / `off` / `none`) and `reranker` (true/false) for that request |
| `eval/results/latest.md` → "Models used (compliance)" | The models and endpoints used in the run, embedding calls by source, queries by embedding source |
| `eval/results/latest.csv` → `embed` column | Embedding source per query |
| `python -m pytest backend/tests -q` | `test_compliance.py` tests every guard above |
