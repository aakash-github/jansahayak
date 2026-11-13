"""Deterministic eligibility engine. The LLM never decides eligibility; these rules do.

Each scheme in data/schemes.json has a list of atomic rules:
  {"field": "annual_income", "op": "<=", "value": 450000, "text": "Family income up to Rs 4.5 lakh"}
Each rule evaluates to met / not_met / unknown (field missing in profile).
"""
import json
from pathlib import Path

SCHEMES = json.loads((Path(__file__).parent.parent / "data" / "schemes.json").read_text(encoding="utf-8"))
BY_ID = {s["scheme_id"]: s for s in SCHEMES}


def _check(rule: dict, profile: dict) -> str:
    v = profile.get(rule["field"])
    if v is None or v == "":
        return "unknown"
    op, target = rule["op"], rule["value"]
    try:
        if op == "in":
            return "met" if str(v).lower() in [str(t).lower() for t in target] else "not_met"
        if op == "==":
            return "met" if str(v).lower() == str(target).lower() else "not_met"
        if op == "is_true":
            return "met" if v in (True, "yes", "true") else "not_met"
        v, target = float(v), float(target)
        return "met" if {"<=": v <= target, ">=": v >= target, "<": v < target, ">": v > target}[op] else "not_met"
    except (ValueError, KeyError):
        return "unknown"


def evaluate(scheme: dict, profile: dict) -> dict:
    conditions = [{"text": r["text"], "field": r["field"], "result": _check(r, profile)} for r in scheme["rules"]]
    results = {c["result"] for c in conditions}
    status = ("appears_not_eligible" if "not_met" in results
              else "more_info_needed" if "unknown" in results
              else "potentially_eligible")
    return {"scheme_id": scheme["scheme_id"], "status": status, "conditions": conditions}


def find_schemes(profile: dict, limit: int = 5) -> list[dict]:
    """Tool 1: filter catalogue by group/state, then evaluate rules. Best matches first."""
    group = (profile.get("occupation") or "").lower()
    state = (profile.get("state") or "").lower()
    out = []
    for s in SCHEMES:
        if group and group not in [g.lower() for g in s["beneficiary_groups"]]:
            continue
        if state and s["states"] != ["All India"] and state not in [x.lower() for x in s["states"]]:
            continue
        out.append(evaluate(s, profile))
    rank = {"potentially_eligible": 0, "more_info_needed": 1, "appears_not_eligible": 2}
    return sorted(out, key=lambda r: rank[r["status"]])[:limit]


def documents_for(scheme_id: str) -> list[str]:
    """Tool 3: document checklist."""
    return BY_ID[scheme_id].get("required_documents", [])


def apply_link(scheme_id: str) -> str:
    """Tool 4: official apply / info link."""
    return BY_ID[scheme_id].get("official_url", "https://www.myscheme.gov.in/")
