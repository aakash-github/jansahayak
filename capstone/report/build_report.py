"""Build the technical report: REPORT.md -> report.html -> JanSahayak_Report.pdf (A4).

Edit REPORT.md (it also reads fine on GitHub), then run from the repo root:
    backend/.venv/Scripts/pip install markdown==3.7 playwright     # once
    backend/.venv/Scripts/python capstone/report/build_report.py

Uses headless Microsoft Edge (or Chromium) to render the diagram and print the PDF.
Prints the page count at the end: the brief asks for 12 pages.
"""
import html
import re
import sys
from pathlib import Path

import markdown

HERE = Path(__file__).resolve().parent
MERMAID = "https://cdn.jsdelivr.net/npm/mermaid@10.9.1/dist/mermaid.min.js"

CSS = """
@page { size: A4; margin: 14mm 15mm 14mm 15mm; }
* { box-sizing: border-box; }
body { font-family: "Segoe UI", Calibri, Arial, sans-serif; font-size: 10.4pt; line-height: 1.45; color: #1b1b1b; margin: 0; }
h1 { font-size: 17pt; margin: 0 0 6px; line-height: 1.2; }
h2 { font-size: 13pt; margin: 16px 0 5px; color: #17365d; border-bottom: 1px solid #c9d3e0; padding-bottom: 2px; break-after: avoid; }
h3 { font-size: 10.6pt; margin: 8px 0 3px; break-after: avoid; }
p { margin: 4px 0 6px; text-align: justify; }
ul, ol { margin: 3px 0 6px; padding-left: 18px; }
li { margin: 1px 0; }
table { border-collapse: collapse; width: 100%; margin: 5px 0 8px; font-size: 9pt; break-inside: avoid; }
th, td { border: 1px solid #c9d3e0; padding: 2.5px 5px; text-align: left; vertical-align: top; }
th { background: #eef2f7; }
code { font-family: Consolas, monospace; font-size: 8.3pt; background: #f3f4f6; padding: 0 2px; border-radius: 2px; }
pre { background: #f6f7f9; border: 1px solid #e1e4e8; padding: 6px 8px; font-size: 7.9pt; line-height: 1.35; white-space: pre-wrap; break-inside: avoid; }
pre code { background: none; padding: 0; font-size: inherit; }
figure { margin: 6px 0 8px; text-align: center; break-inside: avoid; }
figure img { max-width: 100%; border: 1px solid #d0d7de; }
figure.half img { max-height: 85mm; }
figure.third img { max-height: 80mm; }
figure.wide img { width: 88%; }
figure.chart img { width: 82%; border: none; }
figcaption { font-size: 8.2pt; color: #555; margin-top: 3px; font-style: italic; }
.mermaid { display: flex; justify-content: center; }
.mermaid svg { max-width: 100%; height: auto; }
.title { text-align: center; border-bottom: 2px solid #17365d; padding-bottom: 8px; margin-bottom: 6px; }
.title p { text-align: center; margin: 2px 0; }
"""


def build_html() -> str:
    src = (HERE / "REPORT.md").read_text(encoding="utf-8")
    body = markdown.markdown(src, extensions=["tables", "fenced_code", "md_in_html", "sane_lists"])
    # ```mermaid blocks -> <div class="mermaid"> so mermaid.js draws them
    body = re.sub(r'<pre><code class="language-mermaid">(.*?)</code></pre>',
                  lambda m: f'<div class="mermaid">{html.unescape(m.group(1))}</div>', body, flags=re.S)
    return f"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<title>JanSahayak Technical Report</title><style>{CSS}</style>
<script src="{MERMAID}"></script>
<script>mermaid.initialize({{startOnLoad: false, theme: "base", themeVariables: {{fontSize: "15px", primaryColor: "#eef2f7", primaryBorderColor: "#5b7bb5", lineColor: "#5b7bb5", xyChart: {{plotColorPalette: "#2f5597"}}}}, flowchart: {{htmlLabels: true, nodeSpacing: 22, rankSpacing: 34}}, xyChart: {{width: 720, height: 250}}}});
window.addEventListener("load", async () => {{ await mermaid.run(); document.body.dataset.ready = "1"; }});</script>
</head><body>{body}</body></html>"""


def main():
    page = HERE / "report.html"
    page.write_text(build_html(), encoding="utf-8")
    from playwright.sync_api import sync_playwright
    out = HERE / "JanSahayak_Report.pdf"
    with sync_playwright() as p:
        try:
            browser = p.chromium.launch(channel="msedge")
        except Exception:  # noqa: BLE001
            browser = p.chromium.launch()
        pg = browser.new_page()
        pg.goto(page.as_uri())
        pg.wait_for_selector("body[data-ready='1']", timeout=30000)
        pg.pdf(path=str(out), format="A4", print_background=True,
               margin={"top": "14mm", "bottom": "14mm", "left": "15mm", "right": "15mm"},
               display_header_footer=True, header_template="<span></span>",
               footer_template='<div style="font-size:7pt;color:#888;width:100%;text-align:center;">'
                               'JanSahayak · Track B · <span class="pageNumber"></span> / <span class="totalPages"></span></div>')
        browser.close()
    from pypdf import PdfReader
    print(f"{out.name}: {len(PdfReader(out).pages)} pages")


if __name__ == "__main__":
    sys.exit(main())
