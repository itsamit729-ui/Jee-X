"""Build a review page for a person: every flagged question plus a random sample of verified ones.

Writes data/review/review-<date>.html (maths rendered with KaTeX; open it in a browser). Checking the
sample by hand is how you measure the pipeline's real error rate. Questions already put on an
earlier review page are not sampled again.

Usage:
  python pipeline/review.py
  python pipeline/review.py --sample-percent 10
"""

import argparse
import html
import json
import random
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import CONFIG, load_questions, path, question_text  # noqa: E402

PAGE = """<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Solution review</title>
<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/katex@0.16.11/dist/katex.min.css">
<script defer src="https://cdn.jsdelivr.net/npm/katex@0.16.11/dist/katex.min.js"></script>
<script defer src="https://cdn.jsdelivr.net/npm/katex@0.16.11/dist/contrib/auto-render.min.js"
 onload="renderMathInElement(document.body,{{delimiters:[{{left:'$$',right:'$$',display:true}},{{left:'$',right:'$',display:false}}],throwOnError:false}})"></script>
<style>body{{font-family:system-ui,sans-serif;max-width:900px;margin:24px auto;padding:0 16px;line-height:1.5;color:#1d2230}}
h1{{font-size:22px}} .card{{border:1px solid #dde1ea;border-radius:10px;padding:16px;margin:18px 0}}
.flag{{border-left:5px solid #d9534f}} .ok{{border-left:5px solid #2e9d6a}} .meta{{color:#5b6475;font-size:13px}}
pre{{white-space:pre-wrap;font-family:inherit;margin:6px 0}} .sol{{background:#f6f8fb;border-radius:8px;padding:10px}}
img{{max-width:100%;max-height:320px}} .issues li{{color:#a33}}</style></head><body>
<h1>Solution review: {title}</h1><p class="meta">{summary}</p>{cards}</body></html>"""


def card(r, q, kind):
    parts = [f'<div class="card {"flag" if kind == "flag" else "ok"}">',
             f'<div class="meta"><b>{html.escape(r["ref"])}</b> · {html.escape(r["subject"])} · {html.escape(r["chapter"])}'
             f' · {html.escape(r["type"])} · key <b>{html.escape(str(r["answer_key"]))}</b> · verdict '
             f'<b>{html.escape(r["verdict"])}</b></div>']
    if q:
        parts.append(f"<pre>{html.escape(question_text(q))}</pre>")
        if q.get("image_url"):
            url = q["image_url"] if q["image_url"].startswith("http") else CONFIG["image_base_url"] + q["image_url"]
            parts.append(f'<img src="{html.escape(url)}" alt="figure">')
    for a in r["attempts"]:
        parts.append(f'<div class="meta">Attempt {a["attempt"]}: answer {html.escape(str(a.get("final_answer")))}'
                     f' · matches key: {a.get("matches_key")}</div>')
        if a.get("solution") and (kind == "flag" or a is r["attempts"][-1]):
            parts.append(f'<pre class="sol">{html.escape(a["solution"])}</pre>')
        issues = (a.get("checker") or {}).get("issues") or []
        if issues:
            parts.append('<ul class="issues">' + "".join(f"<li>{html.escape(i)}</li>" for i in issues) + "</ul>")
    parts.append("</div>")
    return "\n".join(parts)


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--sample-percent", type=float, default=CONFIG["review_sample_percent"])
    args = parser.parse_args()
    pack = {q["ref"]: q for q in load_questions()}
    results = [json.loads(f.read_text(encoding="utf-8")) for f in sorted(path("results_dir").glob("*.json"))]
    review_dir = path("review_dir")
    seen_file = review_dir / "sampled.json"
    seen = set(json.loads(seen_file.read_text(encoding="utf-8"))) if seen_file.exists() else set()

    flagged = [r for r in results if r["verdict"] != "verified" and r["ref"] not in seen]
    verified = [r for r in results if r["verdict"] == "verified" and r["ref"] not in seen]
    k = max(1, round(len(verified) * args.sample_percent / 100)) if verified else 0
    sample = random.sample(verified, k) if k else []
    if not flagged and not sample:
        print("Nothing new to review.")
        return
    stamp = datetime.now().strftime("%Y-%m-%d-%H%M")
    cards = [card(r, pack.get(r["ref"]), "flag") for r in flagged] + [card(r, pack.get(r["ref"]), "ok") for r in sample]
    summary = (f"{len(flagged)} flagged (need a decision: fix the key, fix/write the solution, or drop) · "
               f"{len(sample)} random verified solutions ({args.sample_percent}% sample) to spot-check")
    out = review_dir / f"review-{stamp}.html"
    out.write_text(PAGE.format(title=stamp, summary=summary, cards="\n".join(cards)), encoding="utf-8")
    seen_file.write_text(json.dumps(sorted(seen | {r["ref"] for r in flagged + sample})), encoding="utf-8")
    print(f"{summary}\nOpen {out}")


if __name__ == "__main__":
    main()
