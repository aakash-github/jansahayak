"""FastAPI backend. Holds the API key + CA cert; the React app only talks to this."""
import os
import uuid

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from . import llm
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


@app.get("/health")
def health():
    return {"ok": True, "mock_llm": llm.MOCK}


@app.post("/api/chat")
async def chat(body: ChatIn):
    sid = body.session_id or str(uuid.uuid4())
    sess = SESSIONS.setdefault(sid, {"profile": {}, "asked": [], "lang": "en"})
    try:
        out = await GRAPH.ainvoke({"message": body.message[:1000], "profile": sess["profile"],
                                   "asked": sess["asked"], "lang": sess["lang"], "steps": 0})
    except Exception as e:
        return {"session_id": sid, "message": f"Sorry, the AI service is busy right now ({type(e).__name__}). Please try again.",
                "profile": sess["profile"], "schemes": [], "sources": [], "needs_followup": False, "data_as_of": DATA_AS_OF}
    sess["profile"], sess["asked"] = out.get("profile", {}), out.get("asked", sess["asked"])
    sess["lang"] = out.get("lang", sess["lang"])
    return {
        "session_id": sid,
        "message": out.get("answer", ""),
        "profile": sess["profile"],
        "needs_followup": bool(out.get("followup")),
        "schemes": out.get("results", []) if not out.get("followup") else [],
        "sources": [{"id": f"S{i+1}", "scheme_id": c["scheme_id"], "title": c["title"], "section": c["section"],
                     "url": c["source_url"], "page": c.get("page")} for i, c in enumerate(out.get("evidence", []))],
        "data_as_of": DATA_AS_OF,
    }


@app.post("/api/reset")
def reset(body: ChatIn):
    SESSIONS.pop(body.session_id or "", None)
    return {"ok": True}
