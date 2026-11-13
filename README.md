# JanSahayak

A chatbot that helps Indian citizens (farmers, students, entrepreneurs) find government schemes, check stated eligibility, and see the documents and official links they need. IIT KGP Capstone, Track B.

## Architecture

```mermaid
flowchart LR
  U[Citizen browser] --> FE["React app<br/>GitHub Pages (static)"]
  FE -- "POST /api/chat (HTTPS JSON)" --> BE["FastAPI backend<br/>Render (Docker)"]
  subgraph BE_box [Backend: holds API key + CA cert]
    BE --> G[LangGraph workflow]
    G --> T1["Eligibility rules<br/>schemes.json"]
    G --> T2["Hybrid RAG<br/>BM25 + bge-small + reranker<br/>chunks.json / embeddings.npy"]
    G --> T3[Document checklist]
    G --> T4[Official link lookup]
  end
  G -- "chat/completions" --> LLM["IIT KGP Qwen3-8B<br/>103.42.50.41:103X"]
  P["Offline: scripts/ingest.py<br/>PDFs → chunks → embeddings"] -.-> T2
```

**No separate database.** The scheme rules (`schemes.json`) and RAG index (`chunks.json`, `embeddings.npy`) are files that ship inside the backend container. Embeddings run locally with fastembed (ONNX), because the course endpoint does not provide them. Sessions live in server memory and are cleared on reset.

### Agent workflow (one chat turn)

```mermaid
flowchart TD
  A[User message] --> B["Intake agent (LLM)<br/>extract profile JSON + intent"]
  B -->|out of scope| R[Polite refusal]
  B -->|key detail missing| F["Ask ONE follow-up<br/>(user may skip)"]
  B -->|enough info| P[Planner]
  P --> E["Executor: 4 tools<br/>eligibility · RAG · docs · links"]
  E --> AN["Answer agent (LLM)<br/>only tool results, cited [S1]"]
  AN --> C{"Critic (rules)<br/>hallucinated scheme?<br/>'you are eligible'?"}
  C -->|fail, steps < 10| AN
  C -->|pass| OUT[JSON → React cards]
```

Each turn makes only 2 LLM calls, because the group key allows 1 active request at a time. Eligibility is decided by rules, never by the model.

## Run locally

```bash
# backend
cd backend
python -m venv .venv && .venv/Scripts/pip install -r requirements.txt   # mac/linux: .venv/bin/pip
cp ../.env.example .env        # fill key, URL and cert path (or leave empty for MOCK mode)
.venv/Scripts/python ../scripts/test_llm.py        # 1. prove the API works
.venv/Scripts/python ../scripts/ingest.py          # 2. build RAG index (after adding PDFs to data/raw)
.venv/Scripts/uvicorn app.main:app --reload        # 3. http://localhost:8000/health

# frontend (needs Node 20+)
cd frontend && npm install && npm run dev          # http://localhost:5173
```

## Deploy
1. **Backend → Render:** New → Blueprint → pick this repo (it reads `render.yaml`). Set `MODEL_BASE_URL`, `MODEL_API_KEY` and `FRONTEND_ORIGIN=https://<user>.github.io`, and upload the `.crt` as Secret File `ca.crt`. Then open `/health`.
2. **Frontend → GitHub Pages:** Repo Settings → Pages → Source: *GitHub Actions*. Settings → Variables → add `VITE_API_URL=https://<your-render-app>.onrender.com`. Push to `main`.

## Adding data
- Schemes and rules: `backend/data/schemes.json` (fields follow the `Scheme_Data_Schema` sheet). Set `verification_status` to `verified` only after checking against myScheme or the official guideline.
- Documents: put them in `backend/data/raw/` as `<SCHEME_ID>__name.pdf`, then run `scripts/ingest.py`. Raw PDFs are git-ignored; commit `chunks.json` and `embeddings.npy`.
- Eval: fill `gold_scheme_ids` in `eval/eval_set.csv`, then run `eval/run_eval.py`.

## Responsible AI
We say "may be eligible", never "you are eligible". We never collect Aadhaar, bank or phone numbers. Every answer shows its sources, a data-as-of date and an official link, and points to a CSC for help.
