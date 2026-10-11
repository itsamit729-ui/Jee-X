"""Redraw a sample of MHT-CET question figures as our own SVGs, for review.

The scraped figures carry the source site's watermark, so they can't be shown to students. Each
figure here is drawn from scratch from what the question needs (components, values, labels), with
the scraped image only as a reference for the layout.

Writes review/figures/<ref>.svg and <ref>.png (white background, 2x for sharp text) and
review/index.html (scraped figure next to the redrawn one, with the question). The PNGs are rendered
with headless Chrome or Edge; without either, only the SVGs are written.
Run from anywhere:  python review/make_figures.py
"""

import html
import importlib
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
DATASET = ROOT / "datasets" / "mht-cet-2026" / "questions.jsonl"

PNG_SCALE = 2
BROWSERS = ["chrome", "msedge", "chromium", "google-chrome",
            r"C:\Program Files\Google\Chrome\Application\chrome.exe",
            r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
            r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
            r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
            "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"]


def load_figures() -> dict:
    """{question ref: drawing function} from every module in review/drawings."""
    sys.path.insert(0, str(HERE))
    figures = {}
    for module in sorted((HERE / "drawings").glob("*.py")):
        if module.stem != "__init__":
            figures.update(importlib.import_module(f"drawings.{module.stem}").FIGURES)
    return figures


def browser():
    for name in BROWSERS:
        found = shutil.which(name) or (name if os.path.isfile(name) else None)
        if found:
            return found
    return None


def render_png(exe: str, svg: Path, png: Path, width: int, height: int) -> bool:
    """Screenshot the SVG at its own size on a white page."""
    subprocess.run([exe, "--headless=new", "--disable-gpu", "--hide-scrollbars", "--default-background-color=FFFFFFFF",
                    f"--force-device-scale-factor={PNG_SCALE}", f"--window-size={width},{height}",
                    f"--screenshot={png}", svg.resolve().as_uri()],
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=120, check=False)
    return png.is_file()


PAGE = """<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>MHT-CET figures: scraped vs redrawn</title>
<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/katex@0.16.11/dist/katex.min.css">
<script defer src="https://cdn.jsdelivr.net/npm/katex@0.16.11/dist/katex.min.js"></script>
<script defer src="https://cdn.jsdelivr.net/npm/katex@0.16.11/dist/contrib/auto-render.min.js"
  onload="renderMathInElement(document.body,{delimiters:[{left:'$$',right:'$$',display:true},{left:'$',right:'$',display:false}]})"></script>
<style>
  body { font: 16px/1.5 system-ui, sans-serif; margin: 0 auto; max-width: 1100px; padding: 24px 16px; color: #111827; background: #f9fafb; }
  h1 { font-size: 22px; } .note { color: #4b5563; }
  article { background: #fff; border: 1px solid #e5e7eb; border-radius: 8px; padding: 16px; margin: 20px 0; }
  .meta { color: #6b7280; font-size: 13px; } .stem { white-space: pre-line; margin: 8px 0; }
  .options { color: #374151; font-size: 14px; margin: 0 0 12px; padding-left: 0; list-style: none; }
  .options .key { font-weight: 600; color: #047857; }
  .pair { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; }
  @media (max-width: 720px) { .pair { grid-template-columns: 1fr; } }
  figure { margin: 0; border: 1px solid #e5e7eb; border-radius: 6px; padding: 8px; background: #fff; }
  figure img { max-width: 100%; height: auto; display: block; margin: 0 auto; }
  figcaption { font-size: 13px; color: #6b7280; margin-bottom: 6px; }
</style></head><body>
<h1>MHT-CET 2026 figures: scraped vs redrawn</h1>
<p class="note">__COUNT__ of the 149 figures, redrawn as our own figures (PNG and SVG in <code>review/figures/</code>). For each one,
check that every component, value and label the question needs is there and correct.</p>
__ITEMS__
</body></html>
"""


def main():
    FIGURES = load_figures()
    questions = {}
    for line in DATASET.read_text(encoding="utf-8").splitlines():
        q = json.loads(line)
        if q["ref"] in FIGURES:
            questions[q["ref"]] = q
    out = HERE / "figures"
    out.mkdir(exist_ok=True)
    items, exe, pngs = [], browser(), 0
    for ref, draw in FIGURES.items():
        figure = draw()
        (out / f"{ref}.svg").write_text(figure.svg(), encoding="utf-8")
        shown = f"{ref}.svg"
        if exe and render_png(exe, out / f"{ref}.svg", out / f"{ref}.png", figure.width, figure.height):
            shown, pngs = f"{ref}.png", pngs + 1
        q = questions[ref]
        options = "".join(f'<li class="{"key" if o["is_correct"] else ""}">({o["label"]}) {html.escape(o["content"])}</li>'
                          for o in q["options"])
        items.append(
            f'<article><div class="meta">{ref} &middot; {html.escape(q["subject"])} &middot; {html.escape(q["chapter"])} '
            f'&middot; {html.escape(q["shift"])}</div>'
            f'<div class="stem">{html.escape(q["stem"])}</div><ul class="options">{options}</ul>'
            f'<div class="pair"><figure><figcaption>Scraped (watermarked)</figcaption>'
            f'<img src="../frontend/public{q["figure"]["url"]}" alt="scraped figure"></figure>'
            f'<figure><figcaption>Redrawn: {html.escape(draw.__doc__.strip())}</figcaption>'
            f'<img src="figures/{shown}" alt="redrawn figure"></figure></div></article>')
    (HERE / "index.html").write_text(PAGE.replace("__COUNT__", str(len(items))).replace("__ITEMS__", "\n".join(items)),
                                     encoding="utf-8")
    print(f"Wrote {len(items)} SVGs and {pngs} PNGs to {out}, and {HERE / 'index.html'}")
    if not exe:
        print("No Chrome or Edge found: PNGs were not rendered.")


if __name__ == "__main__":
    main()
