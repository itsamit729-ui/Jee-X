"""Scrape MHT-CET (PCM) previous-year questions (question, options, answer key, figure) from
ExamSIDE's chapter-wise PYQ pages into Jee Edge question files.

Output has the same shape as scrape_pyqs.py (docs/database-schema.md section 15), in its own root:
generated/scraped-mht-cet/<subject>/<chapter-slug>.json, with `exam` = "mht_cet". ExamSIDE's
chapters are folded into ours where we have the chapter (SLUGS), so both exams share one syllabus;
each chapter written here is marked `in_mht_cet`. Import the files with
backend/scripts/import_scraped_pyqs.py generated/scraped-mht-cet (after backend/scripts/add_mht_cet.py).

How the site is read: ExamSIDE is a SvelteKit app, and every page has a JSON twin at
<page>/__data.json. A chapter's twin lists its questions (newest paper first); a question's twin
carries that question and the next three of the chapter in full: paper, year, options, correct
option, topic, difficulty. So a chapter costs about one request per four questions.

Formulas: the site renders MathJax on the server, so the text holds SVG instead of LaTeX. The SVG
keeps MathJax's MathML structure (data-mml-node) and each glyph's code point (data-c), and
`math_to_tex` rebuilds LaTeX from that. The only raw LaTeX the site exposes is a ~240 character
excerpt of each question; every rebuilt question is compared with it and the ones that differ are
listed in <out>/.reports/<subject>/<chapter-slug>.json (`math_check`) for a person to look at.

What is NOT taken: the site's written solutions. The explanation is dropped before a page is
cached; `solution` is left empty for the solution pipeline to fill.

Questions that can't be imported as they are (image options, more than one figure, a table, no
key, a formula that could not be rebuilt) are kept in <out>/.pending/<subject>/<chapter-slug>.json
with their figure URLs. <out>/.sources/... records where each question came from (ExamSIDE id and
URL, paper, question number within the paper's subject, ExamSIDE's topic and difficulty).

--dataset YEAR then writes datasets/mht-cet-<year>/ in the format of
solution-pipeline/pipeline/export_dataset.py (questions.jsonl, pipeline-pack.jsonl, pending.jsonl,
summary.json), from the files alone: no database is needed.

Usage:
  python scripts/scrape_mhtcet.py --list
  python scripts/scrape_mhtcet.py --chapter alternating-current --limit 12
  python scripts/scrape_mhtcet.py --all --min-year 2026            # every chapter, 2026 papers only
  python scripts/scrape_mhtcet.py --all --min-year 2026 --offline  # re-parse the cache, no network
  python scripts/scrape_mhtcet.py --all                            # everything (2019 onwards)
  python scripts/scrape_mhtcet.py --dataset 2026

Requires: pip install requests beautifulsoup4
"""

import argparse
import difflib
import gzip
import hashlib
import json
import re
import sys
import time
import unicodedata
from collections import Counter, defaultdict
from pathlib import Path

import requests
from bs4 import BeautifulSoup, NavigableString, Tag

ROOT = Path(__file__).resolve().parent.parent
BASE = "https://questions.examside.com"
EXAM_PATH = "/past-years/jee/mht-cet"
QUESTION_PATH = "/past-years/jee/question"
PAPER_PATH = "/past-years/year-wise/jee/mht-cet"
EXAM_VALUE = "mht_cet"
EXAM_NAME = "MHT CET"
OUT = ROOT / "generated" / "scraped-mht-cet"
IMAGE_ROOT = ROOT / "frontend" / "public" / "question-images" / "mht-cet"
EXISTING_CHAPTERS = [ROOT / "generated" / "questions", ROOT / "generated" / "scraped"]

USER_AGENT = "Mozilla/5.0 (compatible; JeeEdgePYQScraper/0.1)"
DEFAULT_DELAY = 1.5
IMAGE_DELAY = 0.5
RETRIES = 3

SUBJECTS = {  # ExamSIDE subject key -> (our subject code, output folder, name)
    "physics": ("PHY", "physics", "Physics"),
    "chemistry": ("CHEM", "chemistry", "Chemistry"),
    "mathematics": ("MATH", "mathematics", "Mathematics"),
}
# ExamSIDE chapter -> our chapter slug. Chapters not listed keep their ExamSIDE slug: the same slug as
# ours, or a chapter we don't have yet (NEW_CHAPTER_CLASS). Several ExamSIDE chapters fold into one of ours.
SLUGS = {
    "physics": {
        "units-and-measurement-and-dimensions": "units-dimensions",
        "motion": "kinematics",
        "work-energy-and-power": "work-energy-power",
        "center-of-mass": "centre-of-mass-and-collision",
        "simple-harmonic-motion": "oscillations",
        "elasticity": "mechanical-properties-solids",
        "heat-and-thermodynamics": "thermodynamics",
        "capacitor": "capacitance",
        "moving-charges-and-magnetism": "moving-charges-magnetism",
        "magnetism-and-matter": "magnetism-matter",
        "dual-nature-of-radiation": "dual-nature",
        "semiconductor-devices-and-logic-gates": "semiconductors",
    },
    "chemistry": {
        "states-of-matter": "states-of-matter-gaseous-and-liquid-states",
        "thermodynamics": "chemical-thermodynamics",
        "ionic-equilibrum": "ionic-equilibrium",
        "liquid-solution": "solutions",
        "nuclear-chemistry": "chemical-kinetics",
        "periodic-table-and-periodicity": "classification-of-elements",
        "chemical-bonding-and-molecular-structure": "chemical-bonding",
        "s-block-elements": "s-block",
        "d-and-f-block-elements": "d-f-block",
        "iupac-nomenclature": "goc",
        "general-organic-chemistry": "goc",
        "isomerism": "goc",
        "haloalkanes-and-haloarenes": "haloalkanes-haloarenes",
        "alcohol-phenols-and-ethers": "alcohols-phenols-and-ethers",
        "aldehyde-and-ketone": "aldehydes-ketones-acids",
        "carboxylic-acids-and-its-derivatives": "aldehydes-ketones-acids",
        "compounds-containing-nitrogen": "amines",
        "chemistry-in-everyday-life": "chemistry-everyday-life",
    },
    "mathematics": {
        "sets-and-relations": "sets-relations-functions",
        "functions": "sets-relations-functions",
        "sequences-and-series": "sequences-series",
        "permutations-and-combinations": "permutations-combinations",
        "vector-algebra": "vectors",
        "three-dimensional-geometry": "three-d-geometry",
        "matrices-and-determinants": "matrices-determinants",
        "trigonometric-ratios-and-identities": "trigonometry",
        "trigonometric-equations": "trigonometry",
        "properties-of-triangles": "trigonometry",
        "differentiation": "continuity-differentiability",
        "limits-continuity-and-differentiability": "continuity-differentiability",
        "definite-integration": "definite-integrals",
        "area-under-the-curves": "area-under-curves",
        "indefinite-integration": "indefinite-integrals",
        "parabola": "conic-sections",
        "ellipse": "conic-sections",
        "hyperbola": "conic-sections",
        "circle": "circles",
        "straight-lines-and-pair-of-straight-lines": "straight-lines",
    },
}
# Class of the chapters we don't have yet (ExamSIDE doesn't give one).
NEW_CHAPTER_CLASS = {
    ("physics", "communication-systems"): "12",
    ("chemistry", "surface-chemistry"): "12",
    ("chemistry", "hydrogen-and-its-compounds"): "11",
    ("mathematics", "linear-programming"): "12",
}
TYPES = {"mcq": "single_correct", "mcqm": "multi_correct", "integer": "numerical"}
SITE_DIFFICULTY = {"easy": 3, "medium": 5, "hard": 7}
DEFAULT_DIFFICULTY = 5
DEFAULT_TIME = {"single_correct": 120, "multi_correct": 180, "numerical": 180}
DEFAULT_SUBTOPIC = {"slug": "general", "name": "General", "position": 99}

