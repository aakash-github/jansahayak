"""Draw the report's two bar charts as SVG (no plotting library needed).

Run from the repo root:  backend/.venv/Scripts/python capstone/report/make_charts.py
Numbers come from eval/results/prompting.md and docs/EVALUATION.md (section 6).
"""
from pathlib import Path

OUT = Path(__file__).resolve().parent / "img"
INK, MUTED, GRID, BASE = "#0b0b0b", "#52514e", "#e4e3df", "#b9b8b2"
ACCENT, OTHER = "#2a78d6", "#a7b6c9"   # highlighted bar / other bars


def bar_chart(name: str, labels: list[str], values: list[float], highlight: set[int], y_min: int, y_max: int,
              note: str = ""):
    W, H, left, right, top, bottom = 720, 270, 44, 16, 18, 46
    pw, ph = W - left - right, H - top - bottom
    band = pw / len(values)
    bw = min(56, band * 0.42)
    y = lambda v: top + ph * (1 - (v - y_min) / (y_max - y_min))
    s = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" '
         f'font-family="Segoe UI, Arial, sans-serif">', f'<rect width="{W}" height="{H}" fill="#ffffff"/>']
    step = 25 if y_max - y_min > 60 else 10
    for t in range(y_min, y_max + 1, step):  # recessive grid + tick labels
        s.append(f'<line x1="{left}" x2="{W - right}" y1="{y(t):.1f}" y2="{y(t):.1f}" stroke="{GRID}" stroke-width="1"/>')
        s.append(f'<text x="{left - 8}" y="{y(t) + 4:.1f}" font-size="12" fill="{MUTED}" text-anchor="end">{t}%</text>')
    for i, (lab, v) in enumerate(zip(labels, values)):
        cx = left + band * (i + 0.5)
        x0, x1, yt, yb, r = cx - bw / 2, cx + bw / 2, y(v), y(y_min), 4
        fill = ACCENT if i in highlight else OTHER
        # rounded data end (top), square at the baseline
        s.append(f'<path d="M{x0:.1f},{yb:.1f} V{yt + r:.1f} Q{x0:.1f},{yt:.1f} {x0 + r:.1f},{yt:.1f} '
                 f'H{x1 - r:.1f} Q{x1:.1f},{yt:.1f} {x1:.1f},{yt + r:.1f} V{yb:.1f} Z" fill="{fill}"/>')
        weight = "700" if i in highlight else "600"
        s.append(f'<text x="{cx:.1f}" y="{yt - 7:.1f}" font-size="15" font-weight="{weight}" fill="{INK}" text-anchor="middle">{v:g}%</text>')
        s.append(f'<text x="{cx:.1f}" y="{H - bottom + 20:.1f}" font-size="13" fill="{INK}" text-anchor="middle">{lab}</text>')
    s.append(f'<line x1="{left}" x2="{W - right}" y1="{y(y_min):.1f}" y2="{y(y_min):.1f}" stroke="{BASE}" stroke-width="1.5"/>')
    if note:
        s.append(f'<text x="{W - right}" y="{H - 6}" font-size="11" fill="{MUTED}" text-anchor="end">{note}</text>')
    s.append("</svg>")
    (OUT / name).write_text("\n".join(s), encoding="utf-8")
    print("wrote", name)


if __name__ == "__main__":
    OUT.mkdir(exist_ok=True)
    bar_chart("chart_prompting.svg", ["Zero-shot", "Few-shot", "Chain-of-thought", "Decomposition", "Agent system"],
              [73, 72, 65, 76, 91], {4}, 0, 100, "Single prompt with the whole catalogue vs agent system")
    bar_chart("chart_runs.svg", ["Baseline", "Eval-driven fixes", "Full-schema decoding (rejected)", "Final"],
              [82, 90, 85, 91], {3}, 50, 100, "Axis starts at 50%")
