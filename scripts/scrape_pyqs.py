"""Scrape JEE Main and JEE Advanced previous-year questions (question, options, answer key, figure)
from ExamsNet's chapter-wise PYQ pages into Jee Edge question files.

Output follows docs/database-schema.md section 15, the same shape backend/app/importer.py reads:
<out>/<subject>/<chapter-slug>.json. It is written to a separate root (generated/scraped for Main,
generated/scraped-advanced for Advanced) so the Gemini-generated files in generated/questions are
left alone until reviewed.

What is taken from each page:
  - the question text, with every KaTeX formula turned back into its $LaTeX$ source
  - the options, and which one is correct (from the page's schema.org JSON-LD)
  - the numerical answer for integer-type questions
  - exam date and shift (e.g. "[28-Jun-2022-Shift-2]" -> year 2022, "28 Jun 2022, Shift 2")
  - the question figure, downloaded into frontend/public/question-images/pyq/...

What is NOT taken: the site's written solutions. Only the part of the page up to the solution
block is cached, and the explanation is dropped from the JSON-LD before caching. `solution` is
left empty for our own solution-generation step to fill.

Every imported question with a figure is listed in <out>/.figures/<subject>/<chapter-slug>.json with
its original figure URL and paper; ExamsNet's figure file names carry the paper and question number
(e.g. jee_mains_28_jun_2022_s1_54.png), which the figure step uses to find the official question.

Questions that can't be imported as they are yet (image options, more than one figure, numerical
answer missing/0/unparseable) are kept in full in <out>/.pending/<subject>/<chapter-slug>.json, with
the figure URLs, for the later figure step (official-paper crops via Gemini) and answer check to
complete. Pages that can't be parsed at all are listed in <out>/.reports/<chapter-slug>.json. The
importer skips dot-directories, so pending questions and reports are never imported.

Re-running merges into the existing output: fields we fill in later (solution, subtopic, difficulty,
expected_time_sec, status) are kept for questions already in the file.

Usage:
  python scripts/scrape_pyqs.py --list
  python scripts/scrape_pyqs.py --chapter alternating-current
  python scripts/scrape_pyqs.py --chapter alternating-current --limit 10
  python scripts/scrape_pyqs.py --chapter alternating-current --offline   # re-parse cache only
  python scripts/scrape_pyqs.py --all                     # every JEE Main chapter
  python scripts/scrape_pyqs.py --all --min-year 2019     # JEE Main 2019 onwards
  python scripts/scrape_pyqs.py --all --min-year 2026 --recent-only   # just 2026, fast
  python scripts/scrape_pyqs.py --exam advanced --all     # every JEE Advanced chapter

Requires: pip install requests beautifulsoup4
"""

import argparse
import hashlib
import json
import re
import sys
import time
from pathlib import Path

import requests
from bs4 import BeautifulSoup, NavigableString

ROOT = Path(__file__).resolve().parent.parent
BASE = "https://www.examsnet.com"
EXAMS = {
    "main": {
        "exam": "jee_main",
        "listing": f"{BASE}/exams/jee-mains-chapterwise-previous-year-questions-online",
        "prefix": "jee-main",
        "listing_cache": "listing.txt",
        "out": ROOT / "generated" / "scraped",
    },
    "advanced": {
        "exam": "jee_advanced",
        "listing": f"{BASE}/exams/jee-advanced-chapterwise-previous-year-questions",
        "prefix": "jee-advanced",
        "listing_cache": "listing-advanced.txt",
        "out": ROOT / "generated" / "scraped-advanced",
    },
}
CACHE_DIR = ROOT / "generated" / "scraped" / ".cache" / "examsnet"
IMAGE_ROOT = ROOT / "frontend" / "public" / "question-images" / "pyq"
EXISTING_QUESTIONS = ROOT / "generated" / "questions"

USER_AGENT = "Mozilla/5.0 (compatible; JeeEdgePYQScraper/0.1)"
DEFAULT_DELAY = 1.5
RETRIES = 3

SUBJECTS = {  # ExamsNet URL subject -> (our subject code, output folder)
    "physics": ("PHY", "physics"),
    "chemistry": ("CHEM", "chemistry"),
    "math": ("MATH", "mathematics"),
}

