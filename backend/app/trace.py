"""Tracing: what happened inside one chat request, step by step.

For every request we record:
  - each graph step (node) and how long it took
  - each AI call: time, tokens in/out, retries, bad-JSON replies
  - each tool call: eligibility, search, documents, links
  - errors, critic problems, and which schemes the evidence came from

The summary is returned with every chat reply ("trace"), kept in memory for GET /api/traces,
and (if TRACE_FILE is set) appended to a JSON-lines file. No message text is stored, only counts,
timings, step names and scheme IDs, so traces hold no personal details.

Optional: set LANGSMITH_TRACING=true and LANGSMITH_API_KEY to also send full traces (including
message text) to LangSmith's dashboard. See docs/EVALUATION.md.
"""
import functools
import inspect
import json
import os
import time
import uuid
from collections import deque
from contextvars import ContextVar

RECENT: deque = deque(maxlen=200)          # last 200 request summaries, for GET /api/traces
TRACE_FILE = os.getenv("TRACE_FILE", "")   # e.g. logs/traces.jsonl (local runs)
_current: ContextVar[dict | None] = ContextVar("trace", default=None)


def start() -> dict:
    t = {"id": uuid.uuid4().hex[:12], "t0": time.perf_counter(), "nodes": [], "llm": [], "tools": [],
         "errors": [], "critic_retries": 0, "evidence_ids": []}
    _current.set(t)
    return t


def _t() -> dict | None:
    return _current.get()


def node(name: str, fn):
    """Wrap a graph step so its run time is recorded (works for normal and async functions)."""
    if inspect.iscoroutinefunction(fn):
        @functools.wraps(fn)
        async def run_async(state):
            t0 = time.perf_counter()
            try:
                return await fn(state)
            finally:
                _add("nodes", {"name": name, "ms": _ms(t0)})
        return run_async

    @functools.wraps(fn)
    def run(state):
        t0 = time.perf_counter()
        try:
            return fn(state)
        finally:
            _add("nodes", {"name": name, "ms": _ms(t0)})
    return run


class tool:
    """with trace.tool("search"): ...   records one tool call and its run time."""
    def __init__(self, name: str):
        self.name = name

    def __enter__(self):
        self.t0 = time.perf_counter()

    def __exit__(self, exc_type, exc, tb):
        _add("tools", {"name": self.name, "ms": _ms(self.t0), "ok": exc_type is None})
        if exc_type:
            error("tool_error", f"{self.name}: {exc_type.__name__}")
        return False


def llm_call(ms: float, tokens_in: int, tokens_out: int, retries: int):
    _add("llm", {"ms": round(ms), "in": tokens_in, "out": tokens_out, "retries": retries})


def error(kind: str, detail: str = ""):
    """kind: tool_error | malformed_json | json_gave_up | llm_error"""
    _add("errors", {"kind": kind, "detail": detail[:200]})


def put(key: str, value):
    t = _t()
    if t is not None:
        t[key] = value


def finish(**extra) -> dict:
    """Close the trace and return its summary."""
    t = _t()
    if t is None:
        return {}
    s = {
        "id": t["id"],
        "time": time.strftime("%Y-%m-%d %H:%M:%S"),
        "ms": _ms(t["t0"]),
        "path": [n["name"] for n in t["nodes"]],
        "node_ms": {n["name"]: n["ms"] for n in t["nodes"]},
        "llm_calls": len(t["llm"]),
        "llm_ms": sum(c["ms"] for c in t["llm"]),
        "tokens_in": sum(c["in"] for c in t["llm"]),
        "tokens_out": sum(c["out"] for c in t["llm"]),
        "llm_retries": sum(c["retries"] for c in t["llm"]),
        "tool_calls": len(t["tools"]),
        "tools": [x["name"] for x in t["tools"]],
        "critic_retries": t["critic_retries"],
        "critic_unresolved": t.get("critic_unresolved", ""),
        "errors": t["errors"],
        "evidence_ids": t["evidence_ids"],
        "evidence_chunks": t.get("evidence_chunks", []),
        **extra,
    }
    RECENT.append(s)
    if TRACE_FILE:
        try:
            os.makedirs(os.path.dirname(TRACE_FILE) or ".", exist_ok=True)
            with open(TRACE_FILE, "a", encoding="utf-8") as f:
                f.write(json.dumps(s, ensure_ascii=False) + "\n")
        except OSError:
            pass
    _current.set(None)
    return s


def _add(key: str, item: dict):
    t = _t()
    if t is not None:
        t[key].append(item)


def _ms(t0: float) -> int:
    return round((time.perf_counter() - t0) * 1000)
