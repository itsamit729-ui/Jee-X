"""Fill answer keys for scraped questions that came without one, from sources other than the scraped site.

Sources (each one only fills a question it can match safely; nothing is guessed):
  pw    PhysicsWallahAI/JEE-Main-2025-Math (Hugging Face, Apache-2.0): every 2025 maths question with the
        NTA-verified answer. Matched by question text, the answer mapped onto our options by content.
  nta   NTA's official final keys (scripts/nta_keys.py): numerical answers per shift and subject. MCQ keys
        can't be used (NTA shuffles question and option order per candidate), but a numerical value is
        accepted when exactly one numerical answer in that shift and subject equals it - used as a check.

  grafite  ruh-ai/grafite-jee-mains-qna-no-img (Hugging Face CSV, no licence stated: only the answer letters
        and values are used). JEE Main 2019-2024 by shift; matched by text within the same shift.
  keys  keys found by the solution pipeline's key mode (solution-pipeline/pipeline/find_keys.py): two
        independent solves agree and the checker accepts the solution. Numericals still face the NTA check.

Usage:
  python scripts/answer_sources.py --year 2025 --pw DIR_WITH_PW_JSONL --nta KEY.pdf [KEY2.pdf] [--apply]
  ... --export-pack solution-pipeline/data/keyless.jsonl     # questions still without a key, for find_keys.py
  ... --pipeline-keys solution-pipeline/data/keys            # use the keys find_keys.py found
Without --apply it only reports; with --apply it adds the answers (and their source) to
generated/scraped/.answers/<year>.json. Re-running scrape_pyqs.py for that year then fills them in and moves
those questions from pending into the chapter files (pages come from its cache; only figures are fetched).
"""

import argparse
import collections
import glob
import html
import json
import os
import re
import sys

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
SCRAPED = os.path.join(ROOT, "generated", "scraped")
NO_KEY = "no answer key on the page"


def norm(s):
    """question text for fuzzy matching: letters and digits only"""
    s = html.unescape(re.sub(r"<[^>]+>", " ", str(s or ""))).lower()
    s = re.sub(r"\\(mathrm|text|mathbf|operatorname|left|right|displaystyle|limits|quad|,|;|!)", " ", s)
    s = re.sub(r"\\(d|t)?frac", " frac ", s)
    s = re.sub(r"[^a-z0-9]+", " ", s)
    return " ".join(s.split())


def onorm(s):
    """option text keeping signs and fractions: '$\\; \\frac{3}{2}$' and '3/2' both give '3/2'"""
    s = html.unescape(re.sub(r"<[^>]+>", "", str(s or ""))).lower().replace("\u2212", "-")
    s = re.sub(r"\\[()\[\]]|\$", "", s)
    s = re.sub(r"\\(left|right|displaystyle|mathrm|text|quad)\b|\\[;,!]", "", s)
    for _ in range(3):
        s = re.sub(r"\\[dt]?frac\s*\{([^{}]*)\}\s*\{([^{}]*)\}", r"(\1)/(\2)", s)
    s = re.sub(r"\s+|\\", "", s)
    s = re.sub(r"\(([a-z0-9.]+)\)", r"\1", s)
    return s.replace("{", "").replace("}", "")


def onorm_loose(s):
    """onorm without sub/superscript marks, brackets and arrow spelling: 'CH_3CON(CH_3)_2' = 'CH3CON(CH3)2',
    'A\\to P' = 'A→P', '{5 \\over 6}' = '\\frac{5}{6}', '\\frac{25}{\\sqrt{3}}' = '25/sqrt3', '–1' = '-1'.
    Used only when onorm finds no option; a clash between two options makes the map fail."""
    s = str(s or "").replace("–", "-").replace("—", "-")
    s = re.sub(r"\\sqrt\s*\{([^{}]*)\}", r"sqrt\1", s)  # so the \frac below sees no nested braces
    s = re.sub(r"\{([^{}]*)\\over([^{}]*)\}", r"\\frac{\1}{\2}", s)
    s = onorm(s).replace("→", "to").replace("rightarrow", "to").replace("longto", "to")
    return re.sub(r"[_^()\[\]]|operatorname|mathbf|mathrm", "", s)


