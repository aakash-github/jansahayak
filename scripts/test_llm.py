"""Step 1 of the project: prove the IIT KGP endpoint works. Run from backend/ with .env values exported:
    .venv/Scripts/python ../scripts/test_llm.py
"""
import asyncio, os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))
from app import llm
print("MOCK mode" if llm.MOCK else f"Calling {llm.BASE_URL}")
print(asyncio.run(llm.chat([{"role": "user", "content": "Explain RAG in three steps."}], max_tokens=200)))