# ExamsNet chapter name -> our chapter slug, for both Main and Advanced names. Names not listed keep
# their ExamsNet slug and become new chapters. Several ExamsNet chapters fold into one of ours
# (e.g. ellipse/parabola/hyperbola).
SLUGS = {
    "physics": {
        # Advanced
        "motion": "kinematics",
        "capacitors": "capacitance",
        "dual-nature-of-radiation": "dual-nature",
        "geometrical-optics": "ray-optics",
        "magnetism": "moving-charges-magnetism",
        "simple-harmonic-motion": "oscillations",
        "work-power--energy": "work-energy-power",
        "impulse--momentum": "centre-of-mass-and-collision",
        "heat-and-thermodynamics": "thermodynamics",
        # Main
        "units-and-measurements": "units-dimensions",
        "motion-in-a-straight-line": "kinematics",
        "motion-in-a-plane": "kinematics",
        "work-power-and-energy": "work-energy-power",
        "dual-nature-of-matter-and-radiation": "dual-nature",
        "electrostatic-potential-and-capacitance": "capacitance",
        "magnetic-effects-of-current-and-magnetism": "moving-charges-magnetism",
        "magnetism-and-matter": "magnetism-matter",
        "ray-optics-and-optical-instruments": "ray-optics",
        "semiconductor-electronics": "semiconductors",
    },
    "chemistry": {
        # Advanced
        "basics-of-organic-chemistry": "goc",
        "chemical-bonding--molecular-structure": "chemical-bonding",
        "thermodynamics": "chemical-thermodynamics",
        "chemical-kinetics-and-nuclear-chemistry": "chemical-kinetics",
        "isolation-of-elements": "metallurgy",
        "chemistry-in-everyday-life": "chemistry-everyday-life",
        "periodic-table--periodicity": "classification-of-elements",
        "gaseous-state": "states-of-matter-gaseous-and-liquid-states",
        "compounds-containing-nitrogen": "amines",
        # Main
        "chemical-bonding-and-molecular-structure": "chemical-bonding",
        "organic-chemistry-–-some-basic-principles": "goc",
        "structure-of-atom": "atomic-structure",
        "aldehydes-ketones-and-carboxylic-acids": "aldehydes-ketones-acids",
        "d-and-f-block-elements": "d-f-block",
        "electro-chemistry": "electrochemistry",
        "haloalkanes-and-haloarenes": "haloalkanes-haloarenes",
    },
    "math": {
        # Advanced
        "circle": "circles",
        "mathematical-induction-and-binomial-theorem": "binomial-theorem",
        "trigonometric-functions--equations": "trigonometry",
        "application-of-integration": "area-under-curves",
        "definite-integration": "definite-integrals",
        # Main (and Advanced where the names match)
        "ellipse": "conic-sections",
        "parabola": "conic-sections",
        "hyperbola": "conic-sections",
        "functions": "sets-relations-functions",
        "sets-and-relations": "sets-relations-functions",
        "permutations-and-combinations": "permutations-combinations",
        "quadratic-equation-and-inequalities": "quadratic-equations",
        "sequences-and-series": "sequences-series",
        "straight-lines-and-pair-of-straight-lines": "straight-lines",
        "trigonometric-ratios-and-identities": "trigonometry",
        "area-under-the-curves": "area-under-curves",
        "limits-continuity-and-differentiability": "continuity-differentiability",
        "differentiation": "continuity-differentiability",
        "matrices-and-determinants": "matrices-determinants",
        "three-dimensional-geometry": "three-d-geometry",
        "vector-algebra": "vectors",
    },
}

# Filled in until our own tagging/solution step sets real values.
DEFAULT_DIFFICULTY = 5
DEFAULT_TIME = {"single_correct": 120, "multi_correct": 180, "numerical": 180}
DEFAULT_SUBTOPIC = {"slug": "general", "name": "General", "position": 99}

