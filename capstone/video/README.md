# Explainer video (about 11 min, 1920x1080)

One farmer's question, followed through the whole system. The left half is the live app. The right half is an
**X-ray** replayed from that request's real trace: intake, router, rules engine, hybrid search (BM25 + dense →
fusion → rerank), answer, critic, follow-up. Then follow-ups and the cache, Hindi, the guardrails, three lessons
(documents and chunking, working with a small model, evaluation), observability, and a closing callback.

| File | What it does |
|---|---|
| `narration.py` | The script: one entry per voice clip. Edit the words here |
| `voice.py` | Makes one WAV per clip with the chosen voice. Clips are cached by text, so changing one line only re-voices that line |
| `stage.html`, `stage.css`, `stage.js` | All scenes, the X-ray panel and the animations |
| `make_video.py` | Drives the stage and the live app, records frames, lays the voice clips on the timeline, encodes the MP4 |
| `JanSahayak_explainer.mp4` | The current render |

## Re-render with a different voice (for a teammate)

1. **Get the branch and the extra packages** (once):
   ```bash
   git checkout explainer-video          # or main, after it is merged
   backend/.venv/Scripts/pip install -r capstone/video/requirements.txt
   ```
2. **Choose the voice** in `backend/.env` (never commit this file):
   ```
   # ElevenLabs. Paid plans can use any Voice Library voice (e.g. an Indian-English narrator); free plans only the Default ones.
   VOICE_PROVIDER=elevenlabs
   ELEVENLABS_API_KEY=your_key
   ELEVENLABS_VOICE_ID=voice_id

   # or the free Indian-English voice used in the current render (Hindi words switch to a native Hindi voice):
   VOICE_PROVIDER=edge
   EDGE_VOICE=en-IN-PrabhatNeural      # or en-IN-NeerjaNeural / en-IN-NeerjaExpressiveNeural
   ```
   Check the cost first: `backend/.venv/Scripts/python capstone/video/voice.py --chars` (about 7,900 characters;
   ElevenLabs bills per character). `voice.py` on its own makes only the clips, so you can listen to them in
   `capstone/video/_audio/` before recording.
3. **Start the app** (two terminals), with the backend started fresh so its cache is empty:
   ```bash
   cd backend && RATE_LIMIT_PER_MIN=0 RATE_LIMIT_TOTAL_PER_MIN=0 LANGSMITH_TRACING=false \
     .venv/Scripts/uvicorn app.main:app --port 8000
   cd frontend && VITE_API_URL=http://localhost:8000 npx vite --port 5173 --strictPort
   ```
   Send one unrelated question once to warm up the search models, e.g.
   `curl -s localhost:8000/api/chat -H "Content-Type: application/json" -d "{\"session_id\":\"warm\",\"message\":\"I am a student in Delhi\"}"`.
   Do **not** ask the farmer question before recording: the cache scene needs the first farmer request to be fresh.
4. **Record** (about 15 minutes, hands off):
   ```bash
   backend/.venv/Scripts/python capstone/video/make_video.py     # → capstone/video/JanSahayak_explainer.mp4
   ```
   If only the final encoding step fails, `make_video.py --encode-only` redoes it from the saved frames.

**Any voice fits.** Each scene waits for its own clip, subtitles follow the real clip length, and the fixed
animations (title, PDF pile, chunk page, lessons, results chart, closing) stretch or shrink to the clip they play
under. A faster or slower voice only changes the total length (about 10–11 min at a normal pace).

Live replies, timings and the reranking order differ a little from run to run. The X-ray always shows the
numbers of the request it is replaying. `<break time="0.6s" />` in `narration.py` marks a pause.
