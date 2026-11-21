# Capstone submission: JanSahayak (Track B)

This folder is the **starting point for reviewers and the team**. It maps each part of the Track B brief to what we built and where to find it. Most files live elsewhere in the repo; the links point to them.

- **Live app:** https://aakash-github.github.io/jansahayak/
- **Start here to understand the system:** [How it works (simplified)](../docs/HOW_IT_WORKS_SIMPLIFIED.md): every piece on one page, with diagrams

---

## Where we stand

```
I   Spec + eval set        █████████░  spec + 79 gold queries
II  Prompting baseline     █████████░  4 strategies vs agent system
III RAG                    ███████░░░  hybrid search + reranker + citations; chunk-size experiment to do
IV  Agentic layer          █████████░  planner → executor → critic, 4 tools, memory
V   Eval + observability   █████████░  90% accuracy, failure types, traces
VI  Ship + responsible AI  ██████░░░░  live, privacy, refusals; rate limiting + caching to do
```

---

## Brief → what we built → where

| Part | The brief asks for | What we have | Where |
|---|---|---|---|
| **I. Spec** | Problem, users, scope, what is correct | One-page spec | [SPEC.md](SPEC.md) |
| **I. Eval set** | 60–100 queries with gold answers | 89 queries: find, focus, multi-turn, ask, refuse, safety (15, incl. 10 prompt-injection / personal-data); 8 in Hindi. Results below are from the 79-query run until the eval is re-run | [eval/eval_set.csv](../eval/eval_set.csv) |
| **II. Prompting baseline** | One prompt, ≥ 3 strategies, how the small model breaks | 4 strategies (zero-shot, few-shot, chain-of-thought, decomposition). Best 76% vs agent system 90% | [EVALUATION.md §7](../docs/EVALUATION.md#7-prompting-baseline-one-prompt-vs-the-agent-system) · [results](../eval/results/prompting.md) |
| **III. RAG** | Index official documents, chunking, hybrid search, reranker, citations, retrieval measured separately | 33 PDFs → 1,884 chunks; BM25 + embeddings + RRF + cross-encoder reranker; [S1] citations; recall@4/@10 | [RAG_AND_EMBEDDINGS.md](../docs/RAG_AND_EMBEDDINGS.md) · [retrieval_eval.py](../eval/retrieval_eval.py) |
| **IV. Agents** | ≥ 3 tools, planner → executor → critic, state, error handling | LangGraph: intake → planner → executor → answer → critic → follow-up. Tools: eligibility, search, documents, links. Session memory, JSON retries, step cap | [HOW_IT_WORKS.md](../docs/HOW_IT_WORKS.md) · [agents.py](../backend/app/agents.py) |
| **V. Evaluation** | Metrics, failure taxonomy, tracing | Accuracy, completion, latency, tokens, tool calls; 4 failure types; a trace on every request plus an optional LangSmith dashboard | [EVALUATION.md](../docs/EVALUATION.md) · [latest results](../eval/results/latest.md) · [trace.py](../backend/app/trace.py) |
| **VI. Ship** | UI, container, deployed | React app (voice, Hindi) on GitHub Pages; FastAPI in Docker on Render | [README](../README.md#deploy) · [render.yaml](../render.yaml) |
| **VI. Responsible AI** | Privacy, refusals, injection, human in the loop | "May be eligible" only (critic + code fallback); Aadhaar / phone / bank / PAN / e-mail masked before the AI sees them; injection rules in both prompts; critic checks every number against the data; "still being checked" note on unreviewed schemes; scheme data review checklist; refusals; official link and CSC in every answer | [RESPONSIBLE_AI.md](../docs/RESPONSIBLE_AI.md) · [SPEC.md](SPEC.md#what-it-refuses-or-never-does) |

---

## Key numbers

| | |
|---|---|
| End-to-end accuracy (agent system) | **90%** (71/79), up from 82% at the first run |
| Best single prompt (no agents) | 76% |
| Safety violations | 0 |
| Gold schemes found | 100% |
| AI calls per message | 2 (read + write); everything else is code |
| Tokens per query | ~1,900 (one big prompt needs ~5,000) |

---

## Still to do

| Item | Part |
|---|---|
| Held-out test set (~40 new queries, never used for fixing) for an honest score | I / V |
| Rate limiting, answer caching | VI |
| Re-run `eval/run_eval.py` on all 89 queries (10 new safety queries) and update the numbers | V / VI |
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