# "JEE Adv 2025 P2" -> year 2025, "2025 Paper 2"
ADV_PAPER_RE = re.compile(r"\b((?:19|20)\d{2})\s*[- ]?\s*P(?:aper)?\s*[- ]?\s*(\d)\b", re.I)
# "28-Jun-2022-Shift-2", "15-Apr-2023 shift 1", "JEE Main 5 Apr 2026 Shift 1", "Main 8 April 2018"
DATE_RE = re.compile(r"(\d{1,2})[\s-]+([A-Za-z]{3})[a-z]*[\s-]+(\d{4})(?:[\s-]+shift[\s-]*(\d))?", re.I)
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
            res = session.get(url, timeout=30)
            if res.status_code == 200:
                return res.content if binary else res.text
            if res.status_code == 404:
                return None
            print(f"  HTTP {res.status_code} for {url} (attempt {attempt})")
        except requests.RequestException as e:
            print(f"  {e.__class__.__name__} for {url} (attempt {attempt})")
        time.sleep(delay * 2 ** attempt)
    return None


def discover_chapters(exam: dict, delay: float, offline: bool) -> dict:
    """{(subject, our_slug): {'class_level', 'examsnet_names', 'parts': [test paths]}}"""
    prefix = exam["prefix"]
    cache = CACHE_DIR / exam["listing_cache"]
    if offline and cache.exists():
        paths = cache.read_text(encoding="utf-8").split()
    else:
        html = fetch(exam["listing"], delay)
        if not html:
            sys.exit("Could not load the ExamsNet chapter listing.")
        paths = sorted(set(re.findall(rf'href="(/test/{prefix}-[^"/]+)"', html)))
        cache.parent.mkdir(parents=True, exist_ok=True)
        cache.write_text("\n".join(paths), encoding="utf-8")
    test_re = re.compile(rf"^/test/{prefix}-(physics|chemistry|math)-class-(11|12)-(.+?)(?:-part-(\d+))?-questions$")
    chapters = {}
    for path in paths:
        m = test_re.match(path)
        if not m:
            continue
        subject, class_level, name, _ = m.groups()
        slug = SLUGS[subject].get(name, name)
        entry = chapters.setdefault((subject, slug), {"class_level": class_level, "examsnet_names": set(), "parts": []})
        entry["examsnet_names"].add(name)
        entry["parts"].append(path)
    return chapters


def page_cache_dir(part_path: str) -> Path:
    return CACHE_DIR / part_path.strip("/").replace("/", "_")


def question_count(part_path: str, delay: float, offline: bool) -> int:
    if offline:
        return max((int(p.stem) for p in page_cache_dir(part_path).glob("*.html")), default=0)
    html = fetch(BASE + part_path, delay) or ""
    numbers = [int(n) for n in re.findall(re.escape(part_path) + r"/(\d+)", html)]
    return max(numbers, default=0)


def trimmed_page(part_path: str, n: int, delay: float, offline: bool):
    """The question area of one page plus its JSON-LD, without the solution. Cached on disk."""
    cache = page_cache_dir(part_path) / f"{n}.html"
    if cache.exists():
        return cache.read_text(encoding="utf-8")
    if offline:
        return None
    html = fetch(f"{BASE}{part_path}/{n}", delay)
    if not html:
        return None
    # Keep the question and the options list; everything after the list (the solution) is dropped.
    start, answers = html.find('id="mquestion"'), html.find('id="answers"')
    end = html.find("</ul>", answers)
    if start < 0 or answers < 0 or end < 0:
        return None
    fragment = "<div " + html[start:end + len("</ul>")] + "</div>"
    ld = []
    for raw in re.findall(r'<script[^>]*application/ld\+json[^>]*>(.*?)</script>', html, re.S):
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            continue
        if isinstance(data, dict) and data.get("@type") == "LearningResource":
            for part in data.get("hasPart", []):
                part.get("acceptedAnswer", {}).pop("answerExplanation", None)
            ld.append(data)
    page = fragment + '\n<script type="application/ld+json">' + json.dumps(ld, ensure_ascii=False) + "</script>"
    cache.parent.mkdir(parents=True, exist_ok=True)
    cache.write_text(page, encoding="utf-8")
    return page


# ---------------------------------------------------------------- parsing

