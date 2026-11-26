"""Text -> 384 numbers (embeddings) with bge-small-en-v1.5.

1st choice: the course-hosted embedding API (IIT KGP VM02), fast and uses no memory on our server.
Fallback:   the same model run locally with fastembed (loaded only if the API fails).
Both give identical vectors (tested: cosine similarity 1.0), so they can be mixed freely.

API rules from the quickstart: max 16 texts per request, each chunk within 512 tokens,
retry briefly on capacity errors.
"""
import os
import time

import httpx
import numpy as np
from dotenv import load_dotenv

from . import trace

load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

BASE_URL = os.getenv("EMBED_BASE_URL", "")          # https://103.42.50.41:1035/v1
API_KEY = os.getenv("EMBED_API_KEY", "")
CA_CERT = os.getenv("EMBED_CA_CERT_PATH", "")       # path to vm02-ca.crt
API_MODEL = os.getenv("EMBED_MODEL", "bge-small-en-v1.5")
LOCAL_MODEL = "BAAI/bge-small-en-v1.5"
BATCH = 16
# Render free tier has 512 MB; loading the local model there (+150 MB) can crash the server.
# Set EMBED_LOCAL_FALLBACK=0 on Render: if the API is down, search falls back to keywords (BM25) only.
LOCAL_FALLBACK = os.getenv("EMBED_LOCAL_FALLBACK", "1") != "0"

_local = None
last_source = "none"  # "api" or "local", handy for /health and debugging


def _api(texts: list[str], timeout: float) -> np.ndarray:
    out = []
    with httpx.Client(verify=CA_CERT or True, timeout=timeout) as c:
        for i in range(0, len(texts), BATCH):
            batch = texts[i:i + BATCH]
            for wait in (1, 2, 4, None):
                r = c.post(f"{BASE_URL}/embeddings", headers={"Authorization": f"Bearer {API_KEY}"},
                           json={"model": API_MODEL, "input": batch})
                if r.status_code in (429, 503) and wait:
                    time.sleep(wait)
                    continue
                r.raise_for_status()
                break
            data = sorted(r.json()["data"], key=lambda d: d["index"])
            out.extend(d["embedding"] for d in data)
    return np.array(out, dtype=np.float32)


def _local_embed(texts: list[str]) -> np.ndarray:
    global _local
    if _local is None:
        from fastembed import TextEmbedding
        _local = TextEmbedding(LOCAL_MODEL)
    return np.array(list(_local.embed(texts)), dtype=np.float32)


_query_cache: dict[str, np.ndarray] = {}  # search questions already embedded (same question -> no API call)


def embed(texts: list[str], timeout: float = 10) -> np.ndarray:
    """Embed texts; API first, local model if the API is not configured or fails.
    Single texts (search questions) are cached, up to 500."""
    if len(texts) == 1 and texts[0] in _query_cache:
        trace.cache_hit("embed")
        return _query_cache[texts[0]][None, :]
    v = _embed(texts, timeout)
    if len(texts) == 1:
        if len(_query_cache) >= 500:
            _query_cache.pop(next(iter(_query_cache)))
        _query_cache[texts[0]] = v[0]
    return v


def _embed(texts: list[str], timeout: float) -> np.ndarray:
    global last_source
    if BASE_URL and API_KEY:
        try:
            v = _api(texts, timeout)
            last_source = "api"
            return v
        except Exception as e:
            print("embedding API failed:", type(e).__name__, e)
            if not LOCAL_FALLBACK:
                raise
    v = _local_embed(texts)
    last_source = "local"
    return v
