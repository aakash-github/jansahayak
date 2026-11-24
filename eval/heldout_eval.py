"""Held-out evaluation on eval/heldout_set.csv (40 queries never used while building the app).

Same checks, failure labels and summary as run_eval.py (imported from there, not copied):
behaviour, schemes, facts and safety must all be right for a query to PASS.

RULE: this set is for an honest score. NEVER fix code or prompts because of a held-out failure
and then re-score it: that turns it into a second dev set and the score stops meaning anything.
Fix problems you find with eval_set.csv queries instead, and report the held-out score as it was.

Run from the repo root (real model; mock mode gives meaningless scores, don't commit those):
    backend/.venv/bin/python eval/heldout_eval.py              # all 40 queries
    backend/.venv/bin/python eval/heldout_eval.py H-0 H-12     # only IDs starting with these
Writes eval/results/heldout.csv (one row per query) and eval/results/heldout.md (summary).
"""
import csv
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
from run_eval import TestClient, app, check, run_query, summary  # noqa: E402

from app import llm  # noqa: E402  (same backend package run_eval put on sys.path)


def main():
    only = sys.argv[1:]
    rows = [r for r in csv.DictReader(open(ROOT / "heldout_set.csv", encoding="utf-8"))
            if not only or any(r["query_id"].startswith(o) for o in only)]
    if llm.MOCK:
        print("WARNING: no model configured (MOCK mode). Scores are meaningless; do not commit the results.\n")
    client, results = TestClient(app), []
    for i, row in enumerate(rows, 1):
        res = check(row, run_query(client, row))
        results.append(res)
        print(f"[{i}/{len(rows)}] {res['query_id']:5s} {'PASS' if res['pass'] else 'FAIL ' + res['failure']:22s} "
              f"{res['ms'] / 1000:5.1f}s  mode={res['mode']}  cards={res['cards']}", flush=True)
    out = ROOT / "results"
    out.mkdir(exist_ok=True)
    with open(out / "heldout.csv", "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(results[0]))
        w.writeheader()
        w.writerows(results)
    md = summary(results).replace("# Evaluation results", "# Held-out evaluation results", 1)
    md = md.replace("`eval/eval_set.csv`", "`eval/heldout_set.csv` (held-out: never tuned on)", 1)
    if llm.MOCK:
        md = md.replace("real Qwen3-8B model", "MOCK mode (no model): scores are meaningless", 1)
    (out / "heldout.md").write_text(md, encoding="utf-8")
    print("\n" + md)


if __name__ == "__main__":
    main()