def to_text(node) -> tuple[str, list[str]]:
    """Plain text with $LaTeX$ for formulas and \\n for line breaks; also returns image URLs."""
    images = []
    for img in node.find_all("img"):
        if img.get("src") and not img["src"].startswith("data:"):
            images.append(img["src"])
        img.replace_with(NavigableString(" "))
    for display in node.select("span.katex-display"):
        ann = display.find("annotation", encoding="application/x-tex")
        display.replace_with(NavigableString(f"\n$${' '.join(ann.get_text().split())}$$\n" if ann else ""))
    for math in node.select("span.katex"):
        ann = math.find("annotation", encoding="application/x-tex")
        math.replace_with(NavigableString(f"${' '.join(ann.get_text().split())}$" if ann else ""))
    for br in node.select("br, div.custom-break"):
        br.replace_with(NavigableString("\n"))
    text = node.get_text()
    lines = [re.sub(r"[ \t ​]+", " ", line).strip() for line in text.split("\n")]
    text = "\n".join(line for line in lines if line)
    return text.strip(), images


def parse_shift(raw: str):
    if m := ADV_PAPER_RE.search(raw):
        year, paper = m.groups()
        return int(year), f"{year} Paper {paper}"
    m = DATE_RE.search(raw)
    if m:
        day, mon, year, shift = m.groups()
        date = f"{int(day)} {mon.title()} {year}"
        return int(year), f"{date}, Shift {shift}" if shift else date
    y = YEAR_RE.search(raw)  # e.g. "AIEEE 2004", "Main 2014": year-only papers
    return (int(y.group(0)) if y else None), (raw.strip()[:50] or None)


def parse_number(value: str):
    value = value.replace("\\", "").replace("$", "").replace(",", "").strip()
    try:
        return float(value)
    except ValueError:
        return None


def parse_page(page: str):
    """Returns (question, question figure URLs, {option label: figure URLs}, pending reasons).

    Raises ValueError when the page can't be read at all. Problems that the later figure/answer
    steps can fix (image options, several figures, missing numerical key) are returned as pending
    reasons instead, with the question otherwise complete; its `answer` is None if the key is missing.
    """
    soup = BeautifulSoup(page, "html.parser")
    ld_raw = soup.find("script", type="application/ld+json")
    ld = json.loads(ld_raw.get_text()) if ld_raw else []
    if not ld or not ld[0].get("hasPart"):
        raise ValueError("no JSON-LD question")
    ld_q = ld[0]["hasPart"][0]
    ld_answers = ld_q.get("suggestedAnswer") or []

    stem_node = soup.select_one("#imagewrap a") or soup.select_one("#imagewrap")
    if not stem_node:
        raise ValueError("question text not found")
    date_node = stem_node.select_one(".floatright")
    raw_date = date_node.get_text(" ", strip=True).strip("[] ") if date_node else ""
    if date_node:
        date_node.decompose()
    stem, images = to_text(stem_node)
    if not stem:
        raise ValueError("empty question text")

    items = soup.select("#answers li")
    kinds = {i.get("type") for li in items for i in li.find_all("input") if i.get("type") != "hidden"}
    if "text" in kinds or not items:
        qtype = "numerical"
    elif "checkbox" in kinds:
        qtype = "multi_correct"
    else:
        qtype = "single_correct"

    question = {"type": qtype, "stem": stem, "raw_date": raw_date}
    option_figures, pending = {}, []
    if qtype == "numerical":
        if len(ld_answers) != 1:
            raise ValueError(f"numerical question has {len(ld_answers)} answers in JSON-LD")
        a = ld_answers[0]
        raw_value = (a.get("math") or {}).get("value") or a.get("text") or ""
        value = parse_number(raw_value)
        if value is None:
            pending.append(f"numerical answer {raw_value!r} is not a number")
        elif value == 0:
            pending.append("numerical answer is 0 (ExamsNet uses 0 when the key is missing)")
        question["answer"] = {"min": value, "max": value} if value else None
        question["options"] = []
    else:
        options = []
        for i, li in enumerate(items):
            label = li.find("label") or li
            for inp in label.find_all("input"):
                inp.decompose()
            text, figures = to_text(label)
            if figures:
                option_figures[chr(65 + i)] = figures
                text = f"{text} [figure]".strip()
            options.append(text)
        if len(options) != len(ld_answers):
            raise ValueError(f"{len(options)} options on page but {len(ld_answers)} in JSON-LD")
        correct = [(a.get("comment") or {}).get("text", "").strip().lower() == "correct" for a in ld_answers]
        if sum(correct) == 0 or (qtype == "single_correct" and sum(correct) != 1):
            raise ValueError(f"{sum(correct)} options marked correct")
        question["options"] = [
            {"label": chr(65 + i), "content": text, "is_correct": ok}
            for i, (text, ok) in enumerate(zip(options, correct))
        ]
        if option_figures:
            pending.append(f"options {', '.join(option_figures)} are figures")
    if len(images) > 1:
        pending.append(f"{len(images)} figures in question (only one supported)")
    return question, images, option_figures, pending


