"""Build the evidence index PDF: every capstone requirement with clickable links to the proof.

The submission portal takes one document, so this page lists where everything lives
(live app, code, report, video, traces) and maps each item of the Track B brief to its evidence.

Run from the repo root:
    backend/.venv/Scripts/python capstone/report/build_links.py
Output: capstone/report/JanSahayak_Links.pdf
"""
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = "https://github.com/aakash-github/jansahayak"
GH = f"{REPO}/blob/main/"
TREE = f"{REPO}/tree/main/"
APP = "https://aakash-github.github.io/jansahayak/"
API = "https://jansahayak-api-cgos.onrender.com"


def link(label, path):
    url = path if path.startswith("http") else GH + path
    return f'<a href="{url}">{label}</a>'


QUICK = [
    ("Live app", APP, "React front-end on GitHub Pages (English and Hindi, voice input)"),
    ("Source code", REPO, "Full agent stack: backend, front-end, evaluation scripts, data"),
    ("Technical report", GH + "capstone/report/JanSahayak_Report.pdf", "Design, experiments, results and limitations"),
    ("Demo video (5 min)", GH + "capstone/demo/JanSahayak_demo.mp4", "Recording of the real app: four users, safety tests, results"),
    ("Capstone folder", TREE + "capstone", "Brief-to-evidence map, specification, demo script"),
    ("Trace dashboard", GH + "capstone/screenshots/README.md", "8 LangSmith screenshots of real requests, with captions"),
    ("Built-in traces (live)", f"{API}/api/traces", "Step timings, AI calls, tokens and tools for recent requests (JSON)"),
    ("Backend health", f"{API}/health", "Free server: first reply after idle can take up to a minute"),
]

RESULTS = [
    ("91%", "End-to-end accuracy", "72 of 79 gold queries fully correct"),
    ("76%", "Best single prompt", "Same model, no agents, 4 strategies"),
    ("13 / 14", "Injection attacks blocked", "10 typed, 4 hidden in documents"),
    ("0", "Safety violations", "No guarantees, no ID numbers repeated"),
    ("2", "AI calls per message", "About 2,000 tokens per query"),
    ("300 words", "Best chunk size", "Right scheme in top 4 for 15/15 search tests"),
]

