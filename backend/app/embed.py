"""Text -> 384 numbers (embeddings) with bge-small-en-v1.5.

Model compliance (Track B): embeddings must come from the IIT KGP embedding API (VM02).
  - Default: API ONLY. If the API is missing or down, embed() raises and search falls back to
    keywords (BM25); no other embedding service is ever used silently.
  - Opt-in for offline laptop work only: EMBED_LOCAL_FALLBACK=1 runs the same model locally (fastembed).
    It gives identical vectors (cosine 1.0), but it is NOT the course service, so every local call is
    counted (STATS["local"]), shown in /health, in each request trace and in eval results, and
    eval/run_eval.py refuses to run with it switched on.

API rules from the quickstart: max 16 texts per request, each chunk within 512 tokens,
retry briefly on capacity errors.
"""
import os
import time

import httpx
import numpy as np
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

BASE_URL = os.getenv("EMBED_BASE_URL", "")          # https://103.42.50.41:1035/v1
API_KEY = os.getenv("EMBED_API_KEY", "")
CA_CERT = os.getenv("EMBED_CA_CERT_PATH", "")       # path to vm02-ca.crt
API_MODEL = os.getenv("EMBED_MODEL", "bge-small-en-v1.5")
LOCAL_MODEL = "BAAI/bge-small-en-v1.5"
BATCH = 16
# OFF unless explicitly set to 1 (see module docstring). Also keeps Render's 512 MB free tier safe.
LOCAL_FALLBACK = os.getenv("EMBED_LOCAL_FALLBACK", "0") == "1"

_local = None
last_source = "none"  # "api" | "local" | "failed": what served the most recent call
STATS = {"api": 0, "local": 0, "failed": 0}  # calls since start, for /health and eval results


class EmbeddingUnavailable(RuntimeError):
    """The course embedding API is not configured or failed, and the local fallback is off."""


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


def embed(texts: list[str], timeout: float = 10) -> np.ndarray:
    """Embed texts with the course API. The local model is used only if EMBED_LOCAL_FALLBACK=1."""
    global last_source
    reason = "EMBED_BASE_URL / EMBED_API_KEY not set"
    if BASE_URL and API_KEY:
        try:
            v = _api(texts, timeout)
            last_source = "api"
            STATS["api"] += 1
            return v
        except Exception as e:
            reason = f"embedding API failed: {type(e).__name__} {e}"
            print(reason)
    if not LOCAL_FALLBACK:
        last_source = "failed"
        STATS["failed"] += 1
        raise EmbeddingUnavailable(reason)
    print("WARNING: using the LOCAL embedding model (not the IIT KGP API):", reason)
    v = _local_embed(texts)
    last_source = "local"
    STATS["local"] += 1
    return v
