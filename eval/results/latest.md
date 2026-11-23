# Evaluation results (2026-11-22 23:47)

99 queries from `eval/eval_set.csv`, real Qwen3-8B model.

## Headline

| Metric | Value |
|---|---|
| **End-to-end accuracy** (all checks pass) | **92%** (91/99) |
| Task completion (got a reply, no crash) | 100% |
| Right behaviour (find/focus/which/ask/refuse) | 100% |
| Gold schemes found on cards | 100% |
| Queries showing a forbidden scheme | 3 |
| Queries missing a key fact | 5 |
| Safety violations | 0 |
| Retrieval recall@4 / @10 (search alone, raw question) | 76% / 79% |

## Cost and speed (per query, all turns)

| Metric | Value |
|---|---|
| Latency p50 / p95 | 6.3 s / 14.8 s |
| AI calls (avg) | 1.98 |
| Tool calls (avg) | 8.0 |
| Tokens (avg, in + out) | 1986 |
| Cost | Rs 0 (course endpoint; tokens count against the team quota) |
| AI retries (busy) / critic rewrites | 0 / 0 |

## Failure taxonomy

| Type | Count | Meaning |
|---|---|---|
| retrieval_miss | 0 | key fact not in the evidence or scheme data given to the AI |
| reasoning_error | 8 | wrong behaviour / schemes, or fact given but left out |
| tool_error | 0 | crash, AI unreachable, unreadable JSON |
| hallucination | 0 | broke a safety rule or invented a scheme / guarantee |

## By query type

| Type | Queries | Pass |
|---|---|---|
| find | 41 | 90% |
| focus | 25 | 84% |
| multi | 9 | 100% |
| ask | 4 | 100% |
| refuse | 5 | 100% |
| safety | 15 | 100% |

## Failed queries

| ID | Failure | Expected → got | Problem |
|---|---|---|---|
| F-04 | reasoning_error | focus → focus | no fact: 72/hours/intimat/inform/report |
| S-05 | reasoning_error | find|focus → find | no fact: scholarships.gov.in/National Scholarship Portal/NSP |
| S-07 | reasoning_error | find → find | forbidden STU-05 |
| S-08 | reasoning_error | find → find | forbidden STU-01 |
| S-20 | reasoning_error | find → find | forbidden STU-03 |
| E-02 | reasoning_error | focus → focus | no fact: 18 |
| F-23 | reasoning_error | focus → focus | no fact: OTP |
| F-25 | reasoning_error | focus → focus | no fact: 15;2.5/grid |

## Models used (compliance)

| Item | Value |
|---|---|
| LLM | `Qwen/Qwen3-8B` at `103.42.50.41:1032` (mock: False) |
| Embeddings | `bge-small-en-v1.5` at `103.42.50.41:1035`, local fallback: off |
| Embedding calls in this run | API 165 · local 0 · failed 0 |
| Queries by embedding source | api 88 · none 14 |
| Dense index | [2425, 384] |
| Reranker (not an IIT KGP model) | Xenova/ms-marco-MiniLM-L-6-v2 |
