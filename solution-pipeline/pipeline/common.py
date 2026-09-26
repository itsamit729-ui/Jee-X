"""Shared pieces: config, agent definitions, question text, answer checking, formatting checks."""

import hashlib
import json
import math
import re
import urllib.request
from pathlib import Path

HOME = Path(__file__).resolve().parent.parent  # the solution-pipeline folder
CONFIG = json.loads((HOME / "config.json").read_text(encoding="utf-8"))


def path(key: str) -> Path:
    p = HOME / CONFIG[key]
    if key.endswith("_dir"):
        p.mkdir(parents=True, exist_ok=True)
    else:
        p.parent.mkdir(parents=True, exist_ok=True)
    return p


# ---------------------------------------------------------------- agents

def load_agent(name: str) -> dict:
    """agents/<name>.md: YAML-style front matter (name, model, tools, allowed-tools) + the system prompt."""
    text = (HOME / "agents" / f"{name}.md").read_text(encoding="utf-8")
    m = re.match(r"^---\s*\n(.*?)\n---\s*\n(.*)$", text, re.S)
    if not m:
        raise ValueError(f"agents/{name}.md has no front matter")
    meta = {}
    for line in m.group(1).splitlines():
        if ":" in line:
            key, value = line.split(":", 1)
            meta[key.strip()] = value.strip().strip('"').strip("'")
    meta["prompt"] = m.group(2).strip()
    meta["allowed"] = [t.strip() for t in meta.get("allowed-tools", "").split(",") if t.strip()]
    return meta


# ---------------------------------------------------------------- questions

def load_questions() -> list[dict]:
    f = path("questions_file")
    if not f.exists():
        raise SystemExit(f"{f} not found. Run export_questions.py (on the machine with database access) "
                         "or copy the question pack from there.")
    return [json.loads(line) for line in f.read_text(encoding="utf-8").splitlines() if line.strip()]


def in_shard(ref: str, shard: str | None) -> bool:
    """shard "k/n": this machine takes the k-th of n fixed, non-overlapping slices of the questions."""
    if not shard:
        return True
    k, n = (int(x) for x in shard.split("/"))
    return int(hashlib.sha1(ref.encode()).hexdigest(), 16) % n == k - 1


def question_text(q: dict) -> str:
    kind = {"single_correct": "Single correct option", "multi_correct": "One or more options correct",
            "numerical": "Numerical answer (give the number)"}[q["type"]]
    lines = [f"Subject: {q['subject']} | Chapter: {q['chapter']} | Type: {kind}", "", q["stem"]]
    if q.get("image_url"):
        lines += ["", "(The figure for this question is attached.)"]
    if q["type"] != "numerical":
        lines += [""] + [f"({o['label']}) {o['content']}" for o in q["options"]]
    return "\n".join(lines)


def answer_key(q: dict) -> str:
    return str(q["answer"]) if q["type"] == "numerical" else ",".join(q["correct"])


def matches_key(q: dict, answer: str) -> bool:
    if q["type"] == "numerical":
        m = re.search(r"-?\d+(?:\.\d+)?(?:[eE]-?\d+)?", str(answer).replace(",", ""))
        if not m:
            return False
        got, lo, hi = float(m.group(0)), float(q["answer_min"]), float(q["answer_max"])
        if lo <= got <= hi:
            return True
        want = float(q["answer"])
        return math.isclose(got, want, rel_tol=0.01, abs_tol=0.01) or round(got) == round(want) == want
    return sorted(set(re.findall(r"[A-D]", str(answer).upper()))) == sorted(q["correct"])


def figure_file(q: dict) -> Path | None:
    """The question's figure, downloaded once from the live site into data/images."""
    url = q.get("image_url")
    if not url:
        return None
    suffix = Path(url.split("?")[0]).suffix or ".png"
    local = path("images_dir") / f"{q['ref']}{suffix}"
    if not local.exists():
        full = url if url.startswith("http") else CONFIG["image_base_url"].rstrip("/") + url
        request = urllib.request.Request(full, headers={"User-Agent": "JeeEdgeSolutionPipeline/1.0"})
        with urllib.request.urlopen(request, timeout=60) as response:
            local.write_bytes(response.read())
    return local


# ---------------------------------------------------------------- solution text

# LaTeX commands that start with a backslash-n; any other backslash-n in a solution is a line break
# the model typed as text, and becomes a real one. The lookahead sees the text after "\n", so the
# names are compared without their leading "n".
_LATEX_N = ("nabla", "natural", "nearrow", "neg", "neq", "nexists", "newline", "ngeq", "ngtr", "ni", "nleq", "nless",
            "nmid", "not", "notin", "nparallel", "nsubseteq", "nsupseteq", "nu", "nwarrow", "ne")
_LITERAL_NEWLINE = re.compile(r"\\n(?!(?:%s)(?![A-Za-z]))" % "|".join(sorted((c[1:] for c in _LATEX_N), key=len, reverse=True)))


def clean_solution(text: str) -> str:
    text = _LITERAL_NEWLINE.sub("\n", text.replace("\r\n", "\n"))
    return "\n".join(line.rstrip() for line in text.strip().splitlines())


def format_problems(solution: str) -> list[str]:
    """Cheap checks a solution must pass before the checker spends tokens on it."""
    problems = []
    if solution.count("$") < 2:
        problems.append("The solution has no LaTeX: write every formula and number with units inside $...$.")
    elif solution.replace("$$", "").count("$") % 2:
        problems.append("A $ delimiter is unbalanced; every $...$ must be closed.")
    if "\\(" in solution or "\\[" in solution:
        problems.append("Use $...$ / $$...$$ delimiters, not \\( \\) or \\[ \\].")
    if len(solution.splitlines()) < 2:
        problems.append("Put each step on its own line.")
    return problems
