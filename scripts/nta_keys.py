"""Read NTA's official JEE Main final answer keys (PDF, "Question ID -> Correct Option ID") and turn them
into answers per shift and question number, without needing the question papers.

How the IDs work (checked against the official 2 Apr 2026 Shift 1 paper, all 75 questions):
  - In a shift, every question ID is a common prefix plus a running number in paper order, so ranking the
    part after the shared prefix gives the question number (1-75; Mathematics, Physics, Chemistry).
  - Option IDs share one running counter in paper order: each MCQ takes 4 numbers (options A-D) and each
    numerical (SA) question takes 1. The counter's start is fitted per shift as the only value that puts
    every listed MCQ answer on A-D.
  - Numerical answers are given as the value itself; "Drop"/"DROPPED" marks a cancelled question; two IDs
    joined by "or" mean both options were accepted.

Usage: python scripts/nta_keys.py KEY.pdf [KEY2.pdf ...]   -> prints shifts and a sample
"""

import re
import sys
from datetime import datetime

import pypdf

MONTHS = "Jan Feb Mar Apr May Jun Jul Aug Sep Oct Nov Dec".split()
ID = r"\d{7,13}"


def _common_prefix(values):
    if not values:
        return ""
    first, last = min(values), max(values)
    i = 0
    while i < min(len(first), len(last)) and first[i] == last[i]:
        i += 1
    return first[:i]


def _shift_label(date_text, shift_word):
    d = datetime.strptime(date_text.replace("-", "."), "%d.%m.%Y")
    n = {"first": 1, "second": 2}[shift_word.lower()]
    return f"{d.day} {MONTHS[d.month - 1]} {d.year}, Shift {n}"


def parse_pdf(path):
    """{shift label: [(question_id, answer_token), ...]} in the order they appear (domestic keys only)."""
    text = "\n".join(page.extract_text() or "" for page in pypdf.PdfReader(path).pages)
    shifts = {}
    current, skip = None, False
    for page in re.split(r"(?=Exam Date\s*:)", text):
        m = re.search(r"Exam Date\s*:\s*(\d{2}[.-]\d{2}[.-]\d{4}).{0,200}?Shift\s*:\s*(First|Second)", page, re.S)
        if not m:
            continue
        # keys for centres outside India repeat the same IDs; keep the domestic (India) ones
        skip = bool(re.search(r"Outside India|INTERNATIONAL", page))
        current = _shift_label(m.group(1), m.group(2))
        if skip:
            continue
        pairs = shifts.setdefault(current, [])
        for qid, ans in re.findall(rf"(?m)^\s*({ID})\s+((?:{ID}(?:\s*(?:or|OR)\s*{ID})*)|Drop|DROPPED|-?\d+(?:\.\d+)?)\s*$", page):
            pairs.append((qid, ans))
    return shifts


def answers_for_shift(pairs):
    """{question number: {"type": "mcq"|"numerical"|"dropped", "answer": "A".."D" | "A,C" | value}}"""
    seen, rows = set(), []
    for qid, ans in pairs:
        if qid not in seen:
            seen.add(qid)
            rows.append((qid, ans))
    prefix = _common_prefix([q for q, _ in rows])
    first = min(int(q[len(prefix):]) for q, _ in rows)
    layout = []
    for qid, ans in rows:
        # number from the ID itself, so a line the PDF text lost does not shift the others
        n = int(qid[len(prefix):]) - first + 1
        ids = re.findall(ID, ans)
        kind = "dropped" if ans.upper().startswith("DROP") else ("mcq" if ids else "numerical")
        layout.append((n, kind, ids, ans))
    layout.sort()
    # Option IDs: one counter in paper order. Each subject has 20 MCQs (4 slots) then its numerical
    # questions (1 slot each): 5 since 2025 (75 questions), 10 before (90 questions, 5 to attempt).
    block = subject_block(max(n for n, *_ in layout))
    opt_prefix = _common_prefix([i for _, _, ids, _ in layout for i in ids])
    offsets, counter = {}, 0
    for n in range(1, 3 * block + 1):
        slots = 1 if (n - 1) % block >= 20 else 4
        offsets[n] = (counter, slots)
        counter += slots
    result = {}
    # fit the counter's start: every MCQ answer must land on A-D
    candidates = None
    for n, kind, ids, ans in layout:
        if kind != "mcq":
            continue
        start, _ = offsets[n]
        for i in ids:
            v = int(i[len(opt_prefix):])
            ok = {v - start - k for k in range(1, 5)}
            candidates = ok if candidates is None else candidates & ok
    base = min(candidates) if candidates else None
    for n, kind, ids, ans in layout:
        if kind == "mcq":
            start, _ = offsets[n]
            letters = sorted("ABCD"[int(i[len(opt_prefix):]) - base - start - 1] for i in ids)
            result[n] = {"type": "mcq", "answer": ",".join(letters)}
        elif kind == "numerical":
            result[n] = {"type": "numerical", "answer": float(ans)}
        else:
            result[n] = {"type": "dropped", "answer": None}
    return result, {"questions": len(layout), "block": block, "base_candidates": sorted(candidates or [])}


def subject_block(last_question_number):
    """questions per subject: 25 (2025 on, 75 per paper) or 30 (until 2024, 90 per paper)"""
    return 30 if last_question_number > 75 else 25


def load_keys(paths):
    """{shift label: {question number: answer}} for all given key PDFs."""
    out, notes = {}, {}
    for p in paths:
        for shift, pairs in parse_pdf(p).items():
            out[shift], notes[shift] = answers_for_shift(pairs)
    return out, notes


if __name__ == "__main__":
    keys, notes = load_keys(sys.argv[1:])
    for shift in sorted(keys, key=lambda s: datetime.strptime(s.split(",")[0], "%d %b %Y")):
        k = keys[shift]
        kinds = {t: sum(1 for v in k.values() if v["type"] == t) for t in ("mcq", "numerical", "dropped")}
        print(f"{shift:<22} questions {notes[shift]['questions']:>3} {kinds} counter fits: {notes[shift]['base_candidates']}"
              f" | Q1 {k.get(1)} Q21 {k.get(21)} Q26 {k.get(26)}")
