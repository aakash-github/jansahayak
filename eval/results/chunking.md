# Chunking experiment (2026-11-26 10:37)

Same 33 PDFs, same search (BM25 + embeddings + RRF + reranker), only the chunk size changes. Search runs over all chunks with no scheme filter. Made by `eval/chunk_experiment.py`.

- **Search set:** 15 questions written without scheme names (`eval/retrieval_eval.py`)
- **Eval set:** 60 queries from `eval/eval_set.csv` that have gold schemes (last turn)

| Chunk size (words / overlap) | Chunks | Avg words | Search set recall@1 / @4 / @10 | Eval set recall@1 / @4 / @10 | Search time p50 | Index size |
|---|---|---|---|---|---|---|
| 150 / 25 | 3,112 | 121 | 80% / 93% / 93% | 40% / 63% / 71% | 1.2 s | 4.8 MB |
| 300 / 50 **(shipped)** | 1,884 | 192 | 87% / 100% / 100% | 49% / 67% / 70% | 2.8 s | 2.9 MB |
| 500 / 80 | 1,728 | 198 | 93% / 93% / 93% | 53% / 68% / 72% | 1.7 s | 2.7 MB |

Best recall@4 overall: **300 / 50 words**.

Notes: chunks are also capped at 500 tokens (the embedding model's limit), so some long chunks are split further. The reranker reads the first 1,500 characters of each chunk to fit in Render's 512 MB memory, so it sees only part of a 500-word chunk.