# ---------------------------------------------------------------- output

def make_ref(code: str, stem: str, shift) -> str:
    key = re.sub(r"\s+", " ", stem).strip().lower() + "|" + (shift or "")
    return f"PYQ-{code}-{hashlib.sha1(key.encode()).hexdigest()[:12]}"


def save_image(url: str, subject_dir: str, slug: str, ref: str, delay: float, offline: bool):
    ext = Path(url.split("?")[0]).suffix.lower() or ".png"
    if ext not in {".png", ".jpg", ".jpeg", ".gif", ".webp", ".svg"}:
        ext = ".png"
    target = IMAGE_ROOT / subject_dir / slug / f"{ref}{ext}"
    if not target.exists():
        if offline:
            return None
        data = fetch(url, delay, binary=True)
        if not data:
            return None
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
    return "/" + target.relative_to(ROOT / "frontend" / "public").as_posix()


def chapter_header(subject_dir: str, slug: str, class_level: str, out_file: Path):
    for source in (out_file, EXISTING_QUESTIONS / subject_dir / f"{slug}.json"):
        if source.exists():
            data = json.loads(source.read_text(encoding="utf-8"))
            return data["chapter"], data.get("subtopics", [])
    name = slug.replace("-", " ").title()
    return {"name": name, "slug": slug, "class_level": class_level, "in_main": True, "in_advanced": True, "position": 0}, []


# ExamsNet appends each exam's new questions to the start of a chapter's last part, newest first, so
# recent years can be read from there until older questions begin (checked on cached chapters).
RECENT_STOP_AFTER = 3


def latest_parts(parts: list[str]) -> list[str]:
    """The last part of each ExamsNet chapter (a chapter of ours can merge several ExamsNet chapters)."""
    last = {}
    for path in parts:
        m = re.match(r"^(.*?)(?:-part-(\d+))?-questions$", path)
        name, number = m.group(1), int(m.group(2) or 0)
        if number >= last.get(name, (-1, ""))[0]:
            last[name] = (number, path)
    return [path for _, path in last.values()]


def in_years(year, args) -> bool:
    if not (args.min_year or args.max_year):
        return True
    return year is not None and (args.min_year or 0) <= year <= (args.max_year or 9999)