BRIEF = [
    ("I. Task decomposition", [
        ("Written specification: scope, refusals, what a correct answer is", "One-page spec covering users, 28 schemes, refusal policy and scoring rules", [("Spec", "capstone/SPEC.md")]),
        ("Evaluation set of 60–100 realistic queries with gold answers", "79 queries: scheme lists, single-scheme questions, multi-turn chats, unclear users, off-topic and safety tests; 7 in Hindi", [("Eval set", "eval/eval_set.csv"), ("Guide", "docs/EVALUATION.md")]),
        ("Eval set frozen and baseline recorded", "Set frozen and 82% baseline recorded before any evaluation-driven fix", [("Baseline", "eval/results/baseline.md")]),
    ]),
    ("II. Prompt-engineering baseline", [
        ("Single-agent, single-prompt attempt", "Whole scheme catalogue in one prompt, no tools", [("Script", "eval/prompt_baseline.py")]),
        ("At least 3 prompting strategies compared", "Zero-shot 73%, few-shot 72%, chain-of-thought 65%, decomposition 76%; agent system 91%", [("Results", "eval/results/prompting.md")]),
        ("How the small model breaks, documented", "Wrong reply language, age and income rule errors, guessing instead of asking, chain-of-thought hurts, 2× the tokens", [("Write-up", "docs/EVALUATION.md#7-prompting-baseline-one-prompt-vs-the-agent-system")]),
    ]),
    ("III. RAG over a real corpus", [
        ("Corpus of real documents", "33 official scheme PDFs: 995 pages, 1,884 searchable passages (87 PDFs collected)", [("RAG guide", "docs/RAG_AND_EMBEDDINGS.md")]),
        ("Chunking experiments", "150, 300 and 500-word chunks compared on recall; 300 words is best", [("Results", "eval/results/chunking.md"), ("Script", "eval/chunk_experiment.py")]),
        ("Hybrid retrieval (BM25 + dense)", "Keyword and embedding search merged with reciprocal-rank fusion", [("Code", "backend/app/retrieval.py")]),
        ("Reranker", "Cross-encoder re-orders the top 12 passages", [("Search test", "eval/retrieval_eval.py")]),
        ("Citation-grounded answers", "Answers cite [S1]–[S4], each linked to the source PDF and page", [("How it works", "docs/HOW_IT_WORKS_SIMPLIFIED.md")]),
        ("Retrieval recall@k measured separately", "Recall@4 and @10 in every evaluation run, plus a search-only test", [("Results", "eval/results/latest.md")]),
    ]),
    ("IV. Agentic layer", [
        ("At least 3 tools", "4 tools: eligibility rules, document search, document checklist, official links", [("Agent code", "backend/app/agents.py")]),
        ("Planner → executor → critic loop", "LangGraph workflow; a rule-based critic sends answers back when they break a rule", [("Guide", "docs/HOW_IT_WORKS_SIMPLIFIED.md")]),
        ("Persistent state across turns", "Profile, questions already asked and last schemes shown are kept per session", [("Backend", "backend/app/main.py")]),
        ("Error handling: tool failures, bad JSON, loops, token caps", "Safe tool failures, AI-down fallbacks, schema-checked JSON with retries, 10-step cap, token limits; 17 automated tests", [("Tests", "backend/tests/test_robustness.py"), ("Schema", "backend/app/schemas.py")]),
    ]),
    ("V. Evaluation and observability", [
        ("Accuracy, completion, tool calls, cost and latency per query", "91% accuracy, 100% completion, 8.4 tool calls, ~2,000 tokens, 5.5 s typical reply", [("Results", "eval/results/latest.md")]),
        ("Failure taxonomy", "Each failure labelled retrieval miss, reasoning, tool error or hallucination; final run: 7 reasoning errors only", [("Eval guide", "docs/EVALUATION.md")]),
        ("Tracing (LangSmith)", "Trace on every reply, plus a LangSmith project with recorded runs", [("Screenshots", "capstone/screenshots/README.md"), ("Trace code", "backend/app/trace.py")]),
    ]),
    ("VI. Ship it", [
        ("React front-end", "Voice input, Hindi, scheme cards and tap-to-answer follow-ups", [("Live app", APP), ("Code", "frontend/src/App.jsx")]),
        ("Containerised", "Backend in Docker on Render", [("Dockerfile", "backend/Dockerfile"), ("Render config", "render.yaml")]),
        ("Rate limiting and caching", "15 messages a minute per user; repeated questions served from cache with no AI call", [("Responsible AI §7", "docs/RESPONSIBLE_AI.md#7-serving-guardrails")]),
        ("Prompt-injection tests against the corpus", "14 attacks including poisoned documents in the index: 13 blocked", [("Results", "eval/results/injection.md"), ("Script", "eval/injection_test.py")]),
        ("PII handling and refusals", "Never asks for or stores Aadhaar, bank or phone numbers; off-topic requests declined", [("Responsible AI", "docs/RESPONSIBLE_AI.md")]),
        ("Human-in-the-loop boundary", "The bot informs; citizens, CSC operators and departments decide and act", [("Responsible AI §6", "docs/RESPONSIBLE_AI.md#6-human-in-the-loop-boundary")]),
    ]),
    ("Deliverables", [
        ("Git repository with the full agent stack", "Merged on main and deployed", [("Repository", REPO), ("Capstone folder", TREE + "capstone")]),
        ("Trace dashboard with real executions", "LangSmith screenshots of real requests", [("Screenshots", "capstone/screenshots/README.md")]),
        ("Evaluation report with failure taxonomy", "Evaluation guide plus result files for every experiment", [("Eval guide", "docs/EVALUATION.md"), ("Results", TREE + "eval/results")]),
        ("Technical report", "PDF report with architecture, experiments and limitations", [("PDF", "capstone/report/JanSahayak_Report.pdf")]),
        ("Live demo", "10-minute demo script and a 5-minute recorded backup", [("Script", "capstone/README.md#10-minute-demo-script"), ("Video", "capstone/demo/JanSahayak_demo.mp4")]),
    ]),
]

