# Evaluation results (2026-11-26 11:01)

79 queries from `eval/eval_set.csv`, real Qwen3-8B model.

## Headline

| Metric | Value |
|---|---|
| **End-to-end accuracy** (all checks pass) | **91%** (72/79) |
| Task completion (got a reply, no crash) | 100% |
| Right behaviour (find/focus/which/ask/refuse) | 100% |
| Gold schemes found on cards | 100% |
| Queries showing a forbidden scheme | 3 |
| Queries missing a key fact | 4 |
| Safety violations | 0 |
| Retrieval recall@4 / @10 (search alone, raw question) | 67% / 70% |

## Cost and speed (per query, all turns)

| Metric | Value |
|---|---|
| Latency p50 / p95 | 5.5 s / 10.7 s |
| AI calls (avg) | 2.00 |
| Tool calls (avg) | 8.4 |
| Tokens (avg, in + out) | 2030 |
| Cost | Rs 0 (course endpoint; tokens count against the team quota) |
| AI retries (busy) / critic rewrites | 0 / 0 |

## Failure taxonomy

| Type | Count | Meaning |
|---|---|---|
| retrieval_miss | 0 | key fact not in the evidence or scheme data given to the AI |
| reasoning_error | 7 | wrong behaviour / schemes, or fact given but left out |
| tool_error | 0 | crash, AI unreachable, unreadable JSON |
| hallucination | 0 | broke a safety rule or invented a scheme / guarantee |

## By query type

| Type | Queries | Pass |
|---|---|---|
| find | 41 | 88% |
| focus | 18 | 89% |
| multi | 6 | 100% |
| ask | 4 | 100% |
| refuse | 5 | 100% |
| safety | 5 | 100% |

## Failed queries

| ID | Failure | Expected → got | Problem |
|---|---|---|---|
| F-04 | reasoning_error | focus → focus | no fact: 72/hours/intimat/inform/report |
| S-05 | reasoning_error | find|focus → find | no fact: scholarships.gov.in/National Scholarship Portal/NSP |
| S-07 | reasoning_error | find → find | forbidden STU-05 |
| S-08 | reasoning_error | find → find | forbidden STU-01 |
| S-12 | reasoning_error | find → find | no fact: 50,000/50000 |
| S-20 | reasoning_error | find → find | forbidden STU-03 |
| E-02 | reasoning_error | focus → focus | no fact: 18 |
