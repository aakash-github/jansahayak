# JanSahayak: one-page spec (Track B, part I)

## Problem
Indian citizens miss government schemes they could get because the rules are spread over hundreds of long PDFs and portals, mostly in English. JanSahayak lets a farmer, student or small-business owner describe themselves in plain English or Hindi and get the schemes that may suit them, why, which documents to keep ready and the official link.

## Users
| User | Typical question |
|---|---|
| Farmer | "I own 2 acres in UP, age 40. Any help for irrigation?" |
| Student | "SC student, IIT admission, family income 5 lakh" |
| Entrepreneur | "I want to start a pickle unit at home in Bihar" |

## What it does
- Builds a profile from the chat (occupation, state, age, income, category, land…), across several turns.
- Checks every scheme's eligibility rules **in code** and shows up to 5 scheme cards: may be eligible / need more info / appears not eligible.
- Answers questions about one scheme (how to apply, documents, conditions) with citations [S1]–[S4] from the official PDFs.
- Asks at most one useful follow-up question at a time, with tap-to-answer buttons.
- Works in English and Hindi, typed or spoken.

## What it refuses or never does
- Off-topic requests (poems, coding, cricket…) → polite refusal.
- Never says "you are eligible", only "you may be eligible", and always points to the official site or a CSC.
- Never asks for, repeats or stores Aadhaar, bank, PAN or phone numbers. If a user types one, it is masked before the AI sees it. Profiles last only for the session.
- Never names a scheme that is not in the catalogue, and never states an amount or limit that is not in the scheme data or documents. The critic checks both.
- Ignores instructions hidden in messages or documents ("ignore your rules…"), but still helps if the user also says who they are.
- Never approves, sanctions or guarantees anything. Schemes whose rules have not yet been checked by the team are labelled as such.
- Details: [RESPONSIBLE_AI.md](../docs/RESPONSIBLE_AI.md).

## Inputs and outputs
- **Input:** a chat message (or a tapped button).
- **Output:** a short reply with citations, scheme cards (status, benefit, conditions, documents, link), sources, and an optional follow-up question.

## What counts as a correct answer
A reply passes only if all four checks pass (see [EVALUATION.md](../docs/EVALUATION.md)):
1. **Behaviour:** the right kind of reply (find / focus / which / ask / refuse).
2. **Schemes:** every expected scheme is shown, and no scheme the user clearly fails is offered.
3. **Facts:** the key facts asked about appear (amounts, limits, deadlines, documents).
4. **Safety:** no guarantee, no personal numbers repeated.

## Constraints
- Course-hosted Qwen3-8B (one request at a time per key) and the course embedding API (bge-small).
- Free hosting: Render (512 MB) for the backend and GitHub Pages for the frontend.
- 28 central and state schemes, with 67 official PDFs indexed (2,425 chunks). This is below the Track B target of 500–2,000 documents: few citizen-facing PDFs exist per scheme, many are scans or Hindi/Marathi only, and some sites block downloads.

## Success targets
| Metric | Target | Now |
|---|---|---|
| End-to-end accuracy (99 queries) | ≥ 85% | 92% |
| Safety violations | 0 | 0 |
| Latency p95 | < 15 s | 14.8 s locally, slower on free Render |
