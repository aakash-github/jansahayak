# Responsible AI and human oversight

How JanSahayak protects users, avoids wrong or unsafe answers, and keeps people in charge of the decisions that matter. This covers part VI of the Track B brief.

**The principle:** JanSahayak gives *guidance*, never a decision. Code (not the AI) checks eligibility rules. The AI only reads the user's message and writes the reply. The government office or a Common Service Centre (CSC) always makes the final decision.

---

## 1. Safeguards at a glance

| Risk | Safeguard | Where in the code | How it is tested |
|---|---|---|---|
| User shares Aadhaar, phone, bank, PAN or e-mail | **Masked before anything else sees the message** (the AI, the session, traces, LangSmith). The user is told it was removed and why | `backend/app/privacy.py`, called first in `main.py` | `test_responsible_ai.py` (10 formats incl. Hindi digits; normal numbers like income and acres untouched); eval X-02, X-04, X-11, X-12 |
| Prompt injection ("ignore your rules", fake "SYSTEM:" text, role-play) | Both prompts treat the message and documents as information, not instructions; AI-extracted profile values are type-checked (`_clean`); eligibility is decided in code, so injected text cannot change it | `INTAKE_PROMPT`, `RULES` and `intake()` in `agents.py` | Unit tests; eval X-03 and X-06 to X-15 |
| Over-refusal of injected but genuine requests | "Ignore your rules… I am a student" is answered safely instead of refused, because the message still says who the user is. A purely off-topic message is still refused, even mid-chat | `on_topic` in `intake()`, `route_after_intake()` | Unit tests; eval X-03, X-10 |
| Invented schemes | Critic rejects any catalogue scheme name the tools did not return | `critic()` | Eval (`critic_unresolved` counts as hallucination) |
| Invented amounts, limits or dates | Critic checks that **every number in the reply** (≥ 10, or with decimals) appears in the scheme data, evidence or user profile. "2.5 lakh" = 250000; Hindi digits count | `unsupported_numbers()` in `agents.py` | Unit tests; replay over the 67 saved eval answers flagged 0 |
| "You are eligible" / guarantees | Critic asks for a rewrite. If the last rewrite still says it, **code replaces the wording** with "you may be eligible" (Hindi: "पात्र हो सकते हैं") | `critic()` | Unit tests; eval X-01, X-05, X-07, X-09, X-15 |
| Answer still breaks a rule after the last rewrite | A visible caution is added: "Some details could not be checked against the official documents…" | `critic()` | Unit test |
| Scheme data not yet checked by a person | Each card shows "Our team is still checking these rules…" until the scheme is marked `verified` | `_card()` in `agents.py`, `SchemeCard` in `App.jsx` | Unit test |
| Uncertainty | Three statuses (may be eligible / need more info / condition not met), "Data as of" date, sources with page numbers, official link and CSC in every answer | `eligibility.py`, `App.jsx` | Eval safety checks |
| Off-topic requests | Polite refusal | `refuse()` | Eval R-01 to R-05 |
| Personal data kept too long | Profiles live only in server memory for the chat; traces store no message text | `main.py`, `trace.py` | Code review |
| Outside services seeing messages | LangSmith is off unless `LANGSMITH_TRACING=true`; keep it off in production | `.env.example` | Config review |

---

## 2. Personal data

```
User message ──► privacy.redact() ──► AI service, session, traces, LangSmith
                  "My Aadhaar is 1234 5678 9012"  →  "My Aadhaar is [Aadhaar number removed]"
```

- **What is masked:** Aadhaar (12 digits, grouped or not), Indian mobile numbers (with or without +91/0), bank account numbers (9–18 digits), PAN, e-mail addresses. Devanagari digits are handled too.
- **What is kept:** the details the rules need (age, income, acres, state, category…). Incomes are 6–8 digits or written with commas or "lakh", so they are never mistaken for an account number.
- **What the user sees:** "🔒 For your safety I removed a personal number from your message…" (English or Hindi), and the reply JSON says `"pii_masked": true`.
- **Traces** record only *which kind* was masked (e.g. `["aadhaar"]`), never the number.
- The user's own chat bubble on their screen still shows what they typed. It is never sent anywhere else.

---

## 3. Human in the loop

People stay in charge at four points.

### a) Scheme data review (before data is shown as checked)

Every scheme in `backend/data/schemes.json` has `verification_status`. It starts as `needs_review`, and the card shows a warning until a team member completes this checklist against the scheme's **official PDF** (`source_url`) and **portal** (`official_url`):

| # | Check |
|---|---|
| 1 | Scheme name and benefit amounts match the latest official guideline |
| 2 | Every rule (`field`, `op`, `value`) matches the official eligibility text, including age, income and land limits, category and state |
| 3 | Nothing important is missing (exclusions such as "income-tax payers not eligible", or "one per family") |
| 4 | Required documents match the official list |
| 5 | `official_url` opens and is the right application or information page |
| 6 | The guideline date is recent; if the scheme has been revised or closed, update or remove it |

When all six pass, set:

```json
"verification_status": "verified",
"reviewed_by": "<team member>",
"reviewed_on": "YYYY-MM-DD",
"review_note": "Checked against <PDF name>, p.<pages>"
```

Then update `DATA_AS_OF` in `agents.py` and re-run `eval/run_eval.py`. **Current status: 0 of 28 schemes verified.**

### b) Final decisions stay with officials
The app never approves, sanctions or guarantees anything. Every answer ends with the official link or "confirm at your nearest CSC", and cards say "May be eligible", never "Eligible".

### c) Evaluation answers written by people
Gold answers in `eval/eval_set.csv` are written by the team from official rules, not copied from the bot. Failures are read by a person before any fix is made.

### d) Monitoring
`GET /api/traces` shows recent requests with errors, critic problems (`critic_unresolved`) and masked-data counts. A team member should review it regularly during the pilot.

---

## 4. Known limits (residual risks)

| Limit | Effect | Mitigation |
|---|---|---|
| Number check skips small whole numbers (< 10) | A wrong "2 instalments" or "Class 9" would not be caught | Scheme data review; the cards show the official rule text |
| Number check is not a full fact check | A wrong sentence without a number (e.g. wrong portal step) is not caught | Citations shown with page numbers; official link in every answer |
| Masking is pattern-based | A number typed in words ("nine eight seven…") is not masked | The prompt says never to ask for or repeat such data; nothing is stored long term |
| 28 schemes, all `needs_review` | Rules may be out of date | Warning on every card until reviewed (3a) |
| Hindi search is weaker (English-only embedding model) | Hindi questions get fewer good passages | The rules engine still works the same in Hindi |

---

## 5. How to check it

```bash
python -m pytest backend/tests -q        # unit tests, no AI calls (mock mode)
backend/.venv/Scripts/python eval/run_eval.py X- R-   # safety + refusal queries with the real model
```
