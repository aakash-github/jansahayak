"""End-to-end evaluation on eval/eval_set.csv (Track B part V).

For every query it runs the real chat API (real AI model), then checks:
  behaviour   : right kind of reply? (find / focus / which / ask / refuse)
  schemes     : every gold scheme is on the cards, no forbidden scheme is offered
                (a forbidden scheme on a card marked "appears not eligible" is fine)
  facts       : the answer mentions the key facts (must_mention)
  safety      : never "you are eligible", never repeats personal numbers (must_not_mention)
A query PASSES only if all four are right.

Every failure gets ONE label (failure taxonomy), checked in this order:
  tool_error      the request crashed, the AI was unreachable, or its JSON could not be read
  hallucination   a safety rule was broken, or the critic still found an invented scheme / guarantee
  reasoning_error wrong behaviour, a gold scheme missing, or a forbidden scheme shown
                  (also: the fact WAS in the evidence/scheme data but the answer left it out)
  retrieval_miss  a fact is missing AND it was not in anything we gave the AI (search missed it)

Also measured separately: retrieval recall@4 and @10 (search alone, on the raw question).

Run from the repo root (takes ~10 minutes with the real model):
    backend/.venv/Scripts/python eval/run_eval.py              # all queries
    backend/.venv/Scripts/python eval/run_eval.py F- S-01      # only IDs starting with these
Writes eval/results/latest.csv (one row per query) and eval/results/latest.md (summary).
"""
import csv
import os
import re
import statistics
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT.parent / "backend"))
# measure every query fresh: no rate limit, no reused AI replies
os.environ.setdefault("RATE_LIMIT_PER_MIN", "0")
os.environ.setdefault("RATE_LIMIT_TOTAL_PER_MIN", "0")
os.environ.setdefault("LLM_CACHE_SIZE", "0")
from fastapi.testclient import TestClient  # noqa: E402

from app import eligibility, retrieval  # noqa: E402
from app.main import app  # noqa: E402

GUARANTEE = [re.compile(r"\byou are eligible\b", re.I), re.compile(r"(?<!अ)पात्र\s*(हैं|है)")]


def split(v: str, sep: str) -> list[str]:
    return [x.strip() for x in (v or "").split(sep) if x.strip()]


def run_query(client: TestClient, row: dict) -> dict:
    sid, traces, t0, r = None, [], time.perf_counter(), {}
    for turn in split(row["query"], "||"):
        r = client.post("/api/chat", json={"session_id": sid, "message": turn}).json()
        sid = r["session_id"]
        traces.append(r.get("trace") or {})
    ms = round((time.perf_counter() - t0) * 1000)
    client.post("/api/reset", json={"session_id": sid, "message": ""})
    return {"resp": r, "trace": traces[-1], "traces": traces, "ms": ms}


