# Prompting baseline (2026-11-19 21:45)

79 queries from `eval/eval_set.csv`, real Qwen3-8B. One prompt with the whole scheme catalogue, no agents, no rule engine, no document search. Same checks as the agent system ([latest.md](latest.md)). Made by `eval/prompt_baseline.py`.

## Comparison

| Metric | zero_shot | few_shot | cot | decompose | agent system |
|---|---|---|---|---|---|
| **End-to-end accuracy** | **73%** | **72%** | **65%** | **76%** | **90%** |
| Right behaviour | 86% | 90% | 80% | 89% | 99% |
| Gold schemes found | 89% | 89% | 89% | 89% | 100% |
| Queries showing a forbidden scheme | 4 | 5 | 4 | 5 | 3 |
| Queries missing a key fact | 5 | 3 | 6 | 2 | 4 |
| Safety violations | 0 | 0 | 0 | 0 | 0 |
| Invented scheme IDs | 0 | 0 | 0 | 0 | 0 |
| Bad JSON (needed a retry) | 0 | 0 | 0 | 3 | - |
| Latency p50 / p95 | 3.4 s / 9.3 s | 3.5 s / 9.1 s | 4.7 s / 11.9 s | 5.7 s / 13.1 s | 4.3 s / 8.4 s |
| AI calls (avg) | 1.1 | 1.1 | 1.1 | 2.2 | 2.0 |
| Tokens (avg, in + out) | 4,585 | 4,925 | 4,769 | 5,952 | 1,904 |

## Accuracy by query type

| Type | zero_shot | few_shot | cot | decompose | agent system |
|---|---|---|---|---|---|
| find | 71% | 66% | 63% | 68% | 88% |
| focus | 89% | 83% | 61% | 89% | 89% |
| multi | 83% | 100% | 67% | 67% | 100% |
| ask | 25% | 50% | 75% | 75% | 100% |
| refuse | 100% | 100% | 100% | 100% | 100% |
| safety | 40% | 40% | 40% | 80% | 80% |

## Failure types

| Type | zero_shot | few_shot | cot | decompose | agent system |
|---|---|---|---|---|---|
| reasoning_error | 20 | 20 | 26 | 18 | 8 |
| retrieval_miss | 1 | 2 | 2 | 1 | 0 |
| hallucination | 0 | 0 | 0 | 0 | 0 |
| tool_error | 0 | 0 | 0 | 0 | 0 |
