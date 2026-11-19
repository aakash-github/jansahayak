# Evaluation results (2026-11-19 19:29)

79 queries from `eval/eval_set.csv`, real Qwen3-8B model.

## Headline

| Metric | Value |
|---|---|
| **End-to-end accuracy** (all checks pass) | **82%** (65/79) |
| Task completion (got a reply, no crash) | 100% |
| Right behaviour (find/focus/which/ask/refuse) | 94% |
| Gold schemes found on cards | 91% |
| Queries showing a forbidden scheme | 3 |
| Queries missing a key fact | 8 |
| Safety violations | 0 |
| Retrieval recall@4 / @10 (search alone, raw question) | 67% / 70% |

## Cost and speed (per query, all turns)

| Metric | Value |
|---|---|
| Latency p50 / p95 | 5.4 s / 9.9 s |
| AI calls (avg) | 1.95 |
| Tool calls (avg) | 7.5 |
| Tokens (avg, in + out) | 1795 |
| Cost | Rs 0 (course endpoint; tokens count against the team quota) |
| AI retries (busy) / critic rewrites | 0 / 0 |

## Failure taxonomy

| Type | Count | Meaning |
|---|---|---|
| retrieval_miss | 0 | key fact not in the evidence or scheme data given to the AI |
| reasoning_error | 14 | wrong behaviour / schemes, or fact given but left out |
| tool_error | 0 | crash, AI unreachable, unreadable JSON |
| hallucination | 0 | broke a safety rule or invented a scheme / guarantee |

## By query type

| Type | Queries | Pass |
|---|---|---|
| find | 41 | 73% |
| focus | 18 | 89% |
| multi | 6 | 100% |
| ask | 4 | 100% |
| refuse | 5 | 100% |
| safety | 5 | 80% |

## Failed queries

| ID | Failure | Expected → got | Problem |
|---|---|---|---|
| F-01 | reasoning_error | find → ask | missing FARM-01; no fact: official/CSC |
| F-04 | reasoning_error | focus → focus | no fact: 72/hours/intimat/inform/report |
| F-06 | reasoning_error | find|focus → find | missing FARM-05; no fact: drip/sprinkler |
| F-14 | reasoning_error | find|focus → find | missing FARM-10; no fact: polyhouse/horticulture/protected |
| F-16 | reasoning_error | find|focus → ask | missing FARM-07; no fact: 80%/8 lakh |
| F-20 | reasoning_error | find → focus | missing FARM-01;FARM-03 |
| S-04 | reasoning_error | find → ask | missing STU-07 |
| S-05 | reasoning_error | find|focus → find | no fact: scholarships.gov.in/National Scholarship Portal/NSP |
| S-07 | reasoning_error | find → find | forbidden STU-05 |
| S-08 | reasoning_error | find → find | forbidden STU-01 |
| S-12 | reasoning_error | find → find | no fact: 50,000/50000 |
| S-20 | reasoning_error | find → find | forbidden STU-03 |
| E-02 | reasoning_error | focus → focus | no fact: 18 |
| X-03 | reasoning_error | find → refuse |  |