def check(row: dict, out: dict, recall: bool = True) -> dict:
    r, tr = out["resp"], out["trace"]
    answer = r.get("message", "")
    low = answer.lower()
    cards = [s["scheme_id"] for s in r.get("schemes", [])]
    gold, forbid = split(row["gold_scheme_ids"], ";"), split(row["forbidden_scheme_ids"], ";")
    facts = [split(f, "|") for f in split(row["must_mention"], ";")]

    mode_ok = r.get("mode") in split(row["expected_mode"], "|")
    missing = [g for g in gold if g not in cards]
    # a card labelled "appears not eligible" is not a wrong recommendation, so it doesn't count as forbidden
    offered = [s["scheme_id"] for s in r.get("schemes", []) if s.get("status") != "appears_not_eligible"]
    forbidden = [f for f in forbid if f in offered]
    facts_missing = [f for f in facts if not any(a.lower() in low for a in f)]
    unsafe = [p.pattern for p in GUARANTEE if p.search(answer)]
    unsafe += [m for m in split(row["must_not_mention"], "|") if m.lower() in low]
    passed = mode_ok and not missing and not forbidden and not facts_missing and not unsafe

    # failure taxonomy (one label per failed query)
    failure = ""
    if not passed:
        errs = {e["kind"] for t in out["traces"] for e in t.get("errors", [])}
        if r.get("mode") == "error" or errs & {"tool_error", "llm_error", "json_gave_up"}:
            failure = "tool_error"
        elif unsafe or tr.get("critic_unresolved"):
            failure = "hallucination"
        elif not mode_ok or missing or forbidden:
            failure = "reasoning_error"
        else:  # only facts missing: was the fact in what the AI was given?
            given = " ".join(retrieval.CHUNKS[i]["text"] for i in tr.get("evidence_chunks", [])).lower()
            for sid in (c for c in cards if c in eligibility.BY_ID):
                s = eligibility.BY_ID[sid]
                given += " " + " ".join([s["benefit"], " ".join(s["required_documents"]), s["source_url"]]).lower()
            in_input = all(any(a.lower() in given for a in f) for f in facts_missing)
            failure = "reasoning_error" if in_input else "retrieval_miss"

    # retrieval layer alone: search the raw (last) question over ALL chunks
    rec4 = rec10 = None
    if gold and recall:
        q = split(row["query"], "||")[-1]
        top = [c["scheme_id"] for c in retrieval.search(q, None, k=10)]
        rec4 = sum(g in top[:4] for g in gold) / len(gold)
        rec10 = sum(g in top for g in gold) / len(gold)

    completed = r.get("mode") != "error" and bool(answer.strip())
    return {
        "query_id": row["query_id"], "type": row["type"], "group": row["beneficiary_group"], "lang": row["lang"],
        "pass": passed, "failure": failure, "completed": completed,
        "mode": r.get("mode"), "expected_mode": row["expected_mode"], "mode_ok": mode_ok,
        "cards": ";".join(cards), "gold_missing": ";".join(missing), "forbidden_shown": ";".join(forbidden),
        "facts_missing": ";".join("|".join(f) for f in facts_missing), "unsafe": ";".join(unsafe),
        "gold_found": (len(gold) - len(missing)) / len(gold) if gold else None,
        "recall@4": rec4, "recall@10": rec10,
        "ms": out["ms"], "llm_calls": sum(t.get("llm_calls", 0) for t in out["traces"]),
        "tool_calls": sum(t.get("tool_calls", 0) for t in out["traces"]),
        "tokens": sum(t.get("tokens_in", 0) + t.get("tokens_out", 0) for t in out["traces"]),
        "llm_retries": sum(t.get("llm_retries", 0) for t in out["traces"]),
        "critic_retries": sum(t.get("critic_retries", 0) for t in out["traces"]),
        "path": " > ".join(tr.get("path", [])),
        "answer": answer.replace("\n", " ")[:400],
    }


def pct(xs) -> str:
    xs = [x for x in xs if x is not None]
    return f"{100 * sum(xs) / len(xs):.0f}%" if xs else "-"


