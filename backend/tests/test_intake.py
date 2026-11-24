"""Intake routing checks with a fake AI reply (no real AI calls). Run:  python -m pytest backend/tests -q
   or simply:  python backend/tests/test_intake.py

The small model sometimes labels a typed follow-up answer ("less than 1 lakh") as a scheme question,
which used to show "Which scheme do you mean?". A typed detail must update the schemes instead,
while real questions ("What documents do I need?") still go to which / focus.
"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from app import agents, llm  # noqa: E402

SHOWN = ["STU-01", "STU-05", "STU-06"]  # several scheme cards already on screen


def run(message, ai_reply, last_ids=SHOWN):
    """Run intake with the AI replaced by a fixed reply."""
    async def fake_chat_json(*_a, **_k):
        return ai_reply
    saved = llm.MOCK, llm.chat_json
    llm.MOCK, llm.chat_json = False, fake_chat_json
    try:
        return asyncio.run(agents.intake({"message": message, "profile": {"occupation": "student"},
                                          "asked": ["occupation", "annual_income"], "last_ids": last_ids}))
    finally:
        llm.MOCK, llm.chat_json = saved


def test_typed_income_answer_updates_schemes():
    for msg, income in [("less than 1 lakh", 100000), ("80000", 80000), ("मेरी आय 1 लाख से कम है", 100000)]:
        out = run(msg, {"intent": "scheme_question", "profile": {"annual_income": income}})
        assert out["mode"] == "find" and out["intent"] == "find_schemes", (msg, out["mode"])
        assert out["profile"]["annual_income"] == income


def test_real_question_still_asks_which_scheme():
    out = run("What documents do I need?", {"intent": "scheme_question", "profile": {}})
    assert out["mode"] == "which"


def test_question_with_a_detail_is_still_a_question():
    out = run("My income is 1 lakh, how do I apply?", {"intent": "scheme_question", "profile": {"annual_income": 100000}})
    assert out["mode"] == "which"


def test_named_scheme_still_goes_to_focus():
    out = run("income 1 lakh, tell me about PM-YASASVI", {"intent": "scheme_question", "profile": {"annual_income": 100000}})
    assert out["mode"] == "focus" and out["focus"] == "STU-05"


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
