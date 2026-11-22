# How JanSahayak works (simplified)

The whole system, one piece at a time, following one message:

> **"I own 2 acres in UP, age 40. Any help for irrigation?"**

For more detail see [How it works (full)](HOW_IT_WORKS.md) and [Document search (RAG) and embeddings](RAG_AND_EMBEDDINGS.md).

---

## 0) The big picture

```
 User message
     │
     ▼
 ① Intake 🧠 ──► ② Router ──┬─► refuse / ask / which (fixed replies, no AI)
                            │
                            ├─► ③ Rules engine ⚙️ ──► ④ Document search 🔎
                            │                                │
                            └─► (one scheme) ──────────────► │
                                                             ▼
                                         ⑤ Answer 🧠 ──► ⑥ Critic ⚙️ ──► ⑦ Follow-up ⚙️ ──► Reply
                                              ▲              │
                                              └── fix it ────┘

 🧠 = AI (only 2 calls)     ⚙️ = plain Python, no AI     ⑧ Session memory joins the turns
```

Only two steps use the AI: **reading** the message (①) and **writing** the reply (⑤). Everything that *decides* something is code.

---

## ① Intake: message → profile

`backend/app/agents.py` → `intake()`

**1) Shortcuts that skip the AI**
```
 Tapped "How to apply" on a card        ──► mode = focus, no AI call
 Tapped an answer button ("₹2.5–3.5 lakh") ──► value saved directly, no AI call
```

**2) Otherwise the AI reads the message and returns JSON only**
```
"I own 2 acres in UP, age 40. Any help for irrigation?"
        │   🧠 INTAKE_PROMPT: "extract a profile, never guess"
        ▼
{ "intent": "find_schemes",
  "profile": { "occupation": "farmer", "land_acres": 2,
               "state": "Uttar Pradesh", "age": 40 } }
```
- The AI also gets the profile so far and the last question asked, so a reply like "yes" or "30" makes sense.
- It can only fill known fields (occupation, state, age, income, category, gender, course…). Anything else is dropped.
- It is told to never record Aadhaar, bank or phone numbers, and to ignore text that tries to change its instructions.
- If the JSON is bad, we ask again (up to 2 retries).

**3) Safety nets in code, for when the small model slips**
```
 AI forgot occupation?   ──► word patterns: "acres|crops|kisan" → farmer
                                            "college|admission|IIT" → student
                                            "shop|startup|artisan" → entrepreneur
 Still unknown?          ──► schemes named in the message share one group? use it
 "how do I apply" said,
  but AI missed it?      ──► intent = scheme_question
```

---

## ② Router: which kind of reply?

`_mode()` and `route_after_intake()`, plain code:

```
                    ┌─ not about schemes ──────────────► REFUSE  (fixed polite text)
                    ├─ exactly 1 scheme named ─────────► FOCUS   ("tell me about KCC")
 message + profile ─┼─ 2+ schemes named / "compare" ───► FIND    (list, named ones first)
                    ├─ "how to apply?" + 2+ cards shown► WHICH   (buttons: which scheme?)
                    ├─ farmer/student/business unknown ► ASK     (that one question only)
                    └─ otherwise ──────────────────────► FIND
```
Our example: no scheme named, occupation known → **FIND**.

---

## ③ Rules engine: who is eligible (no AI)

`backend/app/eligibility.py` → `find_schemes()`

Each scheme's rules are written down as data in `backend/data/schemes.json`, e.g. PM-KISAN:
```json
"rules": [
  {"field": "occupation", "op": "==", "value": "farmer", "text": "Landholding farmer family"},
  {"field": "land_acres", "op": ">",  "value": 0,        "text": "Owns cultivable land in their name"}
]
```

**Step 1: filter**
```
28 schemes ──► keep only the user's group (farmer)
           ──► drop state-only schemes from other states
           ──► 10 farmer schemes left
```

