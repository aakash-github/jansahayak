"""Corner-case checks for the follow-up logic (no AI calls). Run:  python -m pytest backend/tests -q
   or simply:  python backend/tests/test_followups.py

Simulates thousands of conversations: start with a user group, then keep answering the suggested
question with every possible button, and check that we never get stuck or miss a question.
"""
import itertools
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from app import eligibility as E  # noqa: E402
from app import followups as F  # noqa: E402

GROUPS = ["farmer", "student", "entrepreneur"]
ASK_LIMIT = 12  # a conversation should never need more follow-ups than this


def rule_fields():
    return {r["field"] for s in E.SCHEMES for r in s["rules"]} | {"state"}


def test_every_rule_field_can_be_asked():
    """Each detail used by a rule must have a question + buttons (or be the user group)."""
    missing = rule_fields() - set(F.Q) - {"occupation"}
    assert not missing, f"rule fields with no follow-up question: {missing}"


def test_buttons_only_set_known_fields():
    from app.agents import FIELDS
    for field, q in F.Q.items():
        for o in q["options"]:
            assert set(o["set"]) <= set(FIELDS), (field, o)


def _walk(group, choose, extra=None):
    """Simulate one conversation; returns (profile, asked, final results)."""
    profile, asked = {"occupation": group, **(extra or {})}, ["occupation"]
    for _ in range(ASK_LIMIT + 1):
        results = E.find_schemes(profile, limit=100)
        field, _helps = F.pick(results, asked, group)
        if not field:
            return profile, asked, results
        asked.append(field)
        opts = F.build(field, "en", 0, group)["options"]
        if opts and choose != "skip":
            profile.update(choose(opts)["set"])
        elif F.Q[field].get("input") == "number" and choose != "skip":
            profile[field] = 30  # typed number
    raise AssertionError(f"{group}: more than {ASK_LIMIT} follow-ups: {asked}")


def _stuck(results, asked, group):
    """'Need more info' schemes whose unknown details we are still allowed to ask but never did."""
    out = []
    for r in results:
        if r["status"] != "more_info_needed":  # already ruled out: asking more would not help
            continue
        for c in r["conditions"]:
            if c["result"] == "unknown" and c["field"] in F.Q and c["field"] not in asked:
                if group == "student" or c["field"] not in F.STUDENT_ONLY:
                    out.append((r["scheme_id"], c["field"]))
    return out


def test_conversations_end_and_nothing_left_unasked():
    random.seed(1)
    for group in GROUPS:
        for strategy in ["skip", lambda o: o[0], lambda o: o[-1]] + [lambda o: random.choice(o)] * 300:
            profile, asked, results = _walk(group, strategy)
            stuck = _stuck(results, asked, group)
            if len(asked) - 1 >= F.SOFT_LIMIT:  # past the soft limit we only ask details that settle 2+ schemes
                per_field = {}
                for sid, f in set(stuck):
                    per_field.setdefault(f, set()).add(sid)
                stuck = [x for x in stuck if len(per_field[x[1]]) >= 2]
            assert not stuck, (group, profile, stuck)
            assert len(asked) == len(set(asked)), f"asked twice: {asked}"


def test_every_scheme_reachable():
    """Every scheme should be able to reach 'May be eligible' for some combination of answers.
    (Run without the soft limit: past it, users can still type details like "I'm in a women SHG".)"""
    random.seed(2)
    saved, F.SOFT_LIMIT = F.SOFT_LIMIT, 99
    reached = set()
    for group in GROUPS:
        for _ in range(3000):
            profile, _, results = _walk(group, lambda o: random.choice(o))
            reached |= {r["scheme_id"] for r in results if r["status"] == "potentially_eligible"}
    F.SOFT_LIMIT = saved
    never = {s["scheme_id"] for s in E.SCHEMES} - reached
    assert not never, f"schemes that can never show 'May be eligible': {sorted(never)}"


def test_state_only_schemes_hidden_for_other_states():
    for group, state in itertools.product(GROUPS, ["Bihar", "Kerala"]):
        res = E.find_schemes({"occupation": group, "state": state}, limit=100)
        for r in res:
            assert E.BY_ID[r["scheme_id"]]["states"] == ["All India"], (state, r["scheme_id"])


if __name__ == "__main__":
    fails = 0
    for name, fn in list(globals().items()):
        if name.startswith("test_"):
            try:
                fn()
                print("PASS", name)
            except AssertionError as e:
                fails += 1
                print("FAIL", name, "->", str(e)[:400])
    sys.exit(1 if fails else 0)
