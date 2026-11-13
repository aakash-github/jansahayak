# Pending work & enhancements

Ideas and fixes we have discussed but not built yet. Pick one, mark it 🚧 with your name, and move it to "Done" when merged.

Status: ⏳ not started · 🚧 in progress · ✅ done

---

## 1. User experience: fewer questions before the first answer ⏳

**Problem.** The bot has a fixed checklist per user type (farmer: state → land → age; student: income → course → category; business: age → business type → state). It won't show any scheme until every item is answered, and asks one item per message. That makes about 3 round trips (~6 s each) before the user sees anything. On voice it's worse, because every question is read aloud.

**Proposed fix (suggested build order A → B → C → D → E):**

| | Change | Where | Effort |
|---|---|---|---|
| **A** | **Answer first, then improve.** Only "farmer / student / business?" blocks. After that, show schemes immediately with what we know. Unknown details show as "Need more info" on the cards. | `backend/app/agents.py` (`route_after_intake`) | ~30 min |
| **B** | **At most one question per reply, and only the one that matters most.** Ask about whichever unknown field appears in the most shown schemes' rules (e.g. `category` for students), not a fixed order. If no unknown field would change the results, ask nothing. | `agents.py` + `eligibility.py` | ~30 min |
| **C** | **Tap-to-answer buttons** under the question: age `[18–40] [41–60] [60+] [Skip]`, category `[General] [OBC] [SC] [ST] [EWS]`, state = common states + "Other". Backend returns `followup_field` + `options`; frontend renders chips. | `main.py`, `agents.py`, `frontend/src/App.jsx` | ~1 h |
| **D** | **Hint up front:** welcome screen says *"Tip: say everything at once, e.g. 'Farmer in Bihar, 2 acres, age 35'"*. The bot already understands several details in one message. | `App.jsx` | 10 min |
| **E** | **Editable "Your details" panel:** tap a value to change it (e.g. 5 acres → 2) and the results refresh without chatting again. Needs a small `/api/profile` endpoint. | `main.py`, `App.jsx` | ~1 h |

Mock-up after A + B + C:
```
┌───────────────────────────────────────────────┐
│ ✓ You may be eligible for PM-KISAN, PMFBY…    │
│ [scheme cards]                                │
│                                               │
│ 💡 Tell me your age to check 2 more schemes   │
│  [18–40] [41–60] [60+] [Skip]                 │
└───────────────────────────────────────────────┘
```
**Goal:** first useful answer after 1 message instead of 4, never more than one optional question per reply, answerable with one tap.

---

## 2. Scheme wording: PM-KMY (and similar "pension later" schemes) ⏳

**Reported:** a 25-year-old farmer got *"Get a pension of Rs 3,000 per month after age 60… check if you are not excluded"* and it looked wrong.

**Analysis.** The eligibility result is **correct**: PM-KMY is joined between ages 18 and 40, and all 4 conditions were met (farmer, 25 ≥ 18, 25 ≤ 40, land ≤ 2 ha). The wording is the problem:

1. "Pension after age 60" reads like "only for people over 60". **Fix `benefit` in `schemes.json` (FARM-04):** *"Join now (age 18–40), pay about Rs 55–200 a month until 60, then get Rs 3,000 a month for life."*
2. "Check you are not excluded" is vague. **Add a condition** `not_excluded` (yes/no) with the exclusions from section 5 of the PDF: institutional land holders; current or former ministers, MPs, MLAs and mayors; government employees; income-tax payers; doctors, engineers, lawyers and other professionals; people already in NPS / ESIC / EPFO.
3. It doesn't say what the user would pay. **Add the contribution-by-joining-age chart** from the PDF (≈ Rs 55 at 18 up to Rs 200 at 40) to the benefit text or a chunk, so the answer can name a figure for their age.

**Also:** review all 28 benefit texts for the same kind of confusion (pension, "after", "up to").

---

## 3. Data ⏳

| Item | Detail |
|---|---|
| Verify all 28 schemes | Check each rule, amount and link in `backend/data/schemes.json` against its PDF (`sources.json` has the link). |
| Full guidelines for KCC, PMEGP, CGTMSE | Only short official summaries today. Full PDFs are on RBI / KVIC / cgtmse.in sites that block scripts. Download by hand into `backend/data/raw/`, add to `sources.json`, run `ingest.py`. |
| 15 scanned PDFs (`need_ocr`) | Includes PMS-SC (an important scholarship). Run OCR (e.g. `ocrmypdf`), then ingest. |
| 2 non-English PDFs (`not_english`) | CGSS (Hindi), Birsa Munda (Marathi). Needs translation or a multilingual embedding model. |
| 20 `later` PDFs | Useful schemes not yet in `schemes.json` (FPO, NEC merit, overseas scholarships, ICAR, etc.). Add the scheme, then change status to `use`. |
| Re-run the failed link | "PMFME & AIF Convergence" timed out (`broken`). |

---

## 4. Quality & evaluation ⏳

| Item | Detail |
|---|---|
| Fill eval gold answers | `eval/eval_set.csv` (30 queries) has empty expected-scheme columns. Fill them, then run `eval/run_eval.py` for precision/recall. |
| Hindi search | The embedding model is English-only and we search with the user's raw message, so Hindi questions get weaker search results. Build the search query from the profile + scheme names in English instead. |
| Chat history to the LLM | The answer step sees the profile, not past messages. Follow-ups like "explain the second one" may miss context. Send the last 2–3 turns. |
| Planner is fixed | Always runs the same 4 tools. Fine for now; could let the LLM pick tools later. |

---

## 5. App & ops ⏳

| Item | Detail |
|---|---|
| Screen labels in Hindi | Chat replies follow the user's language, but buttons and panels are English only. Add a UI language switch. |
| Business type from Hindi | "दुकान खोलना" (open a shop) is not extracted as a business type yet. |
| Replace API keys | The chat key and the embedding key were shared in chat. Ask the coordinator for new keys and update `backend/.env` + Render. |
| Back up `capstone_files/` | Research files, certificates and keys exist only on one laptop. Copy to a private Drive/OneDrive folder. |
| Render: `EMBED_LOCAL_FALLBACK=0` | Make sure it is set in Render → Environment (prevents out-of-memory if the course embedding API is down). |
| Cold start | Render free tier sleeps after 15 min (~50 s first reply). Optional: a free uptime pinger, or a paid plan for the demo day. |

---

## Done ✅

- Hindi follow-up questions and replies (sticky chat language)
- Course embedding API (VM02) with local fallback
- 87-PDF manifest (`backend/data/sources.json`) + download script; 28 schemes; PDF-based RAG index (1,884 chunks)
- Ask age (farmers), category (students), state (business); yes/no scheme facts extracted from chat
- Fixed Render out-of-memory crash (reranker batching)
- Mobile: single mic (no 🎤 in the placeholder)