**Step 2: check every rule** (met ✅ · not met ❌ · unknown ❓ = the user didn't say)
```
PM-KISAN       occupation == farmer ✅   land_acres > 0 ✅          → potentially_eligible
Scheme X       age between 18–40 ✅      income ≤ limit ❓           → more_info_needed
Scheme Y       age ≤ 35 ❌                                          → appears_not_eligible

 any ❌  → appears_not_eligible
 any ❓  → more_info_needed
 all ✅  → potentially_eligible
```

**Step 3: rank, best first**
```
 1. not ruled out (❌ go to the bottom)
 2. about the topic asked ("irrigation" → Per Drop More Crop moves up, via "topics" in schemes.json)
 3. better status (✅ before ❓)
 4. fewer unknowns
 5. more rules met
```
The top 5 become the **scheme cards**. Each card also gets two more tools: the **document checklist** and the **official link**.

---

## ④ Document search: proof from the PDFs (no AI writing)

`backend/app/retrieval.py`. Full details: [RAG_AND_EMBEDDINGS.md](RAG_AND_EMBEDDINGS.md)

```
 question + names of the 5 schemes
      │
      ├─► keyword search (BM25) ───────── top 20 ┐
      └─► meaning search (embeddings) ─── top 20 ┘──► merge (RRF) ──► top 12
                                                                       │
                                         re-ranker reads each pair ────┘──► best 4 = [S1]–[S4]
 Only chunks from the matched schemes' own PDFs are searched.
```

---

## ⑤ Answer: the AI writes, from facts it is given

`answer()`, 🧠 AI call #2:
```
 Given to the AI:  profile + 5 cards (status, benefit, each rule ✅❌❓) + 4 PDF passages + question
 Rules:            use ONLY these schemes · "may be eligible" · cite [S1] · under 80 words (find)
                   or 3–5 apply steps (focus) · reply in Hindi if the user wrote Hindi
        ▼
 "You may be eligible for 4 schemes. **Per Drop More Crop** helps with drip and
  sprinkler irrigation [S1]… Confirm on the official site or at a CSC."
```
The AI **cannot** change who is eligible. It only explains what the rules engine decided.

---

## ⑥ Critic: checking the reply (no AI)

`critic()`
```
 Does the reply name a scheme that is NOT on the cards?   ──► "remove it"
 Does it say "you are eligible" / "आप पात्र हैं"?          ──► "say may be eligible"
        │
   problem? ──► back to ⑤ with the notes (at most 10 steps in total)
   OK?      ──► ⑦
```

---

## ⑦ Follow-up: the one most useful question (no AI)

`backend/app/followups.py` → `pick()`
```
 Look at ALL matching schemes marked ❓ (not just the 5 shown):
    income unknown   → would settle 3 schemes
    category unknown → would settle 1 scheme
        ▼
 Ask about income, with tap buttons:
 [Up to ₹2.5 lakh] [₹2.5–3.5 lakh] [₹3.5–4.5 lakh] [₹4.5–8 lakh] [More than ₹8 lakh]
```
- The button ranges match the rule limits, so tapping gives the same result as typing the exact number.
- It never asks the same thing twice.
- After 3 questions it stops, unless one answer would settle 2 or more schemes.
- No question after a focus answer.

---

## ⑧ Session memory: joining the turns

`backend/app/main.py` → `SESSIONS`
```
 Turn 1: "I am a farmer"            profile = {occupation: farmer}
 Turn 2: "3 acres in Haryana, 30"   profile = {occupation, land_acres, state, age}  ← merged
 Turn 3: "How do I apply?"          last cards remembered → FOCUS or WHICH
```
Memory is held on the server only, never in a database. It is cleared on **Reset** or when the server restarts, so no personal data is kept.

---

## Who does what

| Step | AI or code | Why |
|---|---|---|
| ① Intake | 🧠 AI + code safety net | Understanding free text, Hindi and Hinglish needs AI |
| ② Router | ⚙️ code | Must be predictable |
| ③ Rules engine | ⚙️ code | Eligibility must never be guessed |
| ④ Search | ⚙️ code + embedding model | Finds proof; writes nothing |
| ⑤ Answer | 🧠 AI | Writing friendly text is what AI is good at |
| ⑥ Critic | ⚙️ code | Catches the AI's mistakes |
| ⑦ Follow-up | ⚙️ code | Picks the most useful question by counting |

This split is why the full system passes **90%** of the 79 original test questions (92% of all 99 now), while one big prompt doing everything passes 65–76% of the same 79. See [Evaluation](EVALUATION.md#7-prompting-baseline-one-prompt-vs-the-agent-system).