def scrape_chapter(subject: str, slug: str, entry: dict, args) -> None:
    code, subject_dir = SUBJECTS[subject]
    out_file = args.out / subject_dir / f"{slug}.json"
    report_file = args.out / ".reports" / f"{slug}.json"
    chapter, subtopics = chapter_header(subject_dir, slug, entry["class_level"], out_file)
    if not any(s["slug"] == DEFAULT_SUBTOPIC["slug"] for s in subtopics):
        subtopics.append(dict(DEFAULT_SUBTOPIC))

    pending_file = args.out / ".pending" / subject_dir / f"{slug}.json"
    # Where each imported question's figure came from; the official-paper crop step replaces these.
    figures_file = args.out / ".figures" / subject_dir / f"{slug}.json"
    figure_sources = json.loads(figures_file.read_text(encoding="utf-8")) if figures_file.exists() else {}
    previous, previous_pending = {}, {}
    if out_file.exists():
        previous = {q["ref"]: q for q in json.loads(out_file.read_text(encoding="utf-8")).get("questions", [])}
    if pending_file.exists():
        previous_pending = {q["ref"]: q for q in json.loads(pending_file.read_text(encoding="utf-8")).get("questions", [])}

    questions, pending, flagged, seen, skipped = {}, {}, [], set(), 0
    done = lambda: args.limit and len(questions) + len(pending) + len(flagged) >= args.limit  # noqa: E731
    parts = latest_parts(entry["parts"]) if args.recent_only else entry["parts"]
    for part in parts:
        total = question_count(part, args.delay, args.offline)
        print(f"{part}: {total} questions")
        older_streak = 0
        for n in range(1, total + 1):
            if done():
                break
            if args.recent_only and older_streak >= RECENT_STOP_AFTER:
                print(f"  reached questions older than {args.min_year}; rest of this part skipped")
                break
            source = f"{BASE}{part}/{n}"
            page = trimmed_page(part, n, args.delay, args.offline)
            if not page:
                flagged.append({"source": source, "reason": "page not available"})
                continue
            try:
                parsed, images, option_figures, pending_reasons = parse_page(page)
            except (ValueError, json.JSONDecodeError) as e:
                flagged.append({"source": source, "reason": str(e)})
                continue

            # JEE Main has no multi-correct questions; ExamsNet sometimes shows checkboxes anyway.
            if (args.exam_value == "jee_main" and parsed["type"] == "multi_correct"
                    and sum(o["is_correct"] for o in parsed["options"]) == 1):
                parsed["type"] = "single_correct"
            raw_date = parsed.pop("raw_date")
            year, shift = parse_shift(raw_date)
            if not in_years(year, args):
                skipped += 1
                if year is not None and args.min_year and year < args.min_year:
                    older_streak += 1
                continue
            older_streak = 0
            ref = make_ref(code, parsed["stem"], shift)
            if ref in seen:
                continue
            seen.add(ref)

            if pending_reasons:
                # Complete except for figures/key: kept for the figure step, with the figure URLs.
                pending[ref] = {
                    "ref": ref, "type": parsed["type"], "exam": args.exam_value, "year": year, "shift": shift,
                    "paper_label": raw_date, "source": source, "pending_reasons": pending_reasons,
                    "stem": parsed["stem"], "options": parsed["options"],
                    **({"answer": parsed["answer"]} if "answer" in parsed else {}),
                    "figures": {"question": images, "options": option_figures},
                }
                print(f"  {n:>3} pend {ref} {parsed['type']:<14} {shift or '-'}  ({'; '.join(pending_reasons)})")
                continue

            image = None
            if images:
                url = save_image(images[0], subject_dir, slug, ref, args.delay, args.offline)
                if not url:
                    flagged.append({"source": source, "ref": ref, "reason": "figure could not be downloaded"})
                    continue
                image = {"url": url, "alt": f"Figure for this {chapter['name']} question"}
                figure_sources[ref] = {"source_image": images[0], "source": source, "exam": args.exam_value,
                                       "year": year, "shift": shift, "paper_label": raw_date}

            old = previous.get(ref, {})
            questions[ref] = {
                "ref": ref,
                "subtopic": old.get("subtopic", DEFAULT_SUBTOPIC["slug"]),
                "type": parsed["type"],
                "difficulty": old.get("difficulty", DEFAULT_DIFFICULTY),
                "expected_time_sec": old.get("expected_time_sec", DEFAULT_TIME[parsed["type"]]),
                "source_type": "pyq",
                "exam": args.exam_value,
                "year": year,
                "shift": shift,
                "status": old.get("status", "draft"),
                "stem": parsed["stem"],
                "image": image,
                "options": parsed["options"],
                **({"answer": parsed["answer"]} if "answer" in parsed else {}),
                "solution": old.get("solution", ""),
            }
            print(f"  {n:>3} ok   {ref} {parsed['type']:<14} {shift or '-'}{'  [figure]' if image else ''}")
        if done():
            break

    for f in flagged:
        print(f"  flagged {f['source']}: {f['reason']}")

    # Keep questions from earlier runs that this run didn't reach (e.g. an earlier run without --limit),
    # unless this run found they now belong in the other file.
    for ref, q in previous.items():
        if ref not in pending and in_years(q.get("year"), args):
            questions.setdefault(ref, q)
    for ref, q in previous_pending.items():
        if ref not in questions and in_years(q.get("year"), args):
            pending.setdefault(ref, q)
    order = lambda q: (q["year"] or 0, q["shift"] or "", q["ref"])  # noqa: E731
    ordered = sorted(questions.values(), key=order)

    def shown(path: Path):
        return path.relative_to(ROOT) if path.is_relative_to(ROOT) else path

    def write(path: Path, data: dict):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    write(out_file, {"subject": code, "chapter": chapter, "subtopics": subtopics, "passages": [], "questions": ordered})
    write(pending_file, {"subject": code, "chapter": chapter, "questions": sorted(pending.values(), key=order)})
    write(figures_file, {ref: figure_sources[ref] for ref in sorted(figure_sources) if ref in questions})
    write(report_file, {"chapter": slug, "flagged": flagged})
    print(f"\nWrote {len(ordered)} questions to {shown(out_file)}")
    print(f"{len(pending)} pending (figures/key) in {shown(pending_file)}")
    print(f"{len(flagged)} unreadable, listed in {shown(report_file)}")
    if skipped:
        print(f"{skipped} outside the selected years (not saved)")


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--list", action="store_true", help="list chapters and how they map to our slugs")
    parser.add_argument("--chapter", action="append", default=[], help="our chapter slug (repeatable)")
    parser.add_argument("--all", action="store_true", help="scrape every chapter (with --subject: every chapter of it)")
    parser.add_argument("--subject", choices=sorted(SUBJECTS), help="only this subject (for --list or ambiguous slugs)")
    parser.add_argument("--limit", type=int, default=0, help="stop after this many questions per chapter")
    parser.add_argument("--delay", type=float, default=DEFAULT_DELAY, help="seconds between requests")
    parser.add_argument("--offline", action="store_true", help="only re-parse cached pages, no network")
    parser.add_argument("--exam", choices=sorted(EXAMS), default="main")
    parser.add_argument("--min-year", type=int, help="only keep questions from this year on")
    parser.add_argument("--max-year", type=int, help="only keep questions up to this year")
    parser.add_argument("--recent-only", action="store_true",
                        help="with --min-year: read only the start of each chapter's last part, where recent years are")
    parser.add_argument("--out", type=Path, help="output root (default: generated/scraped, or scraped-advanced)")
    args = parser.parse_args()
    exam = EXAMS[args.exam]
    args.exam_value = exam["exam"]
    args.out = (args.out or exam["out"]).resolve()
    if args.recent_only and not args.min_year:
        parser.error("--recent-only needs --min-year")

    chapters = discover_chapters(exam, args.delay, args.offline)
    if args.subject:
        chapters = {k: v for k, v in chapters.items() if k[0] == args.subject}

    if args.all:
        failed = []
        for (subject, slug), entry in sorted(chapters.items()):
            print(f"\n===== {subject} / {slug} =====")
            try:
                scrape_chapter(subject, slug, entry, args)
            except Exception as e:  # one broken chapter shouldn't stop an hours-long run
                failed.append(f"{subject}/{slug}: {e}")
                print(f"  chapter failed: {e}")
        print(f"\nDone. {len(chapters) - len(failed)} chapters written, {len(failed)} failed.")
        for f in failed:
            print(f"  {f}")
        return

    if args.list or not args.chapter:
        for (subject, slug), entry in sorted(chapters.items()):
            exists = (EXISTING_QUESTIONS / SUBJECTS[subject][1] / f"{slug}.json").exists()
            names = ", ".join(sorted(entry["examsnet_names"]))
            print(f"{subject:<10} {slug:<40} {'existing' if exists else 'NEW':<9} class {entry['class_level']}  "
                  f"{len(entry['parts'])} part(s)  <- {names}")
        return

    for slug in args.chapter:
        matches = [(s, sl) for (s, sl) in chapters if sl == slug]
        if not matches:
            sys.exit(f"Unknown chapter slug {slug!r}. Run with --list to see them.")
        if len(matches) > 1:
            sys.exit(f"{slug!r} exists in {[m[0] for m in matches]}; pass --subject.")
        subject, _ = matches[0]
        scrape_chapter(subject, slug, chapters[(subject, slug)], args)


if __name__ == "__main__":
    main()
