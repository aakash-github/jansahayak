# Evaluation results: run with the FULL intake schema (rejected)

n> This run forced every profile field through constrained decoding. The model filled unstated yes/no facts with false and dropped facts it found before, so accuracy fell from 90% to 85%. We switched to a light schema (only `intent` and the object shape) plus pydantic validation. E-16 and M-04 failed because the course AI server was slow (30-55 s) during this run.
79 queries from `eval/eval_set.csv`, real Qwen3-8B model.

## Headline

| Metric | Value |
|---|---|
| **End-to-end accuracy** (all checks pass) | **85%** (67/79) |
| Task completion (got a reply, no crash) | 100% |
| Right behaviour (find/focus/which/ask/refuse) | 100% |
| Gold schemes found on cards | 98% |
| Queries showing a forbidden scheme | 6 |
| Queries missing a key fact | 4 |
| Safety violations | 0 |
| Retrieval recall@4 / @10 (search alone, raw question) | 67% / 70% |

## Cost and speed (per query, all turns)

| Metric | Value |
|---|---|
| Latency p50 / p95 | 6.2 s / 30.6 s |
| AI calls (avg) | 1.89 |
| Tool calls (avg) | 8.4 |
| Tokens (avg, in + out) | 1926 |
| Cost | Rs 0 (course endpoint; tokens count against the team quota) |
| AI retries (busy) / critic rewrites | 10 / 0 |

## Failure taxonomy

| Type | Count | Meaning |
|---|---|---|
| retrieval_miss | 0 | key fact not in the evidence or scheme data given to the AI |
| reasoning_error | 10 | wrong behaviour / schemes, or fact given but left out |
| tool_error | 2 | crash, AI unreachable, unreadable JSON |
| hallucination | 0 | broke a safety rule or invented a scheme / guarantee |

## By query type

| Type | Queries | Pass |
|---|---|---|
| find | 41 | 80% |
| focus | 18 | 83% |
| multi | 6 | 83% |
| ask | 4 | 100% |
| refuse | 5 | 100% |
| safety | 5 | 100% |

## Failed queries

| ID | Failure | Expected → got | Problem |
|---|---|---|---|
| F-04 | reasoning_error | focus → focus | no fact: 72/hours/intimat/inform/report |
| S-03 | reasoning_error | find → find | missing STU-03 |
| S-05 | reasoning_error | find|focus → find | no fact: scholarships.gov.in/National Scholarship Portal/NSP |
| S-07 | reasoning_error | find → find | forbidden STU-05 |
| S-08 | reasoning_error | find → find | forbidden STU-01 |
| S-15 | reasoning_error | find → find | forbidden STU-06 |
| S-20 | reasoning_error | find → find | forbidden STU-03 |
| E-02 | reasoning_error | focus → focus | no fact: 18 |
| E-07 | reasoning_error | find → find | forbidden ENT-05 |
| E-09 | reasoning_error | find → find | missing ENT-03; forbidden ENT-05 |
| E-16 | tool_error | focus → focus | no fact: 35%;10 lakh |
| M-04 | tool_error | find → find | missing FARM-04 |