def grams(s, n=4):
    s = s.replace(" ", "")
    return {s[i:i + n] for i in range(max(1, len(s) - n + 1))}


def containment(a, b):
    return len(a & b) / max(1, min(len(a), len(b)))


def load_questions(year, subjects):
    """[(path, question, keyed)] for the year, from the chapter files and the pending files"""
    out = []
    for subject in subjects:
        for base, keyed in ((os.path.join(SCRAPED, subject), True), (os.path.join(SCRAPED, ".pending", subject), False)):
            for path in sorted(glob.glob(os.path.join(base, "*.json"))):
                for q in json.load(open(path, encoding="utf-8"))["questions"]:
                    if q.get("year") == year:
                        out.append((path, q, keyed and NO_KEY not in (q.get("pending_reasons") or [])))
    return out


def current_key(q):
    if q["type"] == "numerical":
        a = q.get("answer")
        return None if not a else (a["min"], a["max"])
    labels = [o["label"] for o in q.get("options") or [] if o.get("is_correct")]
    return ",".join(labels) or None


# ---------------------------------------------------------------- PW maths
def load_pw(directory):
    rows = []
    for path in sorted(glob.glob(os.path.join(directory, "*.jsonl"))):
        for line in open(path, encoding="utf-8"):
            if line.strip():
                r = json.loads(line)
                r["_g"] = grams(norm(r["question"]))
                rows.append(r)
    return rows


def pw_answer(q, r):
    """our answer from PW row r: ("numerical", value) | ("mcq", "A,C", exact_option_set) | None"""
    if r["question_type"] == 0:
        if q["type"] != "numerical":
            return None
        try:
            return ("numerical", float(r["answer"]), True)
        except (TypeError, ValueError):
            return None
    if q["type"] == "numerical" or not r.get("correct_options"):
        return None
    for fn in (onorm, onorm_loose):
        ours = {o["label"]: fn(o["content"]) for o in q["options"]}
        theirs = [fn(o) for o in r["options"]]
        if len(set(ours.values())) < len(ours):  # two of our options look the same: can't map safely
            return None
        labels = []
        for i in r["correct_options"]:
            hit = [label for label, text in ours.items() if text == theirs[i]]
            if len(hit) != 1:
                break
            labels.append(hit[0])
        else:
            exact_set = sorted(theirs) == sorted(ours.values())
            return ("mcq", ",".join(sorted(labels)), exact_set)
    return None


def grafite_shift(paper_id):
    """'jee-main-2024-online-1st-february-morning-shift' -> '1 Feb 2024, Shift 1' (2019-early 2021 end in '-slot')"""
    m = re.match(r"jee-main-(\d{4})-online-(\d+)\w*-([a-z]+)-(morning|evening)-(?:shift|slot)$", paper_id or "")
    if not m:
        return None
    return f"{int(m.group(2))} {m.group(3)[:3].title()} {m.group(1)}, Shift {1 if m.group(4) == 'morning' else 2}"


def load_grafite(path, year):
    """ruh-ai/grafite-jee-mains-qna-no-img CSV rows for one year, in the PW row shape (answers only are used)"""
    import csv
    rows = []
    with open(path, encoding="utf-8") as f:
        for r in csv.DictReader(f):
            shift = grafite_shift(r["paper_id"])
            if not shift or not shift.split(",")[0].endswith(str(year)):
                continue
            if r["question_type"] == "integer":
                row = {"question_type": 0, "answer": r["answer"], "options": [], "correct_options": []}
            else:
                options = json.loads(r["options"] or "[]")
                labels = [o["identifier"] for o in options]
                correct = [labels.index(c) for c in json.loads(r["correct_option"] or "[]") if c in labels]
                row = {"question_type": 1, "answer": None, "options": [o["content"] for o in options],
                       "correct_options": correct}
            row.update(question=r["question"], shift=shift, _g=grams(norm(r["question"])))
            rows.append(row)
    return rows


