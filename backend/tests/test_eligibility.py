"""Rule-engine checks for eligibility.py (no AI calls). Run:  python -m pytest backend/tests -q
   or simply:  python backend/tests/test_eligibility.py

Each test takes one real scheme from data/schemes.json and a tiny profile, then checks the status
(potentially_eligible / more_info_needed / appears_not_eligible) or the result of one rule.
Covers limits at the edge (inclusive), every operator, bad values, state-only schemes,
the find_schemes ranking, and scheme-name matching.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from app import eligibility as E  # noqa: E402

KNOWN_OPS = {"==", "<=", ">=", "<", ">", "between", "contains_any", "in", "is_true"}


def status(sid, profile):
    return E.evaluate(E.BY_ID[sid], profile)["status"]


def result(sid, profile, field):
    """Result (met / not_met / unknown) of the rule on `field` for scheme `sid`."""
    return next(c["result"] for c in E.evaluate(E.BY_ID[sid], profile)["conditions"] if c["field"] == field)


# AICTE Pragati (STU-02): student, female, income <= 8 lakh, technical course
PRAGATI_OK = {"occupation": "student", "gender": "female", "annual_income": 300000, "course": "B.Tech"}


# --- the 3 statuses -------------------------------------------------------------------------

def test_all_rules_met_is_potentially_eligible():
    assert status("STU-02", PRAGATI_OK) == "potentially_eligible"


def test_missing_detail_is_more_info_needed():
    p = {k: v for k, v in PRAGATI_OK.items() if k != "annual_income"}
    assert status("STU-02", p) == "more_info_needed"


def test_failed_rule_is_appears_not_eligible():
    assert status("STU-02", {**PRAGATI_OK, "gender": "male"}) == "appears_not_eligible"


def test_one_failed_rule_beats_unknown_ones():
    # gender fails; income and course are unknown -> still "appears not eligible"
    assert status("STU-02", {"occupation": "student", "gender": "male"}) == "appears_not_eligible"


# --- limits at the edge ---------------------------------------------------------------------

def test_income_limit_is_inclusive():
    assert result("STU-02", {**PRAGATI_OK, "annual_income": 800000}, "annual_income") == "met"
    assert result("STU-02", {**PRAGATI_OK, "annual_income": 800001}, "annual_income") == "not_met"


def test_between_age_range_is_inclusive():
    # PM-KMY (FARM-04): entry age 18 to 40
    base = {"occupation": "farmer", "land_acres": 2}
    assert result("FARM-04", {**base, "age": 18}, "age") == "met"
    assert result("FARM-04", {**base, "age": 40}, "age") == "met"
    assert result("FARM-04", {**base, "age": 41}, "age") == "not_met"
    assert result("FARM-04", {**base, "age": 17}, "age") == "not_met"


# --- operators ------------------------------------------------------------------------------

def test_contains_any_matches_course_text():
    assert result("STU-02", {**PRAGATI_OK, "course": "B.Tech CSE"}, "course") == "met"
    assert result("STU-02", {**PRAGATI_OK, "course": "Diploma in Civil"}, "course") == "met"
    assert result("STU-02", {**PRAGATI_OK, "course": "BA History"}, "course") == "not_met"


def test_in_category_list_is_case_insensitive():
    # PM-YASASVI (STU-05): OBC / EBC / DNT
    assert result("STU-05", {"category": "OBC"}, "category") == "met"
    assert result("STU-05", {"category": "dnt"}, "category") == "met"
    assert result("STU-05", {"category": "sc"}, "category") == "not_met"


def test_equals_is_case_insensitive():
    assert result("STU-02", {**PRAGATI_OK, "gender": "Female"}, "gender") == "met"


def test_is_true_yes_no_and_missing():
    # Top Class SC (STU-07): admitted to a notified top institution
    assert result("STU-07", {"top_institution": True}, "top_institution") == "met"
    assert result("STU-07", {"top_institution": "yes"}, "top_institution") == "met"
    assert result("STU-07", {"top_institution": False}, "top_institution") == "not_met"
    assert result("STU-07", {}, "top_institution") == "unknown"


def test_bad_value_is_more_info_needed_not_a_crash():
    p = {"occupation": "farmer", "land_acres": 2, "age": "forty"}
    assert result("FARM-04", p, "age") == "unknown"
    assert status("FARM-04", p) == "more_info_needed"


# --- state-only schemes ---------------------------------------------------------------------

def test_state_only_scheme_hidden_for_other_state():
    ids = [r["scheme_id"] for r in E.find_schemes({"occupation": "entrepreneur", "state": "Bihar"}, limit=100)]
    assert "ENT-06" not in ids and "ENT-05" not in ids  # CMEGP (Maharashtra), UP Vishwakarma (UP)


def test_state_only_scheme_shown_for_right_state():
    ids = [r["scheme_id"] for r in E.find_schemes({"occupation": "entrepreneur", "state": "Maharashtra"}, limit=100)]
    assert "ENT-06" in ids and "ENT-05" not in ids


def test_state_only_scheme_needs_state_when_unknown():
    assert result("ENT-06", {"occupation": "entrepreneur", "age": 30}, "state") == "unknown"
    assert status("ENT-06", {"occupation": "entrepreneur", "age": 30, "state": "Maharashtra"}) == "potentially_eligible"


# --- find_schemes ---------------------------------------------------------------------------

def test_find_shows_only_the_users_group():
    for group in ["farmer", "student", "entrepreneur"]:
        res = E.find_schemes({"occupation": group}, limit=100)
        assert res, group
        for r in res:
            assert group in E.BY_ID[r["scheme_id"]]["beneficiary_groups"], (group, r["scheme_id"])


def test_find_puts_ruled_out_schemes_last():
    res = E.find_schemes({"occupation": "farmer", "age": 45, "land_acres": 2}, limit=100)
    out = [r["status"] == "appears_not_eligible" for r in res]
    assert any(out), "expected PM-KMY to be ruled out at age 45"
    assert out == sorted(out), [(r["scheme_id"], r["status"]) for r in res]


def test_find_ranks_topic_in_text_first():
    res = E.find_schemes({"occupation": "farmer", "land_acres": 2}, limit=5, text="I need help with irrigation")
    assert res[0]["scheme_id"] == "FARM-05"  # Per Drop More Crop


def test_find_respects_limit():
    assert len(E.find_schemes({"occupation": "farmer"}, limit=3)) == 3
    assert len(E.find_schemes({"occupation": "farmer"}, limit=1)) == 1


# --- name matching --------------------------------------------------------------------------

def test_match_scheme_by_alias():
    assert E.match_scheme("how do I join maan dhan?") == "FARM-04"
    assert E.match_scheme("documents for kisan credit card") == "FARM-03"


def test_match_all_finds_two_schemes():
    assert set(E.match_all("compare PMEGP and CGTMSE")) == {"ENT-01", "ENT-02"}


def test_unknown_name_gives_none():
    assert E.match_scheme("tell me about the moon landing scheme") is None
    assert E.match_all("hello there") == []


# --- data sanity ----------------------------------------------------------------------------

def test_every_scheme_has_apply_link_and_documents():
    for s in E.SCHEMES:
        assert E.apply_link(s["scheme_id"]).startswith("https://"), s["scheme_id"]
        docs = E.documents_for(s["scheme_id"])
        assert isinstance(docs, list) and docs, s["scheme_id"]


def test_every_rule_uses_a_known_operator():
    for s in E.SCHEMES:
        for r in s["rules"]:
            assert r["op"] in KNOWN_OPS, (s["scheme_id"], r)


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
