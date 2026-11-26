"""Client for the IIT KGP hosted Qwen3-8B (OpenAI-compatible chat API).

Rules from the Track B guide:
- 1 active request per group key  -> we serialise calls with a lock
- 60 req/min, 8192 tokens in+out, max_tokens <= 1024
- retry 429/503 with 2, 4, 8 s backoff, then give up
- constrained decoding: chat_json(schema=...) makes the server return JSON of that shape
- identical prompts are answered from a small in-memory cache (LLM_CACHE_SIZE, LLM_CACHE_TTL)
- no embeddings on this endpoint (they come from the separate course embedding API, see embed.py)

Every call is recorded in the request trace (time, tokens, retries, bad JSON), see trace.py.
"""
import asyncio
import hashlib
import json
import os
import re
import time
from collections import OrderedDict

import httpx
from dotenv import load_dotenv

from . import trace

try:  # optional LangSmith dashboard: only active when LANGSMITH_TRACING=true
    from langsmith import traceable
    from langsmith.run_helpers import get_current_run_tree
except ImportError:  # pragma: no cover
    def traceable(**_):
        return lambda f: f

    def get_current_run_tree():
        return None


def _report_usage(tokens_in: int, tokens_out: int, model: str):
    """Show token counts on the LangSmith run (no-op when tracing is off)."""
    try:
        rt = get_current_run_tree()
        if rt is not None:
            rt.set(usage_metadata={"input_tokens": tokens_in, "output_tokens": tokens_out,
                                   "total_tokens": tokens_in + tokens_out},
                   metadata={"ls_provider": "iitkgp-course", "ls_model_name": model})
    except Exception:  # noqa: BLE001  (tracing must never break a reply)
        pass

load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

BASE_URL = os.getenv("MODEL_BASE_URL", "")          # e.g. https://103.42.50.41:1034/v1
API_KEY = os.getenv("MODEL_API_KEY", "")
CA_CERT = os.getenv("MODEL_CA_CERT_PATH", "")       # path to vm0X-ca.crt
MODEL = os.getenv("MODEL_NAME", "Qwen/Qwen3-8B")

MOCK = not (BASE_URL and API_KEY)                   # lets the team run without a key
_lock = asyncio.Lock()

# Cache: the same prompt (same message, same profile, same evidence) gets the saved reply instead of a new
# AI call. Saves quota and time when many people ask the same common question ("PM-KISAN documents?").
CACHE_SIZE = int(os.getenv("LLM_CACHE_SIZE", "300"))
CACHE_TTL = int(os.getenv("LLM_CACHE_TTL", "3600"))   # seconds
_cache: "OrderedDict[str, tuple[float, str]]" = OrderedDict()
_schema_ok = True  # set to False if the server ever rejects constrained decoding


def _client() -> httpx.AsyncClient:
    return httpx.AsyncClient(verify=CA_CERT or True, timeout=90)


def _cache_get(key: str) -> str | None:
    hit = _cache.get(key)
    if hit and time.time() - hit[0] < CACHE_TTL:
        _cache.move_to_end(key)
        return hit[1]
    _cache.pop(key, None)
    return None


def _cache_put(key: str, text: str):
    if CACHE_SIZE <= 0 or not text:
        return
    _cache[key] = (time.time(), text)
    _cache.move_to_end(key)
    while len(_cache) > CACHE_SIZE:
        _cache.popitem(last=False)


@traceable(run_type="llm", name="qwen3-8b")
async def chat(messages: list[dict], max_tokens: int = 512, temperature: float = 0.2, schema: dict | None = None) -> str:
    """One AI call. `schema` = JSON schema for constrained decoding (the server can only produce that shape)."""
    global _schema_ok
    if MOCK:
        return "[mock LLM] " + messages[-1]["content"][:200]
    body = {
        "model": MODEL,
        "messages": messages,
        "max_tokens": min(max_tokens, 1024),
        "temperature": temperature,
        # Qwen3 "thinks" by default and burns the token budget; switch it off.
        "chat_template_kwargs": {"enable_thinking": False},
    }
    if schema and _schema_ok:
        body["response_format"] = {"type": "json_schema", "json_schema": {"name": "reply", "schema": schema}}
    key = hashlib.sha256(json.dumps(body, sort_keys=True, ensure_ascii=False).encode()).hexdigest()
    if (cached := _cache_get(key)) is not None:
        trace.cache_hit("llm")
        return cached
    async with _lock:  # one request at a time per key
        t0, retries = time.perf_counter(), 0
        for delay in (2, 4, 8, None):
            async with _client() as c:
                r = await c.post(
                    f"{BASE_URL}/chat/completions",
                    headers={"Authorization": f"Bearer {API_KEY}"},
                    json=body,
                )
            if r.status_code == 400 and "response_format" in body:  # server without constrained decoding
                trace.error("llm_error", "json_schema not supported, retrying without it")
                _schema_ok = False
                body.pop("response_format")
                continue
            if r.status_code in (429, 503) and delay:
                retries += 1
                await asyncio.sleep(delay)
                continue
            if r.status_code >= 400:
                trace.error("llm_error", f"HTTP {r.status_code}")
            r.raise_for_status()
            data = r.json()
            usage = data.get("usage") or {}
            trace.llm_call((time.perf_counter() - t0) * 1000, usage.get("prompt_tokens", 0),
                           usage.get("completion_tokens", 0), retries)
            _report_usage(usage.get("prompt_tokens", 0), usage.get("completion_tokens", 0), MODEL)
            text = data["choices"][0]["message"]["content"] or ""
            text = re.sub(r"<think>.*?</think>", "", text, flags=re.S).strip()
            _cache_put(key, text)
            return text
    trace.error("llm_error", "busy after retries")
    raise RuntimeError("LLM unavailable after retries")


async def chat_json(messages: list[dict], max_tokens: int = 400, retries: int = 2, schema: dict | None = None) -> dict:
    """Ask for JSON (constrained to `schema` when given), parse it, retry on bad JSON (small-model safety net)."""
    for _ in range(retries + 1):
        text = await chat(messages, max_tokens=max_tokens, temperature=0, schema=schema)
        m = re.search(r"\{.*\}", text, re.S)
        if m:
            try:
                return json.loads(m.group(0))
            except json.JSONDecodeError:
                pass
        trace.error("malformed_json", text[:80])
        messages = messages + [
            {"role": "assistant", "content": text},
            {"role": "user", "content": "That was not valid JSON. Reply with ONLY the JSON object."},
        ]
    trace.error("json_gave_up")
    return {}