def match_pw(questions, rows):
    """{ref: (kind, answer, score)} for questions matched safely to a row (PW or grafite shape). Rows that
    know their shift are only compared with questions from the same shift."""
    found, stats = {}, collections.Counter()
    for _, q, _ in questions:
        g = grams(norm(q["stem"]))
        pool = [(i, r) for i, r in enumerate(rows) if not r.get("shift") or r["shift"] == q.get("shift")]
        if len(pool) < 2:
            stats["no rows for this shift"] += 1
            continue
        scored = sorted(((containment(g, r["_g"]), i) for i, r in pool), reverse=True)[:2]
        best, i = scored[0]
        if best < 0.6 or best - scored[1][0] < 0.2:
            stats["no text match"] += 1
            continue
        got = pw_answer(q, rows[i])
        if got is None:
            stats["options did not map"] += 1
            continue
        kind, answer, exact_set = got
        if best < 0.8 and not exact_set:  # loose text match: trust it only when every option matches too
            stats["loose match rejected"] += 1
            continue
        found[q["ref"]] = (kind, answer, round(best, 3))
        stats["matched"] += 1
    return found, stats


# ---------------------------------------------------------------- NTA numericals
SUBJECT_BLOCK = {"mathematics": 0, "physics": 1, "chemistry": 2}  # subject order in NTA papers
REF_SUBJECT = {"MATH": "mathematics", "PHY": "physics", "CHEM": "chemistry"}


