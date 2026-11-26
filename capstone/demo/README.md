# Backup demo video

`record_demo.py` drives the real app in Edge with Playwright, adds a caption bar per scene, and saves
`JanSahayak_demo.mp4` (1280x720, about 5 min) here.

```bash
# 1. backend (fast local replies, no rate limit, no tracing)
cd backend && RATE_LIMIT_PER_MIN=0 RATE_LIMIT_TOTAL_PER_MIN=0 LANGSMITH_TRACING=false \
  .venv/Scripts/uvicorn app.main:app --port 8000
# 2. frontend
cd frontend && VITE_API_URL=http://localhost:8000 npx vite --port 5173 --strictPort
# 3. record (from the repo root)
backend/.venv/Scripts/python capstone/demo/record_demo.py --app http://localhost:5173
```

Scenes: title, problem, farmer (cards, citations, follow-up, "How to apply"), Hindi student,
entrepreneur, safety (Aadhaar, prompt injection, off-topic), LangSmith traces, results, Responsible AI,
limitations, end card. Live replies differ slightly run to run.
