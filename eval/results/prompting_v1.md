# Prompting baseline, run 1: without a reply-language line (2026-11-19 21:17)

79 queries from `eval/eval_set.csv`, real Qwen3-8B. One prompt with the whole scheme catalogue, no agents, no rule engine, no document search. Same checks as the agent system ([latest.md](latest.md)). Made by `eval/prompt_baseline.py`.

> In this run the prompt did not say which language to reply in. Zero-shot and CoT answered 58 and 64 of the 72 English questions in Hindi (the prompt contains one Hindi example phrase), which caused most of their missing facts. The fair comparison is in [prompting.md](prompting.md).

## Comparison

| Metric | zero_shot | few_shot | cot | decompose | agent system |
|---|---|---|---|---|---|
| **End-to-end accuracy** | **59%** | **73%** | **41%** | **71%** | **90%** |
| Right behaviour | 89% | 94% | 75% | 85% | 99% |
| Gold schemes found | 90% | 89% | 80% | 87% | 100% |
| Queries showing a forbidden scheme | 5 | 6 | 3 | 5 | 3 |
| Queries missing a key fact | 18 | 3 | 24 | 2 | 4 |
| Safety violations | 0 | 0 | 1 | 0 | 0 |
| Invented scheme IDs | 0 | 0 | 0 | 0 | 0 |
| Bad JSON (needed a retry) | 6 | 0 | 6 | 2 | - |
| Latency p50 / p95 | 7.4 s / 20.4 s | 3.4 s / 9.9 s | 8.0 s / 19.6 s | 5.7 s / 14.0 s | 4.3 s / 8.4 s |
| AI calls (avg) | 1.1 | 1.1 | 1.1 | 2.2 | 2.0 |
| Tokens (avg, in + out) | 5,048 | 4,909 | 5,223 | 5,902 | 1,904 |

## Accuracy by query type

| Type | zero_shot | few_shot | cot | decompose | agent system |
|---|---|---|---|---|---|
| find | 63% | 68% | 37% | 66% | 88% |
| focus | 56% | 78% | 28% | 89% | 89% |
| multi | 67% | 100% | 50% | 50% | 100% |
| ask | 25% | 75% | 75% | 50% | 100% |
| refuse | 100% | 100% | 100% | 100% | 100% |
| safety | 20% | 40% | 20% | 60% | 80% |

## Failure types

| Type | zero_shot | few_shot | cot | decompose | agent system |
|---|---|---|---|---|---|
| reasoning_error | 27 | 19 | 39 | 22 | 8 |
| retrieval_miss | 4 | 2 | 5 | 1 | 0 |
| hallucination | 0 | 0 | 1 | 0 | 0 |
| tool_error | 1 | 0 | 2 | 0 | 0 |
