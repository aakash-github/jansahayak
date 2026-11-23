# Capstone submission: JanSahayak (Track B)

This folder is the **starting point for reviewers and the team**. It maps each part of the Track B brief to what we built and where to find it. Most files live elsewhere in the repo; the links point to them.

- **Live app:** https://aakash-github.github.io/jansahayak/
- **Start here to understand the system:** [How it works (simplified)](../docs/HOW_IT_WORKS_SIMPLIFIED.md): every piece on one page, with diagrams

---

## Where we stand

```
I   Spec + eval set        █████████░  spec + 99 gold queries
II  Prompting baseline     █████████░  4 strategies vs agent system
III RAG                    ███████░░░  hybrid search + reranker + citations; chunk-size experiment to do
IV  Agentic layer          █████████░  planner → executor → critic, 4 tools, memory
V   Eval + observability   █████████░  92% accuracy, failure types, traces
VI  Ship + responsible AI  ██████░░░░  live, privacy, refusals; rate limiting + caching to do
```

---

## Brief → what we built → where

| Part | The brief asks for | What we have | Where |
|---|---|---|---|
| **I. Spec** | Problem, users, scope, what is correct | One-page spec | [SPEC.md](SPEC.md) |
| **I. Eval set** | 60–100 queries with gold answers | 99 queries: find, focus (25, incl. 7 answerable only from documents added 2026-11-22), multi-turn / multi-step (9), ask, refuse, safety (15, incl. 10 prompt-injection / personal-data); 8 in Hindi. Latest run: 92% (91/99), see [latest results](../eval/results/latest.md) | [eval/eval_set.csv](../eval/eval_set.csv) |
| **II. Prompting baseline** | One prompt, ≥ 3 strategies, how the small model breaks | 4 strategies (zero-shot, few-shot, chain-of-thought, decomposition). Best 76% vs agent system 90% | [EVALUATION.md §7](../docs/EVALUATION.md#7-prompting-baseline-one-prompt-vs-the-agent-system) · [results](../eval/results/prompting.md) |
| **III. RAG** | Index official documents, chunking, hybrid search, reranker, citations, retrieval measured separately | 67 official PDFs → 2,425 chunks (34 added 2026-11-22, de-duplicated; still a deviation from the 500–2,000 target); BM25 + embeddings + RRF + cross-encoder reranker + max 2 evidence chunks per PDF; [S1] citations; recall@4/@10 | [RAG_AND_EMBEDDINGS.md](../docs/RAG_AND_EMBEDDINGS.md) · [retrieval_eval.py](../eval/retrieval_eval.py) |
| **IV. Agents** | ≥ 3 tools, planner → executor → critic, state, error handling | LangGraph: intake → planner → executor → answer → critic → follow-up. The planner writes a plan (tools, inputs, reasons); the executor runs it step by step, passing results between steps (e.g. "find my schemes and the documents for the best one"); plan and step log in every trace. Tools: eligibility, search, documents, links, pick_best. Session memory, JSON retries, step cap | [HOW_IT_WORKS.md](../docs/HOW_IT_WORKS.md) · [agents.py](../backend/app/agents.py) |
| **V. Evaluation** | Metrics, failure taxonomy, tracing | Accuracy, completion, latency, tokens, tool calls; 4 failure types; a trace on every request plus an optional LangSmith dashboard | [EVALUATION.md](../docs/EVALUATION.md) · [latest results](../eval/results/latest.md) · [trace.py](../backend/app/trace.py) |
| **VI. Ship** | UI, container, deployed | React app (voice, Hindi) on GitHub Pages; FastAPI in Docker on Render | [README](../README.md#deploy) · [render.yaml](../render.yaml) |
| **VI. Responsible AI** | Privacy, refusals, injection, human in the loop | "May be eligible" only (critic + code fallback); Aadhaar / phone / bank / PAN / e-mail masked before the AI sees them; injection rules in both prompts; critic checks every number against the data; "still being checked" note on unreviewed schemes; scheme data review checklist; refusals; official link and CSC in every answer | [RESPONSIBLE_AI.md](../docs/RESPONSIBLE_AI.md) · [SPEC.md](SPEC.md#what-it-refuses-or-never-does) |

---

## Key numbers

| | |
|---|---|
| End-to-end accuracy (agent system) | **92%** (91/99), up from 82% (65/79) at the first run |
| Best single prompt (no agents) | 76% |
| Safety violations | 0 (15/15 safety and prompt-injection queries pass) |
| Gold schemes found | 100% |
| AI calls per message | 2 (read + write); everything else is code |
| Tokens per query | ~2,000 (one big prompt needs ~5,000) |
| Latency p50 / p95 | 6.3 s / 14.8 s (laptop to the course endpoint) |
| Search: right scheme in the top 4 | 21/21 test questions; recall@4 76% on the evaluation queries |
| Embeddings via the IIT KGP API | 100% (165/165 calls in the latest run) |

---

## Still to do

| Item | Part |
|---|---|
| Held-out test set (~40 new queries, never used for fixing) for an honest score | I / V |
| Rate limiting, answer caching | VI |
| Chunk-size experiment; re-label chunks in PDFs that cover several schemes | III |
| LangSmith dashboard screenshots (trace dashboard deliverable) | V |
| Human review of all 28 schemes with the checklist in [RESPONSIBLE_AI.md §3](../docs/RESPONSIBLE_AI.md#3-human-in-the-loop) (0/28 verified) | VI |
| 12-page report and 10-minute demo | Deliverables |

---

## All project docs

| Doc | For |
|---|---|
| [HOW_IT_WORKS_SIMPLIFIED.md](../docs/HOW_IT_WORKS_SIMPLIFIED.md) | Everyone: the system in diagrams |
| [HOW_IT_WORKS.md](../docs/HOW_IT_WORKS.md) | Full backend details |
| [RAG_AND_EMBEDDINGS.md](../docs/RAG_AND_EMBEDDINGS.md) | How PDFs are searched, how to add one |
| [EVALUATION.md](../docs/EVALUATION.md) | Test set, metrics, tracing, prompting baseline |
| [SPEC.md](SPEC.md) | One-page spec |
| [RESPONSIBLE_AI.md](../docs/RESPONSIBLE_AI.md) | Safeguards, personal data, human review process |
| [MODEL_COMPLIANCE.md](../docs/MODEL_COMPLIANCE.md) | Models used (Qwen3-8B, bge-small, reranker), how only approved services are enforced, evidence |