def summary(rows: list[dict]) -> str:
    n = len(rows)
    ms = sorted(r["ms"] for r in rows)
    p95 = ms[min(n - 1, int(0.95 * n))]
    fails = Counter(r["failure"] for r in rows if r["failure"])
    L = [f"# Evaluation results ({time.strftime('%Y-%m-%d %H:%M')})", "",
         f"{n} queries from `eval/eval_set.csv`, real Qwen3-8B model.", "",
         "## Headline", "", "| Metric | Value |", "|---|---|",
         f"| **End-to-end accuracy** (all checks pass) | **{pct([r['pass'] for r in rows])}** ({sum(r['pass'] for r in rows)}/{n}) |",
         f"| Task completion (got a reply, no crash) | {pct([r['completed'] for r in rows])} |",
         f"| Right behaviour (find/focus/which/ask/refuse) | {pct([r['mode_ok'] for r in rows])} |",
         f"| Gold schemes found on cards | {pct([r['gold_found'] for r in rows])} |",
         f"| Queries showing a forbidden scheme | {sum(bool(r['forbidden_shown']) for r in rows)} |",
         f"| Queries missing a key fact | {sum(bool(r['facts_missing']) for r in rows)} |",
         f"| Safety violations | {sum(bool(r['unsafe']) for r in rows)} |",
         f"| Retrieval recall@4 / @10 (search alone, raw question) | {pct([r['recall@4'] for r in rows])} / {pct([r['recall@10'] for r in rows])} |",
         "", "## Cost and speed (per query, all turns)", "", "| Metric | Value |", "|---|---|",
         f"| Latency p50 / p95 | {statistics.median(ms) / 1000:.1f} s / {p95 / 1000:.1f} s |",
         f"| AI calls (avg) | {statistics.mean(r['llm_calls'] for r in rows):.2f} |",
         f"| Tool calls (avg) | {statistics.mean(r['tool_calls'] for r in rows):.1f} |",
         f"| Tokens (avg, in + out) | {statistics.mean(r['tokens'] for r in rows):.0f} |",
         f"| Cost | Rs 0 (course endpoint; tokens count against the team quota) |",
         f"| AI retries (busy) / critic rewrites | {sum(r['llm_retries'] for r in rows)} / {sum(r['critic_retries'] for r in rows)} |",
         "", "## Failure taxonomy", "", "| Type | Count | Meaning |", "|---|---|---|",
         f"| retrieval_miss | {fails['retrieval_miss']} | key fact not in the evidence or scheme data given to the AI |",
         f"| reasoning_error | {fails['reasoning_error']} | wrong behaviour / schemes, or fact given but left out |",
         f"| tool_error | {fails['tool_error']} | crash, AI unreachable, unreadable JSON |",
         f"| hallucination | {fails['hallucination']} | broke a safety rule or invented a scheme / guarantee |",
         "", "## By query type", "", "| Type | Queries | Pass |", "|---|---|---|"]
    by = defaultdict(list)
    for r in rows:
        by[r["type"]].append(r["pass"])
    L += [f"| {t} | {len(v)} | {pct(v)} |" for t, v in by.items()]
    L += ["", "## Failed queries", "", "| ID | Failure | Expected → got | Problem |", "|---|---|---|---|"]
    for r in rows:
        if r["pass"]:
            continue
        prob = "; ".join(x for x in [
            f"missing {r['gold_missing']}" if r["gold_missing"] else "",
            f"forbidden {r['forbidden_shown']}" if r["forbidden_shown"] else "",
            f"no fact: {r['facts_missing']}" if r["facts_missing"] else "",
            f"unsafe: {r['unsafe']}" if r["unsafe"] else ""] if x)
        L.append(f"| {r['query_id']} | {r['failure']} | {r['expected_mode']} → {r['mode']} | {prob.replace('|', '/')} |")
    return "\n".join(L) + "\n"


def main():
    only = sys.argv[1:]
    rows = [r for r in csv.DictReader(open(ROOT / "eval_set.csv", encoding="utf-8"))
            if not only or any(r["query_id"].startswith(o) for o in only)]
    client, results = TestClient(app), []
    for i, row in enumerate(rows, 1):
        res = check(row, run_query(client, row))
        results.append(res)
        print(f"[{i}/{len(rows)}] {res['query_id']:5s} {'PASS' if res['pass'] else 'FAIL ' + res['failure']:22s} "
              f"{res['ms'] / 1000:5.1f}s  mode={res['mode']}  cards={res['cards']}", flush=True)
    out = ROOT / "results"
    out.mkdir(exist_ok=True)
    with open(out / "latest.csv", "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(results[0]))
        w.writeheader()
        w.writerows(results)
    md = summary(results)
    (out / "latest.md").write_text(md, encoding="utf-8")
    print("\n" + md)


if __name__ == "__main__":
    main()
