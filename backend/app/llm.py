"""Client for the IIT KGP hosted Qwen3-8B (OpenAI-compatible chat API).

Rules from the Track B guide:
- 1 active request per group key  -> we serialise calls with a lock
- 60 req/min, 8192 tokens in+out, max_tokens <= 1024
- retry 429/503 with 2, 4, 8 s backoff, then give up
- no embeddings on this endpoint (we embed locally, see retrieval.py)
"""
import asyncio
import json
import os
import re

import httpx
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

BASE_URL = os.getenv("MODEL_BASE_URL", "")          # e.g. https://103.42.50.41:1034/v1
API_KEY = os.getenv("MODEL_API_KEY", "")
CA_CERT = os.getenv("MODEL_CA_CERT_PATH", "")       # path to vm0X-ca.crt
MODEL = os.getenv("MODEL_NAME", "Qwen/Qwen3-8B")

MOCK = not (BASE_URL and API_KEY)                   # lets the team run without a key
_lock = asyncio.Lock()


def _client() -> httpx.AsyncClient:
    return httpx.AsyncClient(verify=CA_CERT or True, timeout=90)


async def chat(messages: list[dict], max_tokens: int = 512, temperature: float = 0.2) -> str:
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
    async with _lock:  # one request at a time per key
        for delay in (2, 4, 8, None):
            async with _client() as c:
                r = await c.post(
                    f"{BASE_URL}/chat/completions",
                    headers={"Authorization": f"Bearer {API_KEY}"},
                    json=body,
                )
            if r.status_code in (429, 503) and delay:
                await asyncio.sleep(delay)
                continue
            r.raise_for_status()
            text = r.json()["choices"][0]["message"]["content"] or ""
            return re.sub(r"<think>.*?</think>", "", text, flags=re.S).strip()
    raise RuntimeError("LLM unavailable after retries")


async def chat_json(messages: list[dict], max_tokens: int = 400, retries: int = 2) -> dict:
    """Ask for JSON, parse it, retry on bad JSON (small-model safety net)."""
    for _ in range(retries + 1):
        text = await chat(messages, max_tokens=max_tokens, temperature=0)
        m = re.search(r"\{.*\}", text, re.S)
        if m:
            try:
                return json.loads(m.group(0))
            except json.JSONDecodeError:
                pass
        messages = messages + [
            {"role": "assistant", "content": text},
            {"role": "user", "content": "That was not valid JSON. Reply with ONLY the JSON object."},
        ]
    return {}
