"""FastAPI backend. Holds the API key + CA cert; the React app only talks to this."""
import os
import re
import uuid

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from . import embed, llm, privacy, trace
from .agents import DATA_AS_OF, GRAPH

app = FastAPI(title="JanSahayak API")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[o for o in os.getenv("FRONTEND_ORIGIN", "http://localhost:5173").split(",") if o],
    allow_methods=["*"],
    allow_headers=["*"],
)

SESSIONS: dict[str, dict] = {}  # in-memory, cleared on reset/restart (no PII stored long-term)


class ChatIn(BaseModel):
    session_id: str | None = None
    message: str
    set: dict | None = None        # values from a tapped answer button, e.g. {"category": "sc"}
    scheme_id: str | None = None   # question about one scheme (card button or "Which scheme?" pick)


def _new_session() -> dict:
    return {"profile": {}, "asked": [], "lang": "en", "labels": {}, "last_ids": [], "pending": None}


def _sources(evidence: list, answer: str) -> list:
    """Only the sources the answer actually cites (same numbers as in the text), duplicates removed.
    If the answer cites nothing, show the top 2 distinct ones so users can still check."""
    cited = {int(n) for n in re.findall(r"\[S(\d+)\]", answer)}
    out, seen = [], set()
    for i, c in enumerate(evidence):
        key = (c["title"], c.get("page"))
        if (cited and i + 1 not in cited) or key in seen:
            continue
        seen.add(key)
        out.append({"id": f"S{i+1}", "scheme_id": c["scheme_id"], "title": c["title"], "section": c["section"],
                    "url": c["source_url"], "page": c.get("page")})
    return out if cited else out[:2]


@app.get("/health")
def health():
    return {"ok": True, "mock_llm": llm.MOCK, "embed_api": bool(embed.BASE_URL and embed.API_KEY),
            "last_embed_source": embed.last_source}


@app.post("/api/chat")
async def chat(body: ChatIn):
    sid = body.session_id or str(uuid.uuid4())
    sess = SESSIONS.setdefault(sid, _new_session())
    # Mask Aadhaar / phone / bank / PAN / e-mail BEFORE anything else sees the message (AI, session, traces).
    message, pii_found = privacy.redact(body.message[:1000])
    if body.scheme_id and sess["pending"]:  # answer to "Which scheme do you mean?": re-ask the original question
        message = f"{sess['pending']} ({message})"
    sess["pending"] = None
    if body.set:  # remember the button text so the details panel shows "Up to ₹2.5 lakh", not "250000"
        for k, v in body.set.items():
            sess["labels"][k] = [v, message[:60]]
    trace.start()
    try:
        out = await GRAPH.ainvoke({"message": message, "profile": sess["profile"], "preset": body.set,
                                   "focus": body.scheme_id, "last_ids": sess["last_ids"],
                                   "asked": sess["asked"], "lang": sess["lang"], "steps": 0})
    except Exception as e:
        trace.error("tool_error", f"graph: {type(e).__name__}: {e}")
        return {"session_id": sid, "message": f"Sorry, the AI service is busy right now ({type(e).__name__}). Please try again.",
                "profile": sess["profile"], "profile_labels": {}, "schemes": [], "sources": [], "followup": None,
                "needs_followup": False, "mode": "error", "data_as_of": DATA_AS_OF,
                "trace": trace.finish(mode="error", schemes=[])}
    sess["profile"], sess["asked"] = out.get("profile", {}), out.get("asked", sess["asked"])
    sess["lang"] = out.get("lang", sess["lang"])
    mode = out.get("mode", "find")
    if mode == "find" and out.get("results"):
        sess["last_ids"] = [r["scheme_id"] for r in out["results"]]  # what "How do I apply?" refers to next
    if mode == "which":
        sess["pending"] = message
    blocking = bool(out.get("blocking"))
    labels = {k: lab for k, (v, lab) in sess["labels"].items() if sess["profile"].get(k) == v}  # drop stale labels
    answer = out.get("answer", "")
    if pii_found:  # tell the user we removed it (and why), in the chat language
        answer = f"{privacy.NOTICE.get(sess['lang'], privacy.NOTICE['en'])}\n\n{answer}"
    schemes = [] if blocking else out.get("results", [])
    summary = trace.finish(mode=mode, schemes=[r["scheme_id"] for r in schemes],
                           followup=(out.get("followup") or {}).get("field"),
                           pii_masked=pii_found)  # kinds only (e.g. ["aadhaar"]), never the numbers
    return {
        "session_id": sid,
        "message": answer,
        "mode": mode,                      # find | focus | which | ask | refuse | error
        "profile": sess["profile"],
        "profile_labels": labels,
        "followup": out.get("followup"),   # {field, question, why, helps_names, input, options:[{label, set, scheme_id?}]}
        "needs_followup": blocking,        # True = no schemes in this reply (a question must be answered first)
        "schemes": schemes,
        "sources": _sources(out.get("evidence", []), answer),
        "data_as_of": DATA_AS_OF,
        "pii_masked": bool(pii_found),     # True = a personal number was removed from the message
        "trace": summary,                 # timings, AI calls, tokens, tools, errors (no message text)
    }


@app.get("/api/traces")
def traces(n: int = 50):
    """Last n request traces plus averages: a simple built-in trace dashboard (JSON)."""
    rows = list(trace.RECENT)[-n:]
    k = max(len(rows), 1)
    return {
        "count": len(rows),
        "avg_ms": round(sum(r["ms"] for r in rows) / k),
        "avg_llm_calls": round(sum(r["llm_calls"] for r in rows) / k, 2),
        "avg_tool_calls": round(sum(r["tool_calls"] for r in rows) / k, 2),
        "avg_tokens": round(sum(r["tokens_in"] + r["tokens_out"] for r in rows) / k),
        "errors": sum(len(r["errors"]) for r in rows),
        "traces": rows[::-1],
    }


@app.post("/api/reset")
def reset(body: ChatIn):
    SESSIONS.pop(body.session_id or "", None)
    return {"ok": True}
