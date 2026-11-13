"""Scheme precision/recall vs gold. Fill gold_scheme_ids (e.g. "FARM-01;FARM-02") in eval_set.csv first.
Run from backend/:  .venv/Scripts/python ../eval/run_eval.py
"""
import csv, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))
from fastapi.testclient import TestClient
from app.main import app

c, P, R, n = TestClient(app), 0.0, 0.0, 0
for row in csv.DictReader(open(Path(__file__).parent / "eval_set.csv", encoding="utf-8")):
    gold = {g for g in row["gold_scheme_ids"].split(";") if g}
    if not gold:
        continue
    out = c.post("/api/chat", json={"message": row["query"]}).json()
    got = {s["scheme_id"] for s in out["schemes"]}
    p = len(got & gold) / len(got) if got else 0
    r = len(got & gold) / len(gold)
    P, R, n = P + p, R + r, n + 1
    print(f"{row['query_id']}: P={p:.2f} R={r:.2f} got={sorted(got)} followup={out['needs_followup']}")
print(f"\n{n} queries | precision={P/max(n,1):.2f} recall={R/max(n,1):.2f}")
