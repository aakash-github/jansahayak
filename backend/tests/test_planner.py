"""Planner -> executor checks (no AI calls). Run:  python -m pytest backend/tests -q

  - the planner writes the right plan for find, focus and drill turns (tools, order, inputs, reasons)
  - the executor follows the plan, resolves "$top_5" / "$best" / "$focus", and logs every step
  - a failed optional step is logged and skipped; a failed required step stops the plan
  - plan and step log appear in every trace
"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app import agents, eligibility, retrieval, trace  # noqa: E402
from app.main import app  # noqa: E402

FARMER = {"occupation": "farmer", "state": "Uttar Pradesh", "land_acres": 2, "age": 35}


def tools(plan):
    return [p["tool"] for p in plan]


def run(state):
    """planner + executor, inside a trace (like a real request)."""
    trace.start()
    state = {**state, **agents.planner(state)}
    out = agents.executor(state)
    t = trace.finish()
    return state, out, t


# ---------- planner ----------

def test_find_plan():
    p = agents.planner({"mode": "find", "message": "farmer in UP, any help for irrigation?", "profile": FARMER})["plan"]
    assert tools(p) == ["eligibility", "documents", "links", "search"]
    assert p[1]["args"]["scheme"] == "$top_5" and p[3]["args"]["schemes"] == "$top_5"
    assert "Uttar Pradesh" in p[0]["why"] and "topic" in p[0]["why"]


def test_focus_plan_steers_search_by_question():
    s = {"mode": "focus", "focus": "FARM-01", "message": "What documents do I need for PM-KISAN?", "profile": FARMER}
    out = agents.planner(s)
    assert tools(out["plan"]) == ["eligibility", "documents", "links", "search"]
    assert out["qtype"] == "documents" and "documents required" in out["plan"][3]["args"]["steer"]
    assert out["plan"][0]["args"] == {"scheme": "FARM-01"}


def test_drill_plan_picks_best_then_searches_only_it():
    p = agents.planner({"mode": "find", "drill": True, "message": "find schemes and documents for the best one",
                        "profile": FARMER})["plan"]
    assert tools(p) == ["eligibility", "documents", "links", "pick_best", "search"]
    assert p[4]["args"]["schemes"] == "$best"


def test_plan_is_short_and_uses_known_tools_only():
    for s in [{"mode": "find", "message": "x", "profile": FARMER},
              {"mode": "find", "drill": True, "message": "best one documents", "profile": FARMER},
              {"mode": "focus", "focus": "ENT-01", "message": "how to apply", "profile": {}}]:
        p = agents.planner(s)["plan"]
        assert 0 < len(p) <= agents.MAX_PLAN and set(tools(p)) <= set(agents.TOOLS)


# ---------- intake: when is it a drill? ----------

def intake(message, last_ids=None):
    return asyncio.run(agents.intake({"message": message, "profile": {}, "asked": [], "last_ids": last_ids or []}))


def test_detects_two_step_request():
    out = intake("I am a farmer in Uttar Pradesh with 2 acres. Find my schemes and tell me the documents for the best one.")
    assert out["drill"] and out["mode"] == "find"


def test_drill_also_replaces_which_scheme_question():
    out = intake("How do I apply for the best one?", last_ids=["FARM-01", "FARM-02"])
    assert out["drill"] and out["mode"] == "find"


def test_not_a_drill():
    assert not intake("What are the best schemes for a farmer?")["drill"]           # no apply/documents question
    assert not intake("How do I apply for the best one, PM-KISAN?")["drill"]         # names a scheme: focus
    assert intake("How do I apply?", last_ids=["FARM-01", "FARM-02"])["mode"] == "which"


# ---------- executor ----------

def test_executor_follows_find_plan():
    s, out, t = run({"mode": "find", "message": "farmer in UP", "profile": FARMER})
    shown = [r["scheme_id"] for r in out["results"]]
    assert 0 < len(shown) <= 5 and out["total"] >= len(shown)
    assert all(r["documents"] == eligibility.documents_for(r["scheme_id"]) for r in out["results"])
    assert {c["scheme_id"] for c in out["evidence"]} <= set(shown)
    assert [step["tool"] for step in t["plan_log"]] == tools(s["plan"]) and all(step["ok"] for step in t["plan_log"])
    assert len(t["plan"]) == len(s["plan"]) and t["plan"][0].startswith("eligibility: ")


def test_executor_drill_resolves_best():
    s, out, t = run({"mode": "find", "drill": True, "message": "documents for the best one", "profile": FARMER})
    first_ok = next(r["scheme_id"] for r in out["results"] if r["status"] != "appears_not_eligible")
    assert out["best"] == first_ok
    assert out["evidence"] and {c["scheme_id"] for c in out["evidence"]} == {first_ok}


def test_executor_focus_one_scheme():
    s, out, t = run({"mode": "focus", "focus": "FARM-03", "message": "How do I apply for Kisan Credit Card?",
                     "profile": FARMER})
    assert [r["scheme_id"] for r in out["results"]] == ["FARM-03"] and out["total"] == 1 and out["all_results"] == []
    assert {c["scheme_id"] for c in out["evidence"]} <= {"FARM-03"}


def test_no_match_skips_later_steps():
    s, out, t = run({"mode": "find", "message": "x", "profile": {"occupation": "astronaut"}})
    assert out["results"] == [] and out["evidence"] == []
    assert [step["result"] for step in t["plan_log"][1:]] == ["skipped: no schemes"] * 3


def test_optional_step_failure_is_logged_and_plan_continues(monkeypatch):
    def broken(*a, **k):
        raise ConnectionError("search down")
    monkeypatch.setattr(retrieval, "search", broken)
    s, out, t = run({"mode": "find", "message": "farmer in UP", "profile": FARMER})
    assert out["results"] and out["evidence"] == []
    search = [step for step in t["plan_log"] if step["tool"] == "search"][0]
    assert not search["ok"] and "ConnectionError" in search["result"]
    assert any(e["kind"] == "tool_error" for e in t["errors"])


def test_required_step_failure_stops_the_plan(monkeypatch):
    def broken(*a, **k):
        raise ValueError("rules file broken")
    monkeypatch.setattr(eligibility, "find_schemes", broken)
    trace.start()
    s = {"mode": "find", "message": "farmer", "profile": FARMER}
    s = {**s, **agents.planner(s)}
    with pytest.raises(RuntimeError, match="eligibility"):
        agents.executor(s)
    t = trace.finish()
    assert [step["tool"] for step in t["plan_log"]] == ["eligibility"]


def test_unknown_tool_in_plan_is_rejected_safely():
    trace.start()
    s = {"mode": "find", "message": "farmer", "profile": FARMER,
         "plan": [agents._step("delete_files", "bad"), *agents.planner({"mode": "find", "message": "farmer", "profile": FARMER})["plan"]]}
    out = agents.executor(s)
    t = trace.finish()
    assert not t["plan_log"][0]["ok"] and out["results"]


# ---------- end to end ----------

def test_api_trace_shows_plan_and_log():
    c = TestClient(app)
    r = c.post("/api/chat", json={"message": "Farmer in UP, 2 acres. Find my schemes and the documents for the best one."}).json()
    t = r["trace"]
    assert r["mode"] == "find" and r["schemes"]
    assert [p.split(":")[0] for p in t["plan"]] == ["eligibility", "documents", "links", "pick_best", "search"]
    assert t["path"] == ["intake", "planner", "executor", "answer", "critic", "suggest"]
    c.post("/api/reset", json={"session_id": r["session_id"], "message": ""})
