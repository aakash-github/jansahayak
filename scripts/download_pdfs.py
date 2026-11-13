"""Download the scheme PDFs listed in backend/data/sources.json into backend/data/raw/.

Usage (from repo root, using the backend venv):
    python scripts/download_pdfs.py          # only PDFs tagged "use" (what the chatbot needs)
    python scripts/download_pdfs.py --all    # every working PDF, for the record

Files are saved as <SCHEME_ID>__<name>_<urlhash>.pdf (what ingest.py expects); entries without a
scheme ID are saved as <status>__<name>.pdf. The PDFs are NOT committed to git (too large);
sources.json is the record of what we collected and why each file is used or skipped.

Status tags in sources.json:
    use          used for RAG; scheme exists in schemes.json
    later        useful for citizens but scheme not yet added to schemes.json
    not_citizen  written for governments/agencies/institutions, not individuals
    need_ocr     scanned images, no extractable text (needs OCR first)
    not_english  Hindi/Marathi text; our embedding model is English-only
    broken       link did not download
"""
import hashlib
import json
import re
import sys
from pathlib import Path
from urllib.parse import urlparse

import httpx

DATA = Path(__file__).resolve().parent.parent / "backend" / "data"
RAW = DATA / "raw"
OFFICIAL = (".gov.in", ".nic.in", "nabard.org", "sidbi.in", "aicte-india.org", "rbi.org.in", "cgtmse.in")


def official(url: str) -> bool:
    host = (urlparse(url).hostname or "").lower()
    return any(host == d.lstrip(".") or host.endswith("." + d.lstrip(".")) for d in OFFICIAL)


def slug(text: str) -> str:
    return re.sub(r"[^A-Za-z0-9]+", "_", text).strip("_")[:60]


def file_name(it: dict) -> str:
    tag = hashlib.md5(it["pdf_url"].encode()).hexdigest()[:6]  # keeps names unique
    return f"{it['scheme_id'] or it['status']}__{slug(it['scheme_name'])}_{tag}.pdf"


def main():
    everything = "--all" in sys.argv
    items = json.loads((DATA / "sources.json").read_text(encoding="utf-8"))
    RAW.mkdir(exist_ok=True)
    seen, saved, skipped = set(), 0, 0
    # verify=False: several government sites have incomplete certificate chains.
    # We still only accept official domains and check the bytes are a real PDF.
    with httpx.Client(timeout=90, follow_redirects=True, verify=False, headers={"User-Agent": "Mozilla/5.0"}) as c:
        for it in items:
            if it["status"] == "broken" or (it["status"] != "use" and not everything):
                continue
            out = RAW / file_name(it)
            if out.exists():
                skipped += 1
                continue
            if not official(it["pdf_url"]):
                print("[skip, not an official domain]", it["pdf_url"])
                continue
            try:
                r = c.get(it["pdf_url"])
                r.raise_for_status()
                if not r.content.startswith(b"%PDF"):
                    print("[skip, not a PDF]", it["scheme_name"])
                    continue
                h = hashlib.sha256(r.content).hexdigest()
                if h in seen:
                    print("[skip, duplicate file]", it["scheme_name"])
                    continue
                seen.add(h)
                out.write_bytes(r.content)
                saved += 1
                print(f"[saved] {out.name} ({len(r.content) // 1024} KB)")
            except Exception as e:
                print(f"[failed] {it['scheme_name']}: {type(e).__name__} {e}")
    print(f"\nDone: {saved} downloaded, {skipped} already present, in {RAW}")


if __name__ == "__main__":
    import warnings
    warnings.filterwarnings("ignore")
    main()