CSS = """
@page { size: A4; }
* { box-sizing: border-box; }
body { font-family: "Segoe UI", Calibri, Arial, sans-serif; font-size: 9.6pt; line-height: 1.4; color: #1b1b1b; margin: 0; }
a { color: #1f4e9c; text-decoration: none; }
.head { border-bottom: 2px solid #17365d; padding-bottom: 8px; margin-bottom: 10px; }
.eyebrow { font-size: 8pt; letter-spacing: .08em; text-transform: uppercase; color: #666; }
h1 { font-size: 18pt; margin: 2px 0 4px; color: #17365d; }
h2 { font-size: 12pt; margin: 14px 0 6px; color: #17365d; break-after: avoid; }
.lede { margin: 0; color: #444; }
table { border-collapse: collapse; width: 100%; }
th, td { border: 1px solid #c9d3e0; padding: 4px 6px; text-align: left; vertical-align: top; }
th { background: #eef2f7; font-size: 8.5pt; }
tr { break-inside: avoid; }
tr.part td { background: #e6ecf8; font-weight: 700; color: #17365d; }
.quick td:first-child { font-weight: 600; white-space: nowrap; }
.url { font-family: Consolas, monospace; font-size: 7.8pt; color: #1f4e9c; word-break: break-all; }
.ev a { display: inline-block; margin-right: 8px; white-space: nowrap; }
.stats { display: grid; grid-template-columns: repeat(3, 1fr); gap: 6px; }
.stat { border: 1px solid #c9d3e0; border-radius: 6px; padding: 6px 8px; }
.stat b { font-size: 14pt; color: #17365d; display: block; line-height: 1.1; }
.stat .k { font-weight: 600; } .stat .d { font-size: 8pt; color: #555; }
.note { font-size: 8.2pt; color: #555; margin-top: 8px; }
"""


def build_html():
    quick = "".join(f'<tr><td>{n}</td><td><a href="{u}">{d}</a><div class="url"><a href="{u}">{u}</a></div></td></tr>'
                    for n, u, d in QUICK)
    stats = "".join(f'<div class="stat"><b>{v}</b><div class="k">{k}</div><div class="d">{d}</div></div>'
                    for v, k, d in RESULTS)
    rows = ""
    for part, items in BRIEF:
        rows += f'<tr class="part"><td colspan="3">{part}</td></tr>'
        for ask, built, ev in items:
            rows += f'<tr><td>{ask}</td><td>{built}</td><td class="ev">{"".join(link(l, p) for l, p in ev)}</td></tr>'
    return f"""<!doctype html><html lang="en"><head><meta charset="utf-8"><title>JanSahayak: Links and Evidence</title>
<style>{CSS}</style></head><body>
<div class="head"><div class="eyebrow">IIT Kharagpur · GenAI and Agentic AI Capstone · Track B</div>
<h1>JanSahayak: links and evidence</h1>
<p class="lede">A Hindi and English assistant that helps farmers, students and small-business owners find government
schemes they may qualify for, with answers cited to official documents. This page lists where everything is and maps
each requirement of the Track B brief to its evidence. Every blue item is a link.</p></div>
<h2>Quick links</h2><table class="quick">{quick}</table>
<h2>Key results</h2><div class="stats">{stats}</div>
<h2>Track B brief: what we built and where to find it</h2>
<table><thead><tr><th style="width:30%">The brief asks for</th><th>What we built</th><th style="width:22%">Evidence</th></tr></thead>
<tbody>{rows}</tbody></table>
<p class="note">All file links open the main branch of the repository. The backend runs on a free server that sleeps when
idle; open the health link a minute before using the live app.</p>
</body></html>"""


def main():
    page = HERE / "links.html"
    page.write_text(build_html(), encoding="utf-8")
    from playwright.sync_api import sync_playwright
    out = HERE / "JanSahayak_Links.pdf"
    with sync_playwright() as p:
        try:
            browser = p.chromium.launch(channel="msedge")
        except Exception:  # noqa: BLE001
            browser = p.chromium.launch()
        pg = browser.new_page()
        pg.goto(page.as_uri())
        pg.pdf(path=str(out), format="A4", print_background=True,
               margin={"top": "12mm", "bottom": "14mm", "left": "13mm", "right": "13mm"},
               display_header_footer=True, header_template="<span></span>",
               footer_template='<div style="font-size:7pt;color:#888;width:100%;text-align:center;">'
                               'JanSahayak · Links and evidence · <span class="pageNumber"></span> / <span class="totalPages"></span></div>')
        browser.close()
    page.unlink()
    from pypdf import PdfReader
    print(f"{out.name}: {len(PdfReader(out).pages)} pages")


if __name__ == "__main__":
    sys.exit(main())
