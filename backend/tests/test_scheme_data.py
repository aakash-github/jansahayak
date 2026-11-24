"""Data checks for data/schemes.json (no AI calls). Run:  python -m pytest backend/tests -q
   or simply:  python backend/tests/test_scheme_data.py

Catches mistakes made when editing the scheme catalogue by hand: missing keys, duplicate IDs or
names, unknown groups/states/fields, wrong value types for an operator, income limits written in
lakh instead of rupees, impossible ages, non-https links, empty benefit/documents, an alias shared
by two schemes, and unknown verification status values.
These checks only read the file; if one fails, fix the data (or the check, if the rule is new).
"""
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from app import eligibility as E  # noqa: E402
from app.agents import FIELDS  # noqa: E402

REQUIRED_KEYS = {"scheme_id", "scheme_name", "short_name", "beneficiary_groups", "states", "benefit", "rules",
                 "required_documents", "official_url", "source_url", "verification_status", "aliases"}
GROUPS = {"farmer", "student", "entrepreneur"}
STATES_AND_UTS = {
    "Andhra Pradesh", "Arunachal Pradesh", "Assam", "Bihar", "Chhattisgarh", "Goa", "Gujarat", "Haryana",
    "Himachal Pradesh", "Jharkhand", "Karnataka", "Kerala", "Madhya Pradesh", "Maharashtra", "Manipur",
    "Meghalaya", "Mizoram", "Nagaland", "Odisha", "Punjab", "Rajasthan", "Sikkim", "Tamil Nadu", "Telangana",
    "Tripura", "Uttar Pradesh", "Uttarakhand", "West Bengal",
    "Andaman and Nicobar Islands", "Chandigarh", "Dadra and Nagar Haveli and Daman and Diu", "Delhi",
    "Jammu and Kashmir", "Ladakh", "Lakshadweep", "Puducherry",
}
NUMBER_OPS = {"<=", ">=", "<", ">"}
LIST_OPS = {"contains_any", "in"}
VERIFICATION_STATUSES = {"needs_review", "verified"}  # README: "draft (needs_review) until someone checks it"


def rules():
    """(scheme, rule) for every rule in the catalogue."""
    return [(s, r) for s in E.SCHEMES for r in s["rules"]]


def is_number(v):
    return isinstance(v, (int, float)) and not isinstance(v, bool)


def test_required_keys_present():
    for s in E.SCHEMES:
        missing = REQUIRED_KEYS - set(s)
        assert not missing, (s.get("scheme_id"), missing)
        for r in s["rules"]:
            assert {"field", "op", "value", "text"} <= set(r), (s["scheme_id"], r)


def test_scheme_ids_unique():
    dup = [k for k, n in Counter(s["scheme_id"] for s in E.SCHEMES).items() if n > 1]
    assert not dup, dup


def test_scheme_names_unique():
    for key in ["scheme_name", "short_name"]:
        dup = [k for k, n in Counter(s[key].lower() for s in E.SCHEMES).items() if n > 1]
        assert not dup, (key, dup)


def test_groups_are_known():
    for s in E.SCHEMES:
        assert s["beneficiary_groups"], s["scheme_id"]
        assert set(s["beneficiary_groups"]) <= GROUPS, (s["scheme_id"], s["beneficiary_groups"])


def test_states_are_real_or_all_india_never_mixed():
    for s in E.SCHEMES:
        st = s["states"]
        assert st, s["scheme_id"]
        if "All India" in st:
            assert st == ["All India"], (s["scheme_id"], "All India mixed with states", st)
        else:
            assert set(st) <= STATES_AND_UTS, (s["scheme_id"], set(st) - STATES_AND_UTS)


def test_rule_fields_are_known():
    for s, r in rules():
        assert r["field"] in FIELDS, (s["scheme_id"], r["field"])


def test_rule_values_fit_operator():
    for s, r in rules():
        op, v = r["op"], r["value"]
        where = (s["scheme_id"], r["field"], op, v)
        if op in NUMBER_OPS:
            assert is_number(v), where
        elif op == "between":
            assert isinstance(v, list) and len(v) == 2 and all(map(is_number, v)), where
            assert v[0] <= v[1], where
        elif op in LIST_OPS:
            assert isinstance(v, list) and v, where
            assert all(isinstance(x, str) and x.strip() for x in v), where
        elif op == "is_true":
            assert v is True, where
        elif op == "==":
            assert isinstance(v, str) and v.strip(), where
        else:
            raise AssertionError(("unknown operator", where))


def test_every_rule_has_readable_text():
    for s, r in rules():
        assert isinstance(r["text"], str) and len(r["text"].strip()) >= 5, (s["scheme_id"], r)


def test_occupation_rule_matches_group():
    for s, r in rules():
        if r["field"] == "occupation":
            assert r["op"] == "==" and r["value"] in s["beneficiary_groups"], (s["scheme_id"], r["value"])


def test_income_limits_look_like_rupees():
    # catches "8" meaning 8 lakh (should be 800000)
    for s, r in rules():
        if r["field"] == "annual_income" and r["op"] in NUMBER_OPS:
            assert 10000 <= r["value"] <= 10000000, (s["scheme_id"], r["value"])


def test_ages_are_plausible():
    for s, r in rules():
        if r["field"] == "age":
            vals = r["value"] if r["op"] == "between" else [r["value"]]
            assert all(0 < x < 100 for x in vals), (s["scheme_id"], r["value"])


def test_links_use_https():
    for s in E.SCHEMES:
        for key in ["official_url", "source_url"]:
            assert s[key].startswith("https://"), (s["scheme_id"], key, s[key])


def test_benefit_and_documents_filled_in():
    for s in E.SCHEMES:
        assert s["benefit"].strip(), s["scheme_id"]
        assert s["required_documents"] and all(d.strip() for d in s["required_documents"]), s["scheme_id"]


def test_no_alias_belongs_to_two_schemes():
    owner = {}
    for s in E.SCHEMES:
        for a in s["aliases"] + [s["scheme_name"]]:
            a = a.lower().strip()
            assert a, s["scheme_id"]
            assert owner.setdefault(a, s["scheme_id"]) == s["scheme_id"], (a, owner[a], s["scheme_id"])


def test_verification_status_known():
    for s in E.SCHEMES:
        assert s["verification_status"] in VERIFICATION_STATUSES, (s["scheme_id"], s["verification_status"])


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
