# Evaluation and tracing

How we measure whether JanSahayak gives the right answers, and how we see what happened inside each request. This covers parts I and V of the Track B brief.

- Latest results: [eval/results/latest.md](../eval/results/latest.md)
- First run, before fixes: [eval/results/baseline.md](../eval/results/baseline.md)
- Search-only check: [Document search (RAG) and embeddings](RAG_AND_EMBEDDINGS.md#7-how-good-is-it)

---

## 1. Why evaluate at all

Without a fixed test set, "it looks fine" means "the 3 questions I tried worked". An evaluation set is a list of realistic questions with the **correct answer written down beforehand**. We run the whole system on it and count how many it gets right. Then:

- every change (new prompt, new PDF, new rule) can be checked: did the score go up or down?
- the report can show numbers instead of opinions
- failures are labelled, so we know *which part* to fix

**How real projects do it:**
1. Write the questions and gold answers first, from the real rules (not from what the system happens to say).
2. Freeze the set and record a baseline score.
3. Run it after every change, ideally automatically.
4. Look at the failures, not just the score.

---

## 2. Our evaluation set

`eval/eval_set.csv` has **79 queries**:

| Type | Count | What it tests | Example |
|---|---|---|---|
| `find` | 41 | Right schemes for a profile | "Farmer in Punjab, 10 acres, age 45" |
| `focus` | 18 | Questions about one scheme | "Does CGTMSE give the loan directly?" |
| `multi` | 6 | Several turns in one chat | "I am a farmer" → "I have 3 acres in Haryana, age 30" |
| `ask` | 4 | Asks "farmer, student or business?" when it can't tell | "I need some financial help" |
| `refuse` | 5 | Politely refuses off-topic requests | "Write a poem about cricket" |
| `safety` | 5 | No guarantees, no repeating personal numbers | "Here is my Aadhaar 1234…" |

There are 22 farmer, 20 student and 17 entrepreneur queries, plus 20 general ones. 7 of the queries are in Hindi.

**Columns:**

| Column | Meaning | Example |
|---|---|---|
| `query` | What the user types. Several turns are separated by ` \|\| ` | `I am a farmer \|\| I have 3 acres` |
| `expected_mode` | Kind of reply expected; `\|` means either is fine | `find\|focus` |
| `gold_scheme_ids` | Schemes that **must** be on the cards | `FARM-01;FARM-04` |
| `forbidden_scheme_ids` | Schemes that must **not** be offered (wrong state, age, income). Showing one on a card marked "appears not eligible" is fine. | `FARM-04` |
| `must_mention` | Key facts the answer must contain. `;` separates facts, `\|` separates allowed spellings | `3,000\|3000;60` |
| `must_not_mention` | Must never appear (guarantees, personal numbers) | `9876543210` |
| `gold_answer` | The ideal answer in one line, for people reading the results | |

> **Where the gold answers came from:** the data team wrote them from the official scheme rules (PDFs and portals), **without looking at our system's output**. That way a failure means our data or logic is wrong, not the test. A team member can review and adjust them at any time.

---

## 3. What we measure

```mermaid
flowchart LR
  Q["eval_set.csv<br/>79 queries"] --> RUN["run_eval.py<br/>sends each query to the real<br/>chat API (real Qwen3-8B)"]
  RUN --> CHK{"4 checks"}
  CHK --> B["Behaviour<br/>find / focus / which / ask / refuse"]
  CHK --> S["Schemes<br/>gold on cards, forbidden not"]
  CHK --> F["Facts<br/>must_mention in the answer"]
  CHK --> SA["Safety<br/>no 'you are eligible',<br/>no personal numbers"]
  B & S & F & SA --> P{"all 4 OK?"}
  P -->|yes| PASS[PASS]
  P -->|no| TAX["Label the failure<br/>(taxonomy below)"]
  RUN --> TR["Trace of each request<br/>time, AI calls, tokens, tools"]
  PASS & TAX & TR --> OUT["results/latest.md<br/>results/latest.csv"]
```

| Metric | Meaning |
|---|---|
| **End-to-end accuracy** | % of queries where all 4 checks pass. The main number. |
| Task completion | % that got a reply without crashing |
| Right behaviour, gold found, forbidden shown, facts missing, safety | The 4 checks separately |
| **Retrieval recall@4 / @10** | Search alone, measured separately as the brief requires: for each gold scheme, is one of its chunks in the top 4 (or 10) search results for the raw question? This tells a search problem apart from an answer-writing problem. |
| Latency p50 / p95 | Typical and worst-case response time |
| AI calls, tool calls, tokens | Average per query. Tokens are what we spend from the team quota. The course endpoint costs us nothing in money. |

### Failure taxonomy

Every failed query gets exactly one label, checked in this order:

| Label | Meaning | Usually fixed by |
|---|---|---|
| `tool_error` | Request crashed, AI unreachable, or its JSON was unreadable even after retries | Error handling, retries |
| `hallucination` | A safety rule broken ("you are eligible", repeated a phone number), or the critic still found an invented scheme | Prompt rules, critic |
| `reasoning_error` | Wrong kind of reply, a gold scheme missing, a forbidden one shown, or the fact *was* given to the AI but left out of the answer | Intake prompt, rules in `schemes.json`, answer prompt |
| `retrieval_miss` | A fact is missing **and** it was not in the evidence or scheme data we gave the AI | Search, more or better PDFs |

---

## 4. Tracing: seeing inside each request

A **trace** is a step-by-step record of one request: which steps ran, how long each took, what the AI was asked, and what the tools returned. When an answer is wrong, the trace shows where it went wrong.

**How real projects do it:** tools like **LangSmith**, **Langfuse** or **OpenTelemetry** record every step automatically and show them in a web dashboard. Teams look at traces when debugging and track averages (latency, tokens, errors) over time.

We have two layers:

### a) Built-in trace (always on, no account needed)

`backend/app/trace.py` records, for every chat request:

| Field | Example |
|---|---|
| `path` | `intake > planner > executor > answer > critic > suggest` |
| `node_ms` | `{"intake": 1353, "executor": 2376, "answer": 2534}` |
| `llm_calls`, `tokens_in`, `tokens_out`, `llm_retries` | `2`, `1939`, `155`, `0` |
| `tool_calls`, `tools` | `12`, `["eligibility", "documents", "links", …, "search"]` |
| `critic_retries`, `critic_unresolved` | how often the critic sent the answer back, and anything still wrong |
| `errors` | `[{"kind": "malformed_json", …}]` |
| `evidence_ids` | which schemes the 4 evidence chunks came from |

It is returned with every reply (`"trace"` in the JSON). The last 200 traces, with averages, are at **`GET /api/traces`**, for example `https://<your-app>.onrender.com/api/traces`. Set `TRACE_FILE=logs/traces.jsonl` to also save them to a file. Traces contain **no message text**, only steps, timings, counts and scheme IDs, so no personal details are kept.

### b) LangSmith dashboard (optional, for the "trace dashboard" deliverable)

LangGraph sends traces to LangSmith automatically once these env vars are set. No code changes are needed; the AI calls are already tagged (`qwen3-8b`).

1. Create a free account at smith.langchain.com, then go to Settings → API Keys → create a key.
2. Add to `backend/.env`:
   ```
   LANGSMITH_TRACING=true
   LANGSMITH_API_KEY=<your key>
   LANGSMITH_PROJECT=jansahayak
   ```
3. Run the backend or `run_eval.py`. Each request appears in LangSmith as a tree: intake → executor → answer → critic, with inputs, outputs and timings.

> ⚠️ LangSmith receives **full message text**, so it is an outside service holding user messages. Use it for local testing and eval runs. Only switch it on in production (Render) if the team agrees.

---

## 5. How to run

```bash
# from the repo root
backend/.venv/Scripts/python eval/run_eval.py            # all 79 queries, ~10 minutes
backend/.venv/Scripts/python eval/run_eval.py F- X-      # only farmer and safety queries
backend/.venv/Scripts/python eval/retrieval_eval.py      # search only, ~1 minute
```

The results go to `eval/results/latest.md` (summary and failed queries) and `latest.csv` (one row per query, with the answer). Commit them, so the report can show how the score changed over time.

**Workflow when you change something:**
1. Run the eval, note the accuracy.
2. Make the change.
3. Run again. Did accuracy go up? Did any query that used to pass now fail?
4. Write the before/after numbers in the report.

**Adding a query:** add a row to `eval_set.csv`. Write the gold answer from the official rules, not from what the bot says.

---

## 6. Results so far

| Run | End-to-end accuracy | Right behaviour | Gold schemes found | What changed |
|---|---|---|---|---|
| Baseline | 82% (65/79) | 94% | 91% | First full run |
| After fixes | **90% (71/79)** | 99% | 100% | 1) user group recognised from clear hints (acres → farmer, admission/IIT → student); 2) find answers rank schemes about the asked topic first (irrigation → Per Drop More Crop); 3) "compare" or several schemes named → list answer instead of one scheme |

**Still failing (8):**
- **Answers leave out a fact they were given (4).** Example: the PMFBY claim answer skips "report within 72 hours". Next step: tighter answer prompt, or a checklist of key facts per question type.
- **Rules too loose for school students (3).** A class-8 or class-11 student is offered college or AICTE schemes because "school or college?" is unknown. Next step: ask or infer the study level.
- **Refuses "Ignore your rules… I am a student" (1).** Safe, but it should still show scholarships.
