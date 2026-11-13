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

load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

BASE_URL = os.getenv("EMBED_BASE_URL", "")          # https://103.42.50.41:1035/v1
API_KEY = os.getenv("EMBED_API_KEY", "")
CA_CERT = os.getenv("EMBED_CA_CERT_PATH", "")       # path to vm02-ca.crt
API_MODEL = os.getenv("EMBED_MODEL", "bge-small-en-v1.5")
LOCAL_MODEL = "BAAI/bge-small-en-v1.5"
BATCH = 16

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


def embed(texts: list[str], timeout: float = 10) -> np.ndarray:
    """Embed texts; API first, local model if the API is not configured or fails."""
    global last_source
    if BASE_URL and API_KEY:
        try:
            v = _api(texts, timeout)
            last_source = "api"
            return v
        except Exception as e:
            print("embedding API failed, using local model:", type(e).__name__, e)
    v = _local_embed(texts)
    last_source = "local"
    return v
