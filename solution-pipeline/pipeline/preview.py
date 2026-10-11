"""Preview solved questions the way a student sees them: question, figure, options (correct one
highlighted) and the worked solution with rendered maths.

Writes data/review/preview-<date>.html; open it in a browser.

Usage:
  python pipeline/preview.py                  # every verified result
  python pipeline/preview.py --refs PYQ-CHEM-...
  python pipeline/preview.py --all            # flagged ones too
"""

import argparse
import html
import json
import re
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import CONFIG, load_questions, path  # noqa: E402

PAGE = """<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Solution preview</title>
<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/katex@0.16.11/dist/katex.min.css">
<script defer src="https://cdn.jsdelivr.net/npm/katex@0.16.11/dist/katex.min.js"></script>
<script defer src="https://cdn.jsdelivr.net/npm/katex@0.16.11/dist/contrib/auto-render.min.js"
 onload="renderMathInElement(document.body,{{delimiters:[{{left:'$$',right:'$$',display:true}},{{left:'$',right:'$',display:false}}],throwOnError:false}})"></script>
<style>
body{{font-family:'DM Sans',system-ui,sans-serif;background:#f4f6fb;margin:0;color:#1d2230}}
.wrap{{max-width:820px;margin:0 auto;padding:24px 16px}}
h1{{font-size:20px;margin:0 0 4px}} .sub{{color:#5b6475;font-size:13px;margin-bottom:18px}}
.q{{background:#fff;border:1px solid #e1e5ee;border-radius:14px;padding:20px 22px;margin:18px 0;box-shadow:0 1px 2px rgba(20,30,60,.04)}}
.meta{{display:flex;gap:8px;flex-wrap:wrap;font-size:12px;color:#5b6475;margin-bottom:12px}}
.pill{{background:#eef1f8;border-radius:999px;padding:3px 10px}} .pill.flag{{background:#fdeaea;color:#a33}}
.stem{{font-size:15.5px;line-height:1.6;white-space:pre-wrap}} img{{max-width:100%;max-height:300px;display:block;margin:12px 0;border-radius:8px}}
.opt{{border:1px solid #e1e5ee;border-radius:10px;padding:9px 12px;margin:7px 0;font-size:15px}}
.opt.right{{border-color:#2e9d6a;background:#e9f7ef}} .opt b{{margin-right:8px}}
.ans{{margin:12px 0;font-size:15px}} .ans span{{background:#e9f7ef;border:1px solid #2e9d6a;border-radius:8px;padding:3px 10px}}
.sol{{margin-top:14px;border-top:1px dashed #d5dae5;padding-top:12px}} .sol h3{{font-size:13px;letter-spacing:.4px;color:#4f46e5;margin:0 0 8px;text-transform:uppercase}}
.step{{font-size:15px;line-height:1.65;margin:4px 0}}
</style></head><body><div class="wrap"><h1>Solution preview</h1><div class="sub">{summary}</div>{cards}</div></body></html>"""


def card(r, q):
    flag = r["verdict"] != "verified"
    parts = ['<div class="q">', '<div class="meta">',
             f'<span class="pill">{html.escape(q["subject"])} · {html.escape(q["chapter"])}</span>',
             f'<span class="pill">{html.escape(q.get("shift") or "")}</span>',
             f'<span class="pill">{html.escape(q["type"].replace("_", " "))}</span>',
             f'<span class="pill{" flag" if flag else ""}">{html.escape(r["verdict"])}</span>',
             f'<span class="pill">{html.escape(r["ref"])}</span></div>',
             f'<div class="stem">{html.escape(q["stem"])}</div>']
    if q.get("image_url"):
        url = q["image_url"] if q["image_url"].startswith("http") else CONFIG["image_base_url"] + q["image_url"]
        parts.append(f'<img src="{html.escape(url)}" alt="figure">')
    if q["type"] == "numerical":
        parts.append(f'<div class="ans">Answer: <span>{html.escape(str(q["answer"]))}</span></div>')
    else:
        for o in q["options"]:
            right = o["label"] in q["correct"]
            parts.append(f'<div class="opt{" right" if right else ""}"><b>{o["label"]}</b>{html.escape(o["content"])}</div>')
    solution = r.get("solution") or (r["attempts"][-1].get("solution") if r["attempts"] else None)
    if solution:
        title = "Solution" if not flag else "Last attempt (not published)"
        steps = "".join(f'<div class="step">{html.escape(line)}</div>' for line in solution.splitlines() if line.strip())
        parts.append(f'<div class="sol"><h3>{title}</h3>{steps}</div>')
    parts.append("</div>")
    return "\n".join(parts)


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--refs", nargs="*")
    parser.add_argument("--all", action="store_true", help="include flagged questions")
    args = parser.parse_args()
    pack = {q["ref"]: q for q in load_questions()}
    results = [json.loads(f.read_text(encoding="utf-8")) for f in sorted(path("results_dir").glob("*.json"))]
    results = [r for r in results if (not args.refs or r["ref"] in args.refs)
               and (args.all or args.refs or r["verdict"] == "verified") and r["ref"] in pack]
    if not results:
        print("Nothing to preview.")
        return
    out = path("review_dir") / f"preview-{datetime.now().strftime('%Y-%m-%d-%H%M')}.html"
    summary = f"{len(results)} questions · rendered with KaTeX like the app"
    out.write_text(PAGE.format(summary=summary, cards="\n".join(card(r, pack[r["ref"]]) for r in results)),
                   encoding="utf-8")
    print(f"Open {out}")


if __name__ == "__main__":
    main()
