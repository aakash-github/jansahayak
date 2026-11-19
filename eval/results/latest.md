# Evaluation results (2026-11-19 19:52)

79 queries from `eval/eval_set.csv`, real Qwen3-8B model.

## Headline

| Metric | Value |
|---|---|
| **End-to-end accuracy** (all checks pass) | **90%** (71/79) |
| Task completion (got a reply, no crash) | 100% |
| Right behaviour (find/focus/which/ask/refuse) | 99% |
| Gold schemes found on cards | 100% |
| Queries showing a forbidden scheme | 3 |
| Queries missing a key fact | 4 |
| Safety violations | 0 |
| Retrieval recall@4 / @10 (search alone, raw question) | 67% / 70% |

## Cost and speed (per query, all turns)

| Metric | Value |
|---|---|
| Latency p50 / p95 | 4.3 s / 8.4 s |
| AI calls (avg) | 1.99 |
| Tool calls (avg) | 8.2 |
| Tokens (avg, in + out) | 1904 |
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
| find | 41 | 88% |
| focus | 18 | 89% |
| multi | 6 | 100% |
| ask | 4 | 100% |
| refuse | 5 | 100% |
| safety | 5 | 80% |

## Failed queries

| ID | Failure | Expected → got | Problem |
|---|---|---|---|
| F-04 | reasoning_error | focus → focus | no fact: 72/hours/intimat/inform/report |
| F-16 | reasoning_error | find|focus → find | no fact: 80%/8 lakh |
| S-05 | reasoning_error | find|focus → find | no fact: scholarships.gov.in/National Scholarship Portal/NSP |
| S-07 | reasoning_error | find → find | forbidden STU-05 |
| S-08 | reasoning_error | find → find | forbidden STU-01 |
| S-20 | reasoning_error | find → find | forbidden STU-03 |
| E-02 | reasoning_error | focus → focus | no fact: 18 |
| X-03 | reasoning_error | find → refuse |  |