# "MHT CET 2026 20th May Morning Shift" -> 2026, "20 May 2026, Shift 1"
PAPER_RE = re.compile(r"((?:19|20)\d{2})\s+(\d{1,2})(?:st|nd|rd|th)?\s+([A-Za-z]{3})[a-z]*\s+(morning|evening)", re.I)
YEAR_RE = re.compile(r"\b(?:19|20)\d{2}\b")


# ---------------------------------------------------------------- fetching

session = requests.Session()
session.headers["User-Agent"] = USER_AGENT
_last_request = 0.0


def fetch(url: str, delay: float, binary=False):
    global _last_request
    for attempt in range(1, RETRIES + 1):
        wait = _last_request + delay - time.monotonic()
        if wait > 0:
            time.sleep(wait)
        _last_request = time.monotonic()
        try:
            res = session.get(url, timeout=60)
            if res.status_code == 200:
                return res.content if binary else res.text
            if res.status_code == 404:
                return None
            print(f"  HTTP {res.status_code} for {url} (attempt {attempt})")
        except requests.RequestException as e:
            print(f"  {e.__class__.__name__} for {url} (attempt {attempt})")
        time.sleep(delay * 2 ** attempt)
    return None


def unflatten(data: list):
    """SvelteKit sends page data flattened (devalue): every value is an index into one list."""
    cache = {}

    def value(i):
        if i < 0:
            return None  # undefined / hole / NaN and friends: not used by these pages
        if i in cache:
            return cache[i]
        v = data[i]
        if isinstance(v, dict):
            cache[i] = out = {}
            for k, x in v.items():
                out[k] = value(x)
        elif isinstance(v, list) and v and isinstance(v[0], str):  # ["Date", iso], ["Set", i, ...], ...
            cache[i] = out = v[1] if v[0] in ("Date", "BigInt") else [value(x) for x in v[1:] if isinstance(x, int)]
        elif isinstance(v, list):
            cache[i] = out = []
            out.extend(value(x) for x in v)
        else:
            cache[i] = out = v
        return out

    return value(0)


def page_data(path: str, delay: float):
    """The page's own data from <page>/__data.json (the site-wide navigation node is skipped)."""
    text = fetch(f"{BASE}{path}/__data.json?x-sveltekit-invalidated=01", delay)
    if not text:
        return None
    try:
        nodes = json.loads(text).get("nodes") or []
    except json.JSONDecodeError:
        return None
    for node in reversed(nodes):
        if node and node.get("type") == "data":
            return unflatten(node["data"])
    return None


def read_cache(path: Path):
    if not path.exists():
        return None
    with gzip.open(path, "rt", encoding="utf-8") as f:
        return json.load(f)


