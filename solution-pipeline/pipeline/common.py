"""Shared pieces: config, agent definitions, question text, answer checking, formatting checks."""

import ast
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


# ---------------------------------------------------------------- arithmetic check

_FUNCS = {name: getattr(math, name) for name in ("sqrt", "log", "log10", "log2", "exp", "sin", "cos", "tan", "asin",
                                                  "acos", "atan", "radians", "degrees", "factorial", "comb")}
_FUNCS.update(abs=abs, round=round)
_CONSTS = {"pi": math.pi, "e": math.e}
_BINOPS = {ast.Add: lambda a, b: a + b, ast.Sub: lambda a, b: a - b, ast.Mult: lambda a, b: a * b,
           ast.Div: lambda a, b: a / b, ast.Pow: lambda a, b: a ** b, ast.Mod: lambda a, b: a % b,
           ast.FloorDiv: lambda a, b: a // b}


def safe_eval(expression: str) -> float:
    """Evaluate a numeric expression: numbers, + - * / ** % //, parentheses and a few math functions only."""
    def ev(node):
        if isinstance(node, ast.Expression):
            return ev(node.body)
        if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
            return node.value
        if isinstance(node, ast.BinOp) and type(node.op) in _BINOPS:
            left, right = ev(node.left), ev(node.right)
            if isinstance(node.op, ast.Pow) and abs(right) > 1000:
                raise ValueError("exponent too large")
            return _BINOPS[type(node.op)](left, right)
        if isinstance(node, ast.UnaryOp) and isinstance(node.op, (ast.USub, ast.UAdd)):
            return -ev(node.operand) if isinstance(node.op, ast.USub) else ev(node.operand)
        if isinstance(node, ast.Name) and node.id in _CONSTS:
            return _CONSTS[node.id]
        if (isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id in _FUNCS
                and not node.keywords):
            return _FUNCS[node.func.id](*[ev(a) for a in node.args])
        raise ValueError(f"not allowed: {ast.dump(node)[:60]}")
    return float(ev(ast.parse(expression.replace("^", "**"), mode="eval")))


def _close_enough(value: float, claimed_text: str) -> bool:
    claimed = float(claimed_text)
    if math.isclose(value, claimed, rel_tol=0.01, abs_tol=1e-12):
        return True
    # a claimed value rounded to its shown decimals is fine (17.02 for 17.0213)
    decimals = len(claimed_text.split(".")[1].split("e")[0].split("E")[0]) if "." in claimed_text else 0
    if "e" not in claimed_text.lower():
        return abs(value - claimed) <= 0.5 * 10 ** (-decimals) + 1e-12
    return False


def check_calculations(calculations: list[dict]) -> tuple[list[str], list[dict]]:
    """Recompute every calculation the checker listed. Returns (mismatch issues, per-calculation log)."""
    issues, log = [], []
    for c in calculations or []:
        expr, claimed = str(c.get("expression", "")).strip(), str(c.get("claimed", "")).strip()
        entry = {"expression": expr, "claimed": claimed}
        try:
            value = safe_eval(expr)
            entry["value"] = value
            m = re.fullmatch(r"-?\d+(?:\.\d+)?(?:[eE][-+]?\d+)?", claimed.replace(",", ""))
            if not m:
                entry["status"] = "unparsed_claim"
            elif _close_enough(value, m.group(0)):
                entry["status"] = "ok"
            else:
                entry["status"] = "mismatch"
                issues.append(f"The solution states {claimed} for {expr}, but it evaluates to {value:.6g}.")
        except (ValueError, SyntaxError, TypeError, ZeroDivisionError, OverflowError) as e:
            entry["status"] = f"not_evaluated: {e.__class__.__name__}"
        log.append(entry)
    return issues, log


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