def nta_numericals(paths):
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import nta_keys
    keys, notes = nta_keys.load_keys(paths)
    out = collections.defaultdict(list)  # (shift, subject) -> [values]
    for shift, answers in keys.items():
        for n, a in answers.items():
            if a["type"] == "numerical":
                subject = [s for s, b in SUBJECT_BLOCK.items() if b == (n - 1) // notes[shift]["block"]][0]
                out[(shift, subject)].append(a["answer"])
    return out, set(keys)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--year", type=int, required=True)
    ap.add_argument("--pw", help="directory with the PhysicsWallahAI JEE-Main-<year>-Math *.jsonl files")
    ap.add_argument("--grafite", help="ruh-ai/grafite-jee-mains-qna-no-img CSV (JEE Main 2019-2024, with shifts)")
    ap.add_argument("--nta", nargs="*", default=[], help="NTA final answer key PDFs for the year")
    ap.add_argument("--subjects", nargs="*", default=list(SUBJECT_BLOCK))
    ap.add_argument("--pipeline-keys", help="solution-pipeline/data/keys (results of find_keys.py)")
    ap.add_argument("--export-pack", help="write the questions still without a key here (JSONL for find_keys.py)")
    ap.add_argument("--apply", action="store_true")
    args = ap.parse_args()

    questions = load_questions(args.year, args.subjects)
    keyless = [x for x in questions if not x[2]]
    print(f"{args.year}: {len(questions)} questions, {len(keyless)} without a key")
    fills = {}  # ref -> (answer, source)
    report = collections.Counter()

    sources = []
    if args.pw:
        sources.append(("PW", "pw-jee-main-math", load_pw(args.pw)))
    if args.grafite:
        sources.append(("grafite", "grafite-jee-mains", load_grafite(args.grafite, args.year)))
    for name, source, rows in sources:
        found, stats = match_pw(questions, rows)
        print(f"{name}:", dict(stats))
        for _, q, keyed in questions:  # validation where a key is already known
            if keyed and q["ref"] in found:
                kind, answer, _ = found[q["ref"]]
                truth = current_key(q)
                ok = (truth[0] - 1e-6 <= answer <= truth[1] + 1e-6) if kind == "numerical" else truth == answer
                report[f"{name} agrees with existing key" if ok else f"{name} DISAGREES with existing key"] += 1
                if not ok:
                    print(f"  disagreement {q['ref']} existing {truth} {name} {answer}")
            elif q["ref"] in found and q["ref"] not in fills:
                fills[q["ref"]] = (found[q["ref"]][1], source)

    if args.pipeline_keys:
        found = 0
        for path in glob.glob(os.path.join(args.pipeline_keys, "*.json")):
            r = json.load(open(path, encoding="utf-8"))
            if r.get("verdict") == "key_found" and r["ref"] not in fills:
                answer = float(r["key"]) if r["type"] == "numerical" else r["key"]
                fills[r["ref"]] = (answer, "pipeline-two-solves-checked")
                found += 1
        print("pipeline keys:", found)

    if args.nta:
        values, shifts = nta_numericals(args.nta)
        for _, q, keyed in questions:
            if q["type"] != "numerical" or q.get("shift") not in shifts:
                continue
            subject = REF_SUBJECT[q["ref"].split("-")[1]]
            pool = values.get((q["shift"], subject), [])
            have = fills.get(q["ref"], (None,))[0] if not keyed else current_key(q)[0]
            if have is None:
                report["numerical: no answer yet (NTA lists several per subject)"] += 1
                continue
            hits = [v for v in pool if abs(v - have) < 1e-6]
            report["numerical confirmed by NTA" if hits else "numerical NOT in NTA's list"] += 1
            if not hits:
                print("  not in NTA list", q["ref"], q["shift"], have, pool)
                fills.pop(q["ref"], None)  # don't fill an answer the official key contradicts

    for k, v in sorted(report.items()):
        print(f"  {k}: {v}")
    print(f"answers found for {len(fills)} of {len(keyless)} keyless questions")

    if args.export_pack:
        subject_name = {"mathematics": "Mathematics", "physics": "Physics", "chemistry": "Chemistry"}
        written, skipped = 0, collections.Counter()
        with open(args.export_pack, "w", encoding="utf-8") as f:
            for path, q, _ in keyless:
                if q["ref"] in fills:
                    continue
                other = [r for r in q.get("pending_reasons") or [] if r != NO_KEY]
                if other:  # option figures / several figures: the pipeline takes one question figure only
                    skipped[other[0].split(" (")[0]] += 1
                    continue
                figures = q.get("figures", {}).get("question") or []
                item = {"ref": q["ref"], "subject": subject_name[os.path.basename(os.path.dirname(path))],
                        "chapter": os.path.splitext(os.path.basename(path))[0].replace("-", " "),
                        "type": q["type"], "exam": q.get("exam"), "year": q.get("year"), "shift": q.get("shift"),
                        "stem": q["stem"], "options": [{"label": o["label"], "content": o["content"]} for o in q.get("options") or []],
                        "image_url": figures[0] if figures else None}
                f.write(json.dumps(item, ensure_ascii=False) + "\n")
                written += 1
        print(f"pack: {written} questions -> {args.export_pack}; left out: {dict(skipped)}")

    if not args.apply:
        print("(dry run; --apply writes them)")
        return
    target = os.path.join(SCRAPED, ".answers", f"{args.year}.json")
    saved = json.load(open(target, encoding="utf-8")) if os.path.exists(target) else {}
    for _, q, _ in keyless:
        if q["ref"] in fills:
            answer, source = fills[q["ref"]]
            saved[q["ref"]] = {"answer": answer, "source": source}
    os.makedirs(os.path.dirname(target), exist_ok=True)
    with open(target, "w", encoding="utf-8") as f:
        json.dump(dict(sorted(saved.items())), f, ensure_ascii=False, indent=1)
    print(f"{len(saved)} answers in {os.path.relpath(target, ROOT)}; re-run the scrape (pages come from its cache) "
          f"to move these questions into the chapter files")


if __name__ == "__main__":
    main()