def write_cache(path: Path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    with gzip.open(path, "wt", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False)


def exam_listing(args) -> dict:
    """{(subject key, chapter slug): {'title', 'position', 'total'}}"""
    cache = args.cache / "listing.json.gz"
    exam = read_cache(cache) if args.offline else None
    if exam is None:
        if args.offline:
            sys.exit("No cached chapter listing; run once without --offline.")
        exam = page_data(EXAM_PATH, args.delay)
        if not exam or not exam.get("subjects"):
            sys.exit("Could not load the ExamSIDE chapter listing.")
        exam = {"subjects": [{"key": s["key"], "chapters": [
            {"key": c["key"], "title": c["title"], "order": c.get("order") or 0,
             "total": ((c.get("pyq") or {}).get("count") or {}).get("total", 0)} for c in s["chapters"]]}
            for s in exam["subjects"]]}
        write_cache(cache, exam)
    chapters = {}
    for s in exam["subjects"]:
        if s["key"] in SUBJECTS:
            for c in s["chapters"]:
                chapters[(s["key"], c["key"])] = {"title": c["title"], "position": c["order"], "total": c["total"]}
    return chapters


def chapter_listing(subject: str, slug: str, args) -> list[dict]:
    """The chapter's questions in the site's order (newest paper first): [{'permalink', 'paper'}]."""
    cache = args.cache / subject / slug / "_listing.json.gz"
    listing = read_cache(cache) if args.offline else None
    if listing is None and not args.offline:
        data = page_data(f"{EXAM_PATH}/{subject}/{slug}", args.delay)
        if data:
            listing = [{"permalink": q["permalink"], "paper": q.get("paperTitle") or ""}
                       for group in data.get("questions") or [] for q in group.get("questions") or []]
            write_cache(cache, listing)
    return listing or []


def question_window(subject: str, slug: str, permalink: str, args):
    """The questions a question page carries (that one and the next three of the chapter)."""
    cache = args.cache / subject / slug / f"{permalink.rsplit('-', 1)[-1]}.json.gz"
    window = read_cache(cache)
    if window is None and not args.offline:
        data = page_data(f"{QUESTION_PATH}/{permalink}", args.delay)
        if data and data.get("questions"):
            window = data["questions"]
            for q in window:  # the site's solutions are not ours to keep
                for lang in (q.get("question") or {}).values():
                    if isinstance(lang, dict):
                        lang.pop("explanation", None)
            write_cache(cache, window)
    return window


def paper_numbers(paper_id: str, args) -> dict:
    """{ExamSIDE question id: question number within its subject} for one paper."""
    cache = args.cache / "papers" / f"{paper_id}.json.gz"
    numbers = read_cache(cache)
    if numbers is None and not args.offline:
        data = page_data(f"{PAPER_PATH}/{paper_id}", args.delay)
        if data and data.get("questions"):
            numbers = {q["question_id"]: n for group in data["questions"]
                       for n, q in enumerate(group.get("questions") or [], 1)}
            write_cache(cache, numbers)
    return numbers or {}


# ---------------------------------------------------------------- MathJax SVG -> LaTeX

GREEK = {
    0x3B1: "alpha", 0x3B2: "beta", 0x3B3: "gamma", 0x3B4: "delta", 0x3B5: "varepsilon", 0x3B6: "zeta",
    0x3B7: "eta", 0x3B8: "theta", 0x3B9: "iota", 0x3BA: "kappa", 0x3BB: "lambda", 0x3BC: "mu", 0x3BD: "nu",
    0x3BE: "xi", 0x3C0: "pi", 0x3C1: "rho", 0x3C2: "varsigma", 0x3C3: "sigma", 0x3C4: "tau", 0x3C5: "upsilon",
    0x3C6: "varphi", 0x3C7: "chi", 0x3C8: "psi", 0x3C9: "omega", 0x3D1: "vartheta", 0x3D5: "phi", 0x3D6: "varpi",
    0x3F0: "varkappa", 0x3F1: "varrho", 0x3F5: "epsilon", 0x393: "Gamma", 0x394: "Delta", 0x398: "Theta",
    0x39B: "Lambda", 0x39E: "Xi", 0x3A0: "Pi", 0x3A3: "Sigma", 0x3A5: "Upsilon", 0x3A6: "Phi", 0x3A8: "Psi",
    0x3A9: "Omega", 0xB5: "mu", 0x2126: "Omega", 0x2206: "Delta",
}
SYMBOLS = {
    0x2212: "-", 0xD7: r"\times", 0xF7: r"\div", 0xB1: r"\pm", 0x2213: r"\mp", 0x22C5: r"\cdot", 0xB7: r"\cdot",
    0x2217: "*", 0x2218: r"\circ", 0x2219: r"\bullet", 0x2022: r"\bullet", 0xB0: r"^{\circ}",
    0x2264: r"\le", 0x2265: r"\ge", 0x2260: r"\ne", 0x2248: r"\approx", 0x2261: r"\equiv", 0x223C: r"\sim",
    0x2243: r"\simeq", 0x2245: r"\cong", 0x221D: r"\propto", 0x226A: r"\ll", 0x226B: r"\gg", 0x2A7D: r"\leqslant",
    0x2A7E: r"\geqslant", 0x2250: r"\doteq", 0x226E: r"\nless", 0x226F: r"\ngtr", 0x2272: r"\lesssim",
    0x2273: r"\gtrsim", 0x2192: r"\rightarrow", 0x2190: r"\leftarrow", 0x2194: r"\leftrightarrow",
    0x21D2: r"\Rightarrow", 0x21D0: r"\Leftarrow", 0x21D4: r"\Leftrightarrow", 0x21CC: r"\rightleftharpoons",
    0x21CB: r"\leftrightharpoons", 0x2191: r"\uparrow", 0x2193: r"\downarrow", 0x27F6: r"\longrightarrow",
    0x27F5: r"\longleftarrow", 0x27F9: r"\Longrightarrow", 0x27FA: r"\iff", 0x27F7: r"\longleftrightarrow",
    0x21A6: r"\mapsto", 0x21C4: r"\rightleftarrows", 0x21C6: r"\leftrightarrows", 0x2197: r"\nearrow",
    0x2198: r"\searrow", 0x21BC: r"\leftharpoonup", 0x21C0: r"\rightharpoonup", 0x21D1: r"\Uparrow",
    0x21D3: r"\Downarrow", 0x2195: r"\updownarrow",
    0x221E: r"\infty", 0x2202: r"\partial", 0x2207: r"\nabla", 0x222B: r"\int", 0x222C: r"\iint",
    0x222D: r"\iiint", 0x222E: r"\oint", 0x2211: r"\sum", 0x220F: r"\prod", 0x2210: r"\coprod", 0x221A: r"\surd",
    0x2208: r"\in", 0x2209: r"\notin", 0x220B: r"\ni", 0x2282: r"\subset", 0x2283: r"\supset",
    0x2286: r"\subseteq", 0x2287: r"\supseteq", 0x222A: r"\cup", 0x2229: r"\cap", 0x2205: r"\emptyset",
    0x2216: r"\setminus", 0x22C3: r"\bigcup", 0x22C2: r"\bigcap", 0x2200: r"\forall", 0x2203: r"\exists",
    0xAC: r"\neg", 0x2227: r"\wedge", 0x2228: r"\vee", 0x22C0: r"\bigwedge", 0x22C1: r"\bigvee",
    0x2234: r"\therefore", 0x2235: r"\because", 0x2220: r"\angle", 0x22A5: r"\perp", 0x27C2: r"\perp", 0x25FB: r"\square", 0x2225: r"\parallel",
    0x2226: r"\nparallel", 0x25B3: r"\triangle", 0x25B5: r"\triangle", 0x25A1: r"\square", 0x22A2: r"\vdash",
    0x2026: r"\ldots", 0x22EF: r"\cdots", 0x22EE: r"\vdots", 0x22F1: r"\ddots", 0x2032: "'", 0x2033: "''",
    0x210F: r"\hbar", 0x2113: r"\ell", 0x211C: r"\Re", 0x2111: r"\Im", 0x2135: r"\aleph", 0x2127: r"\mho",
    0x212B: r"\mathring{A}", 0xC5: r"\mathring{A}", 0x27E8: r"\langle", 0x27E9: r"\rangle", 0x2329: r"\langle",
    0x232A: r"\rangle", 0x2308: r"\lceil", 0x2309: r"\rceil", 0x230A: r"\lfloor", 0x230B: r"\rfloor",
    0x2016: r"\|", 0x2223: "|", 0x2295: r"\oplus", 0x2297: r"\otimes", 0x2299: r"\odot", 0x2296: r"\ominus",
    0x2020: r"\dagger", 0x22C6: r"\star", 0x2605: r"\star", 0x2713: r"\checkmark", 0x22A4: r"\top",
    0xA0: "~", 0x2009: r"\,", 0x200A: r"\,", 0x2005: r"\,", 0x2004: r"\:", 0x2002: r"\enspace", 0x2003: r"\quad",
    0x2010: "-", 0x2011: "-", 0x2013: "-", 0x2014: "-", 0x2015: "-", 0x2044: "/", 0x2215: "/", 0x2236: ":",
    0xA3: r"\pounds", 0x2018: "`", 0x2019: "'", 0x201C: "``", 0x201D: "''",
    ord("%"): r"\%", ord("#"): r"\#", ord("&"): r"\&", ord("$"): r"\$", ord("_"): r"\_", ord("{"): r"\{",
    ord("}"): r"\}", ord("\\"): r"\backslash", ord("~"): r"\sim", ord("^"): r"\wedge",
}
INVISIBLE = {0x2061, 0x2062, 0x2063, 0x2064, 0x200B, 0x200C, 0x200D, 0xFEFF}
DELIMITER_PARTS = {  # pieces MathJax assembles tall delimiters from
    **dict.fromkeys((0x239B, 0x239C, 0x239D), "("), **dict.fromkeys((0x239E, 0x239F, 0x23A0), ")"),
    **dict.fromkeys((0x23A1, 0x23A2, 0x23A3), "["), **dict.fromkeys((0x23A4, 0x23A5, 0x23A6), "]"),
    **dict.fromkeys((0x23A7, 0x23A8, 0x23A9), r"\{"), **dict.fromkeys((0x23AB, 0x23AC, 0x23AD), r"\}"),
    0x23D0: "|",
}
DELIMITERS = {"(", ")", "[", "]", r"\{", r"\}", "|", r"\|", r"\langle", r"\rangle", r"\lceil", r"\rceil",
              r"\lfloor", r"\rfloor", "/", r"\backslash", r"\uparrow", r"\downarrow", r"\updownarrow"}
ARROWS = {r"\rightarrow": r"\xrightarrow", r"\longrightarrow": r"\xrightarrow", r"\leftarrow": r"\xleftarrow",
          r"\longleftarrow": r"\xleftarrow", r"\leftrightarrow": r"\xleftrightarrow",
          r"\longleftrightarrow": r"\xleftrightarrow", r"\rightleftharpoons": r"\xrightleftharpoons",
          r"\leftrightharpoons": r"\xleftrightharpoons", r"\Rightarrow": r"\xRightarrow",
          r"\Leftarrow": r"\xLeftarrow", r"\Leftrightarrow": r"\xLeftrightarrow", "=": r"\xlongequal"}
FUNCTIONS = {"sin", "cos", "tan", "cot", "sec", "csc", "sinh", "cosh", "tanh", "coth", "arcsin", "arccos",
             "arctan", "log", "ln", "lg", "exp", "lim", "max", "min", "sup", "inf", "det", "gcd", "arg", "deg",
             "dim", "ker", "Pr", "limsup", "liminf", "hom"}
LIMITS = {r"\sum", r"\prod", r"\coprod", r"\int", r"\iint", r"\iiint", r"\oint", r"\bigcup", r"\bigcap",
          r"\bigwedge", r"\bigvee", r"\lim", r"\max", r"\min", r"\sup", r"\inf", r"\limsup", r"\liminf", r"\det",
          r"\gcd", r"\Pr"}
OVER = {0x20D7: r"\vec", 0x2192: r"\overrightarrow", 0x2190: r"\overleftarrow", 0x2194: r"\overleftrightarrow",
        0x5E: r"\hat", 0x302: r"\hat", 0x2C6: r"\hat", 0xAF: r"\bar", 0x2C9: r"\bar", 0x203E: r"\bar",
        0x2015: r"\bar", 0x2013: r"\bar", 0x2212: r"\bar", 0x5F: r"\bar", 0x2500: r"\bar", 0x2D9: r"\dot",
        0xA8: r"\ddot", 0x7E: r"\tilde", 0x2DC: r"\tilde", 0x223C: r"\tilde", 0x23DE: r"\overbrace",
        0x2C7: r"\check", 0x2D8: r"\breve", 0xB4: r"\acute", 0x60: r"\grave", 0x2DA: r"\mathring"}
UNDER = {0x5F: r"\underline", 0x2015: r"\underline", 0xAF: r"\underline", 0x2212: r"\underline",
         0x2013: r"\underline", 0x2500: r"\underline", 0x23DF: r"\underbrace"}
STYLE_COMMAND = {"bold": r"\mathbf", "bolditalic": r"\boldsymbol", "bb": r"\mathbb", "cal": r"\mathcal",
                 "frak": r"\mathfrak", "sans": r"\mathsf", "mono": r"\mathtt"}
TEXT_ESCAPES = {"%": r"\%", "#": r"\#", "&": r"\&", "$": r"\$", "_": r"\_", "{": r"\{", "}": r"\}",
                "\\": r"\textbackslash ", "~": r"\textasciitilde ", "^": r"\textasciicircum "}
GLYPH_FONT = re.compile(r"TEX-([A-Z0-9]+)-[0-9A-Fa-f]+$")
TRANSLATE = re.compile(r"translate\(\s*(-?[\d.]+)(?:[\s,]+(-?[\d.]+))?\s*\)")
SIMPLE_BASE = re.compile(r"[^\\{}\s]|\d+(?:\.\d+)?|\\[A-Za-z]+|\\[A-Za-z]+\{[^{}]*\}|'+")


class MathProblem(Exception):
    """A formula has a node this converter does not know: the question goes to pending."""


def own(node: Tag, names: set) -> list:
    """Elements that belong to this MathML node itself: its nearest child nodes ("mml"), or its own
    glyphs/rules, never those of a child node."""
    found = []
    stack = [c for c in reversed(node.contents) if isinstance(c, Tag)]
    while stack:
        el = stack.pop()
        if el.has_attr("data-mml-node"):
            if "mml" in names:
                found.append(el)
            continue
        if el.name in names:
            found.append(el)
        stack.extend(c for c in reversed(el.contents) if isinstance(c, Tag))
    return found


def kids(node: Tag) -> list:
    return own(node, {"mml"})


def position(node: Tag) -> tuple[float, float]:
    x = y = 0.0
    for m in TRANSLATE.finditer(node.get("transform", "")):
        x += float(m.group(1))
        y += float(m.group(2) or 0)
    return x, y


def glyphs(node: Tag) -> list[tuple[str, str]]:
    """(character, style) for every glyph of a token node. Style: "", italic, normal, bold, ..."""
    out = []
    for el in own(node, {"use", "text"}):
        if el.name == "text":
            out += [(ch, "text") for ch in el.get_text()]
            continue
        try:
            ch = chr(int(el.get("data-c", ""), 16))
        except ValueError:
            continue
        font = GLYPH_FONT.search(el.get("xlink:href") or el.get("href") or "")
        font = font.group(1) if font else ""
        name = unicodedata.name(ch, "")
        style = {"B": "bold", "BI": "bolditalic", "I": "italic", "N": "normal", "C": "cal"}.get(font, "")
        if name.startswith("MATHEMATICAL") or "DOUBLE-STRUCK" in name or "BLACK-LETTER" in name \
                or name.startswith("SCRIPT ") or name == "PLANCK CONSTANT":
            style = ("bolditalic" if "BOLD ITALIC" in name else "bold" if "BOLD" in name and "FRAKTUR" not in name
                     else "bb" if "DOUBLE-STRUCK" in name else "cal" if "SCRIPT" in name
                     else "frak" if "FRAKTUR" in name or "BLACK-LETTER" in name
                     else "sans" if "SANS-SERIF" in name else "mono" if "MONOSPACE" in name else "italic")
            ch = unicodedata.normalize("NFKC", ch)
        out.append((ch, style))
    return out


def symbol(ch: str, unknown: Counter) -> str:
    cp = ord(ch)
    if cp in INVISIBLE:
        return ""
    if cp in SYMBOLS:
        return SYMBOLS[cp]
    if cp in GREEK:
        return "\\" + GREEK[cp]
    if cp >= 128:
        unknown[ch] += 1
    return ch


def cat(parts) -> str:
    """Concatenate LaTeX pieces, with a space only where a command name would run into a letter."""
    out = ""
    for p in parts:
        if not p:
            continue
        if out and p[0].isalnum() and re.search(r"\\[A-Za-z]+$", out):
            out += " "
        out += p
    return out


def group(tex: str) -> str:
    return tex if len(tex) == 1 and tex.isalnum() else "{" + tex + "}"


def base_group(tex: str) -> str:
    return tex if SIMPLE_BASE.fullmatch(tex) else "{" + tex + "}"


def scripted(base: str, sub: str = "", sup: str = "") -> str:
    out = base_group(base) if base else "{}"
    if sup and not sup.strip("'"):  # primes: f', f''
        out, sup = out + sup, ""
    if sub:
        out += "_" + group(sub)
    if sup:
        out += "^" + group(sup)
    return out


def token_mi(node, unknown) -> str:
    chars = [(c, s) for c, s in glyphs(node) if ord(c) not in INVISIBLE]
    if not chars:
        return ""
    text = "".join(c for c, _ in chars)
    style = chars[0][1]
    if len(text) > 1 and text.isascii() and text.isalpha() and text in FUNCTIONS:
        return "\\" + text
    body = cat(symbol(c, unknown) for c in text)
    if style in STYLE_COMMAND:
        command = STYLE_COMMAND[style]
        if style == "bold" and not (text.isascii() and text.isalnum()):
            command = r"\boldsymbol"
        return f"{command}{{{body}}}"
    if text.isascii() and text.isalpha() and (style in ("normal", "text") or len(text) > 1):
        return rf"\mathrm{{{text}}}"  # upright letters: units, chemical symbols, multi-letter names
    return body


def token_mo(node, unknown) -> str:
    chars = [c for c, _ in glyphs(node) if ord(c) not in INVISIBLE]
    if not chars:
        return ""
    for c in chars:
        if ord(c) in DELIMITER_PARTS:
            return DELIMITER_PARTS[ord(c)]
    if len(chars) > 1:
        if len(set(chars)) == 1 and symbol(chars[0], unknown) in DELIMITERS | {"'"}:
            return symbol(chars[0], unknown) * (len(chars) if chars[0] == "\u2032" else 1)
        for c in chars:  # a stretched arrow or rule is its head plus extension pieces
            if symbol(c, unknown) in ARROWS and c != "=":
                return symbol(c, unknown)
        text = "".join(chars)
        if text.isascii() and text.isalpha():
            return "\\" + text if text in FUNCTIONS else rf"\operatorname{{{text}}}"
        if len(set(chars)) == 1:
            return symbol(chars[0], unknown)
    return cat(symbol(c, unknown) for c in chars)


def token_mtext(node) -> str:
    text = "".join(c for c, _ in glyphs(node) if ord(c) not in INVISIBLE)
    if not text:
        return ""
    if not text.strip():
        return "~"
    return r"\text{" + "".join(TEXT_ESCAPES.get(c, " " if c == "\xa0" else c) for c in text) + "}"


def space(node, following) -> str:
    if following is None:
        return ""
    width = position(following)[0] - position(node)[0]
    if width <= 0:
        return ""
    return r"\," if width < 200 else r"\:" if width < 250 else r"\;" if width < 400 else r"\ " if width < 800 \
        else r"\quad" if width < 1500 else r"\qquad"


def row(nodes, unknown) -> str:
    parts = []
    for i, n in enumerate(nodes):
        if n["data-mml-node"] == "mspace":
            parts.append(space(n, nodes[i + 1] if i + 1 < len(nodes) else None))
        else:
            parts.append(tex(n, unknown))
    return cat(parts)


def table(node, unknown) -> list[list[str]]:
    return [[row(kids(cell), unknown) for cell in kids(line)] for line in kids(node)]


def environment(name: str, rows: list[list[str]], spec: str = "") -> str:
    body = r" \\ ".join(" & ".join(cells) for cells in rows)
    return rf"\begin{{{name}}}{spec} {body} \end{{{name}}}"


def is_delimiter(node, unknown):
    if node["data-mml-node"] != "mo":
        return None
    t = token_mo(node, unknown)
    return t if t in DELIMITERS or t == "" else None


def fenced(node, unknown):
    """An mrow made by \\left ... \\right (or \\binom, cases): LaTeX for it, or None if it is a plain row."""
    k = kids(node)
    if len(k) < 2:
        return None
    left, right = is_delimiter(k[0], unknown), is_delimiter(k[-1], unknown)
    if left is None or right is None or (left == "" and right == ""):
        return None
    inner = k[1:-1]
    if len(inner) == 1 and inner[0]["data-mml-node"] == "mfrac" and not own(inner[0], {"rect"}) \
            and (left, right) == ("(", ")"):
        top, bottom = kids(inner[0])[:2]
        return rf"\binom{{{tex(top, unknown)}}}{{{tex(bottom, unknown)}}}"
    if len(inner) == 1 and inner[0]["data-mml-node"] == "mtable":
        rows = table(inner[0], unknown)
        if (left, right) == (r"\{", ""):
            return environment("cases", rows)
        return cat([rf"\left{left or '.'}", environment("matrix", rows), rf"\right{right or '.'}"])
    return cat([rf"\left{left or '.'}", row(inner, unknown), rf"\right{right or '.'}"])


def tex(node: Tag, unknown: Counter) -> str:
    kind = node["data-mml-node"]
    if kind == "mi":
        return token_mi(node, unknown)
    if kind == "mn":
        return "".join(c for c, _ in glyphs(node))
    if kind == "mo":
        return token_mo(node, unknown)
    if kind == "mtext":
        return token_mtext(node)
    if kind == "mspace":
        return r"\,"
    k = kids(node)
    if kind == "mrow":
        return fenced(node, unknown) or row(k, unknown)
    if kind in ("math", "mstyle", "TeXAtom", "mtd", "menclose", "inferredMrow", "semantics"):
        return row(k, unknown)
    if kind == "mpadded":  # \smash, \vphantom, \rlap and the like: keep what is visible
        return "" if len(k) == 1 and k[0]["data-mml-node"] == "mphantom" else row(k, unknown)
    if kind == "mphantom":
        return rf"\phantom{{{row(k, unknown)}}}"
    if kind == "mfrac" and len(k) >= 2:
        top, bottom = tex(k[0], unknown), tex(k[1], unknown)
        return rf"\frac{{{top}}}{{{bottom}}}" if own(node, {"rect"}) else rf"{{{top} \atop {bottom}}}"
    if kind in ("msqrt", "mroot"):
        k = [n for n in k if not (n["data-mml-node"] == "mo" and any(c == "\u221a" or "\ue000" <= c <= "\uf8ff"
                                                                    for c, _ in glyphs(n)))]
        if kind == "mroot" and len(k) >= 2:
            return rf"\sqrt[{tex(k[-1], unknown)}]{{{row(k[:-1], unknown)}}}"
        return rf"\sqrt{{{row(k, unknown)}}}"
    if kind == "msub" and len(k) == 2:
        return scripted(tex(k[0], unknown), sub=tex(k[1], unknown))
    if kind == "msup" and len(k) == 2:
        return scripted(tex(k[0], unknown), sup=tex(k[1], unknown))
    if kind in ("msubsup", "munderover") and len(k) == 3:
        low, high = sorted(k[1:], key=lambda n: position(n)[1])  # the SVG lists the upper script first
        base, under, over = tex(k[0], unknown), tex(low, unknown), tex(high, unknown)
        if kind == "msubsup" or base in LIMITS:
            return scripted(base, sub=under, sup=over)
        if base in ARROWS:
            return rf"{ARROWS[base]}[{under}]{{{over}}}"
        return rf"\underset{{{under}}}{{\overset{{{over}}}{{{base}}}}}"
    if kind in ("mover", "munder") and len(k) == 2:
        base = tex(k[0], unknown)
        marks = [c for c, _ in glyphs(k[1])] if k[1]["data-mml-node"] == "mo" else []
        accent = next((a for a in ((OVER if kind == "mover" else UNDER).get(ord(c)) for c in marks) if a), None)
        if accent and base not in LIMITS and base not in ARROWS:
            if accent == r"\bar" and not SIMPLE_BASE.fullmatch(base):
                accent = r"\overline"
            return rf"{accent}{{{base}}}"
        script = tex(k[1], unknown)
        if base in LIMITS:
            return scripted(base, sub=script) if kind == "munder" else scripted(base, sup=script)
        if base in ARROWS:
            return rf"{ARROWS[base]}{{{script}}}" if kind == "mover" else rf"{ARROWS[base]}[{script}]{{}}"
        return rf"\overset{{{script}}}{{{base}}}" if kind == "mover" else rf"\underset{{{script}}}{{{base}}}"
    if kind == "mtable":
        rows = table(node, unknown)
        if max((len(r) for r in rows), default=0) <= 1:
            return environment("array", rows, "{l}")
        return environment("aligned", rows)
    raise MathProblem(kind)


def math_to_tex(container: Tag, unknown: Counter) -> str:
    root = container.find(attrs={"data-mml-node": "math"})
    if root is None:
        raise MathProblem("no math node")
    return re.sub(r"\s+", " ", tex(root, unknown)).strip()


# ---------------------------------------------------------------- HTML -> text

BLOCKS = {"p", "div", "li", "tr", "h1", "h2", "h3", "h4", "h5", "h6", "blockquote", "ul", "ol", "table"}
MATH_OPEN, MATH_CLOSE = "\x01", "\x02"


def to_text(html: str, unknown: Counter) -> tuple[str, list[str], list[str]]:
    """Plain text with $LaTeX$ for formulas and \\n for line breaks; also image URLs and problems
    (a table, a formula that could not be rebuilt)."""
    images, problems = [], []

    def render(node) -> str:
        if isinstance(node, NavigableString):
            return str(node).replace("\n", " ")
        if not isinstance(node, Tag):
            return ""
        name = node.name
        if name == "mjx-container":
            try:
                body = math_to_tex(node, unknown)
            except MathProblem as e:
                problems.append(f"formula not rebuilt ({e})")
                return " [formula] "
            if not body:
                return ""
            return f"\n$${body}$$\n" if node.get("display") == "true" else MATH_OPEN + body + MATH_CLOSE
        if name == "img":
            src = node.get("src") or node.get("data-orsrc") or ""
            if src and not src.startswith("data:"):
                images.append(src)
            return " "
        if name == "br":
            return "\n"
        if name in ("script", "style", "svg"):
            return ""
        inner = "".join(render(c) for c in node.contents)
        if name in ("sub", "sup"):
            inner = inner.replace(MATH_OPEN, "").replace(MATH_CLOSE, "").strip()
            return MATH_OPEN + ("_" if name == "sub" else "^") + "{" + inner + "}" + MATH_CLOSE if inner else ""
        if name == "table":
            problems.append("table in the text")
        if name in ("td", "th"):
            return inner.strip() + " | "
        return f"\n{inner}\n" if name in BLOCKS else inner

    text = render(BeautifulSoup(html or "", "html.parser"))
    # H<sub>2</sub>O is one formula's worth of scripts; formulas written back to back stay apart
    text = re.sub(MATH_CLOSE + MATH_OPEN + r"(?=[_^])", "", text).replace(MATH_CLOSE + MATH_OPEN, " ")
    text = text.replace(MATH_OPEN, "$").replace(MATH_CLOSE, "$")
    lines = [re.sub(r"[ \t\u00a0\u200b]+", " ", line).strip().rstrip("|").strip() for line in text.split("\n")]
    return "\n".join(line for line in lines if line), images, problems


# Spellings that mean the same thing, removed before a rebuilt formula is compared with the site's own LaTeX.
_SAME = [(r"\\[dt]?frac", r"\\frac"), (r"\\(?:left|right|displaystyle|limits|,|;|:|!|quad|qquad|enspace| )", ""),
         (r"\\(?:mathrm|text|textbf|mathbf|operatorname|rm|bf|boldsymbol|overrightarrow|vec|overline|bar)\b", ""),
         (r"\\leq\b", r"\\le"), (r"\\geq\b", r"\\ge"), (r"\\neq\b", r"\\ne"), (r"\\to\b", r"\\rightarrow"),
         (r"\\lt\b", "<"), (r"\\gt\b", ">"), (r"\\%", "%"), (r"&lt;", "<"), (r"&gt;", ">"), (r"&amp;", "&"),
         (r"&nbsp;", ""), (r"<[^>]{0,80}>", ""), (r"[\s${}~.]", "")]


def comparable(text: str) -> str:
    for pattern, replacement in _SAME:
        text = re.sub(pattern, replacement, text)
    return text


def agrees_with_excerpt(stem: str, excerpt: str):
    """Similarity (0-1) of the rebuilt stem and the site's raw-LaTeX excerpt over the excerpt's length."""
    theirs = comparable(re.sub(r"\.\.\.$", "", excerpt.strip()))
    if len(theirs) < 8:
        return None
    return difflib.SequenceMatcher(None, comparable(stem)[:len(theirs)], theirs, autojunk=False).ratio()


# ---------------------------------------------------------------- output

def parse_paper(title: str):
    m = PAPER_RE.search(title or "")
    if m:
        year, day, month, shift = m.groups()
        return int(year), f"{int(day)} {month.title()} {year}, Shift {1 if shift.lower() == 'morning' else 2}"
    y = YEAR_RE.search(title or "")
    return (int(y.group(0)) if y else None), ((title or "").strip()[:50] or None)


def make_ref(code: str, stem: str, shift) -> str:
    key = re.sub(r"\s+", " ", stem).strip().lower() + "|" + (shift or "")
    return f"PYQ-{code}-{hashlib.sha1(key.encode()).hexdigest()[:12]}"


def save_image(url: str, subject_dir: str, slug: str, ref: str, args):
    ext = Path(url.split("?")[0]).suffix.lower() or ".png"
    if ext not in {".png", ".jpg", ".jpeg", ".gif", ".webp", ".svg"}:
        ext = ".png"
    target = IMAGE_ROOT / subject_dir / slug / f"{ref}{ext}"
    if not target.exists():
        if args.offline:
            return None
        data = fetch(url, IMAGE_DELAY, binary=True)
        if not data:
            return None
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
    return "/" + target.relative_to(ROOT / "frontend" / "public").as_posix()


def chapter_header(subject: str, slug: str, info: dict, out_file: Path):
    """Our chapter as it already is (name, class, JEE flags) when we have it, else a new MHT-CET-only one."""
    subject_dir = SUBJECTS[subject][1]
    for source in (out_file, *(root / subject_dir / f"{slug}.json" for root in EXISTING_CHAPTERS)):
        if source.exists():
            data = json.loads(source.read_text(encoding="utf-8"))
            return {**data["chapter"], "in_mht_cet": True}, data.get("subtopics", [])
    return {"name": info["title"], "slug": slug, "class_level": NEW_CHAPTER_CLASS.get((subject, slug)),
            "in_main": False, "in_advanced": False, "in_mht_cet": True, "position": info["position"]}, []


def in_years(year, args) -> bool:
    if not (args.min_year or args.max_year):
        return True
    return year is not None and (args.min_year or 0) <= year <= (args.max_year or 9999)


def read_json(path: Path, default):
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else default


def write_json(path: Path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def parse_question(raw: dict, unknown: Counter):
    """Returns (question, question figure URLs, {option label: figure URLs}, pending reasons)."""
    en = (raw.get("question") or {}).get("en") or {}
    qtype = TYPES.get(raw.get("type"))
    if not qtype:
        raise ValueError(f"unknown question type {raw.get('type')!r}")
    stem, images, problems = to_text(en.get("content"), unknown)
    if not stem:
        raise ValueError("empty question text")
    question = {"type": qtype, "stem": stem}
    option_figures, pending = {}, list(dict.fromkeys(problems))
    if qtype == "numerical":
        try:
            value = float(str(en.get("answer")).replace(",", ""))
            question["answer"] = {"min": value, "max": value}
        except ValueError:
            question["answer"] = None
            pending.append(f"numerical answer {en.get('answer')!r} is not a number")
        question["options"] = []
    else:
        correct = set(en.get("correct_options") or [])
        options = []
        for i, o in enumerate(en.get("options") or []):
            label = chr(65 + i)
            text, figures, option_problems = to_text(o.get("content"), unknown)
            pending += [p for p in option_problems if p not in pending]
            if figures:
                option_figures[label] = figures
                text = f"{text} [figure]".strip()
            options.append({"label": label, "content": text, "is_correct": (o.get("identifier") or label) in correct})
        if len(options) < 2:
            raise ValueError(f"{len(options)} options")
        marked = sum(o["is_correct"] for o in options)
        if marked == 0 or (qtype == "single_correct" and marked != 1):
            pending.append(f"{marked} options marked correct")
        question["options"] = options
        if option_figures:
            pending.append(f"options {', '.join(option_figures)} are figures")
    if raw.get("isBonus"):
        pending.append("marked as a bonus question at the source")
    if len(images) > 1:
        pending.append(f"{len(images)} figures in question (only one supported)")
    return question, images, option_figures, pending


def scrape_chapter(subject: str, site_slug: str, info: dict, args) -> None:
    code, subject_dir, _ = SUBJECTS[subject]
    slug = SLUGS[subject].get(site_slug, site_slug)
    out_file = args.out / subject_dir / f"{slug}.json"
    pending_file = args.out / ".pending" / subject_dir / f"{slug}.json"
    figures_file = args.out / ".figures" / subject_dir / f"{slug}.json"
    sources_file = args.out / ".sources" / subject_dir / f"{slug}.json"
    report_file = args.out / ".reports" / subject_dir / f"{site_slug}.json"  # one per ExamSIDE chapter
    chapter, subtopics = chapter_header(subject, slug, info, out_file)
    if not any(s["slug"] == DEFAULT_SUBTOPIC["slug"] for s in subtopics):
        subtopics.append(dict(DEFAULT_SUBTOPIC))
    figure_sources = read_json(figures_file, {})
    sources = read_json(sources_file, {})
    previous = {q["ref"]: q for q in read_json(out_file, {}).get("questions", [])}
    previous_pending = {q["ref"]: q for q in read_json(pending_file, {}).get("questions", [])}

    listing = chapter_listing(subject, site_slug, args)
    wanted = [e for e in listing if in_years(parse_paper(e["paper"])[0], args)]
    if args.limit:
        wanted = wanted[:args.limit]
    print(f"{len(listing)} questions listed, {len(wanted)} selected")

    raw, flagged = {}, []
    for entry in wanted:
        if entry["permalink"] in raw:
            continue
        window = question_window(subject, site_slug, entry["permalink"], args)
        for q in window or []:
            raw.setdefault(q["permalink"], q)
        if entry["permalink"] not in raw:
            flagged.append({"source": f"{BASE}{QUESTION_PATH}/{entry['permalink']}", "reason": "page not available"})

    questions, pending, seen = {}, {}, set()
    unknown, differ, compared = Counter(), [], 0
    for entry in wanted:
        q = raw.get(entry["permalink"])
        if not q:
            continue
        source = f"{BASE}{QUESTION_PATH}/{q['permalink']}"
        paper = q.get("paperTitle") or entry["paper"]
        year, shift = parse_paper(paper)
        try:
            parsed, images, option_figures, pending_reasons = parse_question(q, unknown)
        except ValueError as e:
            flagged.append({"source": source, "reason": str(e)})
            continue
        ref = make_ref(code, parsed["stem"], shift)
        if ref in seen:
            continue
        seen.add(ref)

        excerpt = (((q.get("bookmark") or {}).get("en") or {}).get("excerpt")) or ""
        score = agrees_with_excerpt(parsed["stem"], excerpt)
        if score is not None:
            compared += 1
            if score < 0.85:
                differ.append({"ref": ref, "source": source, "similarity": round(score, 2),
                               "ours": parsed["stem"][:260], "site": excerpt})
        number = paper_numbers(q["paperId"], args).get(q.get("question_id")) if q.get("paperId") else None
        topic = q.get("topic") or DEFAULT_SUBTOPIC["slug"]
        if not any(s["slug"] == topic for s in subtopics):
            subtopics.append({"slug": topic, "name": topic.replace("-", " ").capitalize(), "position": len(subtopics)})
        sources[ref] = {"source": source, "question_id": q.get("question_id"), "paper_id": q.get("paperId"),
                        "paper_label": paper, "number_in_subject": number, "topic": q.get("topic"),
                        "difficulty": q.get("difficulty"), "marks": q.get("marks")}

        if pending_reasons:
            pending[ref] = {
                "ref": ref, "type": parsed["type"], "exam": EXAM_VALUE, "year": year, "shift": shift,
                "paper_label": paper, "source": source, "pending_reasons": pending_reasons,
                "stem": parsed["stem"], "options": parsed["options"],
                **({"answer": parsed["answer"]} if "answer" in parsed else {}),
                "figures": {"question": images, "options": option_figures},
            }
            print(f"  pend {ref} {shift or '-'}  ({'; '.join(pending_reasons)})")
            continue

        image = None
        if images:
            url = save_image(images[0], subject_dir, slug, ref, args)
            if not url:
                flagged.append({"source": source, "ref": ref, "reason": "figure could not be downloaded"})
                continue
            image = {"url": url, "alt": f"Figure for this {chapter['name']} question"}
            figure_sources[ref] = {"source_image": images[0], "source": source, "exam": EXAM_VALUE,
                                   "year": year, "shift": shift, "paper_label": paper}

        old = previous.get(ref, {})
        questions[ref] = {
            "ref": ref,
            "subtopic": old.get("subtopic", topic),
            "type": parsed["type"],
            "difficulty": old.get("difficulty", SITE_DIFFICULTY.get(q.get("difficulty"), DEFAULT_DIFFICULTY)),
            "expected_time_sec": old.get("expected_time_sec", DEFAULT_TIME[parsed["type"]]),
            "source_type": "pyq",
            "exam": EXAM_VALUE,
            "year": year,
            "shift": shift,
            "status": old.get("status", "draft"),
            "stem": parsed["stem"],
            "image": image,
            "options": parsed["options"],
            **({"answer": parsed["answer"]} if "answer" in parsed else {}),
            "solution": old.get("solution", ""),
        }

    for f in flagged:
        print(f"  flagged {f['source']}: {f['reason']}")

    # Keep questions from earlier runs that this run didn't reach (other years, an earlier run without
    # --limit), unless this run found they now belong in the other file.
    for ref, q in previous.items():
        if ref not in pending:
            questions.setdefault(ref, q)
    for ref, q in previous_pending.items():
        if ref not in questions:
            pending.setdefault(ref, q)
    order = lambda q: (q["year"] or 0, q["shift"] or "", q["ref"])  # noqa: E731
    ordered = sorted(questions.values(), key=order)
    kept = set(questions) | set(pending)

    write_json(out_file, {"subject": code, "chapter": chapter, "subtopics": subtopics, "passages": [], "questions": ordered})
    write_json(pending_file, {"subject": code, "chapter": chapter, "questions": sorted(pending.values(), key=order)})
    write_json(figures_file, {ref: figure_sources[ref] for ref in sorted(figure_sources) if ref in questions})
    write_json(sources_file, {ref: sources[ref] for ref in sorted(sources) if ref in kept})
    write_json(report_file, {"chapter": slug, "source_chapter": site_slug, "flagged": flagged,
                             "math_check": {"compared": compared, "differ": len(differ), "questions": differ},
                             "unknown_symbols": dict(unknown.most_common())})
    print(f"Wrote {len(ordered)} questions, {len(pending)} pending, {len(flagged)} unreadable; "
          f"formula check: {len(differ)} of {compared} differ from the site's excerpt"
          + (f"; unknown symbols {dict(unknown)}" if unknown else ""))


# ---------------------------------------------------------------- dataset

def build_dataset(year: int, args) -> None:
    """datasets/mht-cet-<year>/ in the format of solution-pipeline/pipeline/export_dataset.py."""
    out = ROOT / "datasets" / f"{EXAM_VALUE.replace('_', '-')}-{year}"
    full, pack, pending = [], [], []
    for _, subject_dir, subject_name in SUBJECTS.values():
        for f in sorted((args.out / subject_dir).glob("*.json")):
            data = json.loads(f.read_text(encoding="utf-8"))
            chapter = data["chapter"]
            names = {s["slug"]: s["name"] for s in data.get("subtopics", [])}
            figures = read_json(args.out / ".figures" / subject_dir / f.name, {})
            for q in data["questions"]:
                if q.get("year") != year or q.get("exam") != EXAM_VALUE:
                    continue
                numerical = q["type"] == "numerical"
                low, high = ((q.get("answer") or {}).get(k) for k in ("min", "max")) if numerical else (None, None)
                answer = (low if low == high else f"{low} to {high}") if numerical else None
                image = q.get("image")
                full.append({
                    "ref": q["ref"], "exam": q["exam"], "year": q["year"], "shift": q["shift"],
                    "subject": subject_name, "chapter": chapter["name"], "chapter_slug": chapter["slug"],
                    "class_level": chapter.get("class_level"), "subtopic": names.get(q["subtopic"], q["subtopic"]),
                    "type": q["type"], "stem": q["stem"], "options": q["options"],
                    "answer": answer if numerical else ",".join(o["label"] for o in q["options"] if o["is_correct"]),
                    "figure": {"url": image["url"], "alt": image.get("alt")} if image else None,
                    "solution": None, "solution_verified": False,
                    "difficulty": q["difficulty"], "expected_time_sec": q["expected_time_sec"],
                })
                pack.append({
                    "ref": q["ref"], "subject": subject_name, "chapter": chapter["name"], "type": q["type"],
                    "exam": q["exam"], "year": q["year"], "shift": q["shift"], "stem": q["stem"],
                    "options": [{"label": o["label"], "content": o["content"]} for o in q["options"]],
                    "correct": [o["label"] for o in q["options"] if o["is_correct"]],
                    "answer_min": low, "answer_max": high, "answer": answer,
                    # the figure is not on the live site yet, so the pack points at the source
                    "image_url": (figures.get(q["ref"]) or {}).get("source_image") if image else None,
                    "had_solution": False, "content_hash": None, "version": None,
                })
        for f in sorted((args.out / ".pending" / subject_dir).glob("*.json")):
            data = json.loads(f.read_text(encoding="utf-8"))
            for q in data.get("questions", []):
                if q.get("year") == year and q.get("exam") == EXAM_VALUE:
                    pending.append({**q, "subject": subject_name, "chapter": data["chapter"]["name"],
                                    "chapter_slug": data["chapter"]["slug"]})
    order = lambda q: (q["subject"], q.get("chapter_slug") or q["chapter"], q["shift"] or "", q["ref"])  # noqa: E731
    full.sort(key=order)
    pack.sort(key=lambda q: (q["subject"], q["chapter"], q["shift"] or "", q["ref"]))
    pending.sort(key=order)
    if not full and not pending:
        sys.exit(f"No {EXAM_NAME} {year} questions under {args.out}; scrape them first.")

    out.mkdir(parents=True, exist_ok=True)
    for name, items in (("questions.jsonl", full), ("pipeline-pack.jsonl", pack), ("pending.jsonl", pending)):
        (out / name).write_text("".join(json.dumps(i, ensure_ascii=False) + "\n" for i in items), encoding="utf-8")
    by_chapter = defaultdict(Counter)
    for q in full:
        by_chapter[q["subject"]][q["chapter"]] += 1
    summary = {
        "exam": EXAM_NAME, "year": year, "questions": len(full), "verified_solutions": 0,
        "pending_not_imported": len(pending),
        "by_subject": dict(Counter(q["subject"] for q in full)),
        "by_type": dict(Counter(q["type"] for q in full)),
        "with_figure": sum(1 for q in full if q["figure"]),
        "by_shift": dict(sorted(Counter(q["shift"] for q in full).items())),
        "by_chapter": {s: dict(sorted(c.items())) for s, c in sorted(by_chapter.items())},
    }
    write_json(out / "summary.json", summary)
    (out / "README.md").write_text(f"""# {EXAM_NAME} {year} — question dataset

{len(full)} questions from {len(summary['by_shift'])} shifts of {EXAM_NAME} {year}, scraped from ExamSIDE's chapter-wise pages
({summary['by_subject'].get('Physics', 0)} physics, {summary['by_subject'].get('Chemistry', 0)} chemistry, {summary['by_subject'].get('Mathematics', 0)} mathematics; {summary['with_figure']} with a figure).
None has a solution yet. Rebuild this folder with `python scripts/scrape_mhtcet.py --dataset {year}`.

| File | Contents |
|---|---|
| `questions.jsonl` | One question per line: `ref`, `shift`, `subject`, `chapter`, `type`, `stem` (LaTeX in `$...$`), `options` with `is_correct`, `answer`, `figure` (file in `frontend/public`), `solution` (empty) |
| `pipeline-pack.jsonl` | The same {len(pack)} questions in the solution pipeline's format (figures point at the source site) |
| `pending.jsonl` | {len(pending)} questions not usable as they are: options drawn as images, several figures, a table, or a formula that could not be rebuilt (with `pending_reasons` and the source figure URLs) |
| `summary.json` | Counts by subject, chapter, shift and type |

## Solving them

```
copy datasets\\{out.name}\\pipeline-pack.jsonl solution-pipeline\\data\\questions.jsonl
cd solution-pipeline
python pipeline/run_batch.py --limit 3
```

## Notes
- Source: questions and keys as transcribed by ExamSIDE; MHT-CET is computer based and its papers are not published, so these are the source's reconstruction and its keys are not official. The solution pipeline flags disagreements (`key_mismatch`).
- Formulas were rebuilt from the site's rendered MathJax, not copied as LaTeX. `generated/scraped-mht-cet/.reports/` lists the questions whose rebuilt text differs from the site's raw excerpt.
- These files do not publish themselves. Use Admin → Question bank → MHT-CET to preview and publish eligible records after deployment. Pending and unsupported rows stay out.
- Contains answer keys: keep the repository private before sharing it widely.
""", encoding="utf-8")
    print(f"Wrote {out}: {len(full)} questions, {len(pack)} in the pipeline pack, {len(pending)} pending")


# ---------------------------------------------------------------- main

def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--list", action="store_true", help="list the chapters")
    parser.add_argument("--chapter", action="append", default=[], help="ExamSIDE chapter slug (repeatable)")
    parser.add_argument("--all", action="store_true", help="scrape every chapter (with --subject: every chapter of it)")
    parser.add_argument("--subject", choices=sorted(SUBJECTS), help="only this subject (for --list or ambiguous slugs)")
    parser.add_argument("--limit", type=int, default=0, help="stop after this many questions per chapter")
    parser.add_argument("--delay", type=float, default=DEFAULT_DELAY, help="seconds between requests")
    parser.add_argument("--offline", action="store_true", help="only re-parse cached pages, no network")
    parser.add_argument("--min-year", type=int, help="only questions from this year on")
    parser.add_argument("--max-year", type=int, help="only questions up to this year")
    parser.add_argument("--out", type=Path, default=OUT, help="output root (default: generated/scraped-mht-cet)")
    parser.add_argument("--dataset", type=int, metavar="YEAR", help="write datasets/mht-cet-YEAR from the scraped files")
    args = parser.parse_args()
    args.out = args.out.resolve()
    args.cache = args.out / ".cache" / "examside"
    for stream in (sys.stdout, sys.stderr):
        stream.reconfigure(encoding="utf-8", errors="replace")

    if args.dataset and not (args.all or args.chapter):
        build_dataset(args.dataset, args)
        return

    chapters = exam_listing(args)
    if args.subject:
        chapters = {k: v for k, v in chapters.items() if k[0] == args.subject}

    if args.all:
        failed = []
        for (subject, slug), info in chapters.items():
            print(f"\n===== {subject} / {slug} =====", flush=True)
            try:
                scrape_chapter(subject, slug, info, args)
            except Exception as e:  # one broken chapter shouldn't stop an hours-long run
                failed.append(f"{subject}/{slug}: {e.__class__.__name__}: {e}")
                print(f"  chapter failed: {e.__class__.__name__}: {e}")
        print(f"\nDone. {len(chapters) - len(failed)} chapters written, {len(failed)} failed.")
        for f in failed:
            print(f"  {f}")
    elif args.list or not args.chapter:
        for (subject, slug), info in chapters.items():
            print(f"{subject:<12} {slug:<45} {info['total']:>4} questions  -> {SLUGS[subject].get(slug, slug)}")
        return
    else:
        for slug in args.chapter:
            matches = [(s, sl) for (s, sl) in chapters if sl == slug]
            if not matches:
                sys.exit(f"Unknown chapter slug {slug!r}. Run with --list to see them.")
            if len(matches) > 1:
                sys.exit(f"{slug!r} exists in {[m[0] for m in matches]}; pass --subject.")
            subject, _ = matches[0]
            scrape_chapter(subject, slug, chapters[(subject, slug)], args)
    if args.dataset:
        build_dataset(args.dataset, args)


if __name__ == "__main__":
    main()
