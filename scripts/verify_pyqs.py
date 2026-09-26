"""Check the answer keys of scraped PYQs by having Gemini solve each question independently, and
write our own solution, subtopic, difficulty and time for the ones whose key is confirmed.

The scraped key is never shown to the model. Its answer is compared with the key:
  - agree              -> status "reviewed"; our solution, subtopic, difficulty and time are written
  - disagree           -> solved once more with more thinking; if that agrees, as above
  - still disagree     -> left as "draft" and listed in <out>/.reports/<chapter>.verify.json with both
                          answers and the model's working, for a person to settle
Questions with a figure are sent with the image (read from frontend/public).

Each model answer is cached in <out>/.verify-cache/, keyed by question content, so re-runs only pay
for new or changed questions. Questions a person has since set to "published" or "retired" are skipped.

Setup: pip install google-genai, and GEMINI_API_KEY in scripts/.env (same as generate_pyqs.py).

Usage:
  python scripts/verify_pyqs.py generated/scraped/physics/alternating-current.json
  python scripts/verify_pyqs.py generated/scraped/physics/alternating-current.json --limit 10
  python scripts/verify_pyqs.py generated/scraped/physics/*.json --dry-run     # show prompts, no API calls
"""

import argparse
import hashlib
import json
import math
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from generate_pyqs import (  # noqa: E402  -- shared Gemini helpers
    DEFAULT_FALLBACK_MODEL, DEFAULT_MODEL, DIFFICULTY_MAX, DIFFICULTY_MIN, RETRIES, RETRYABLE,
    api_keys, load_env, repair_latex, slugify, thinking_config,
)

ROOT = Path(__file__).resolve().parent.parent
PUBLIC = ROOT / "frontend" / "public"
CACHE_VERSION = 1
SECOND_TRY_THINKING = "high"
MAX_OUTPUT_TOKENS = 8192
SKIP_STATUSES = {"published", "retired"}

SYSTEM = """You are an expert JEE Main teacher. Solve the question yourself, step by step, then give the final answer.
Write the solution for a student: concise, correct, LaTeX in $...$ for all maths, \\n between steps.
Do not mention answer options by letter inside the solution text except in the last line.
Pick the subtopic from the existing list when one fits; otherwise propose a short new one.
difficulty: 1 (very easy) to 10 (very hard) for a JEE Main aspirant. secs: realistic solving time in seconds."""

MIME = {".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".gif": "image/gif", ".webp": "image/webp"}


def schema(numerical: bool, labels: list[str]):
    props = {
        # Solution before key, so the key is derived rather than guessed.
        "sol": {"type": "STRING"},
        "key": {"type": "NUMBER"} if numerical else {"type": "STRING", "enum": labels},
        "sub": {"type": "STRING"},
        "sub_name": {"type": "STRING"},
        "diff": {"type": "INTEGER", "minimum": DIFFICULTY_MIN, "maximum": DIFFICULTY_MAX},
        "secs": {"type": "INTEGER"},
    }
    return {"type": "OBJECT", "properties": props, "required": list(props), "property_ordering": list(props)}


def prompt_for(q: dict, chapter: str, subtopics: list[dict]) -> str:
    lines = [f"Chapter: {chapter}", f"Question type: {q['type'].replace('_', ' ')}", "", q["stem"]]
    if q["type"] == "numerical":
        lines.append("\nThe answer is a number. Give it as `key`.")
    else:
        lines.append("")
        lines += [f"({o['label']}) {o['content']}" for o in q["options"]]
        lines.append("\nGive the letter of the correct option as `key`.")
    if q.get("image"):
        lines.append("The attached figure is part of the question.")
    known = [f"{s['slug']} ({s['name']})" for s in subtopics if s["slug"] != "general"]
    if known:
        lines.append("Existing subtopics: " + ", ".join(known))
    return "\n".join(lines)


def scraped_key(q: dict):
    if q["type"] == "numerical":
        return q["answer"]["min"]
    correct = [o["label"] for o in q["options"] if o["is_correct"]]
    return correct[0] if len(correct) == 1 else "".join(correct)


def same_answer(q: dict, model_key) -> bool:
    expected = scraped_key(q)
    if q["type"] != "numerical":
        return str(model_key).strip().upper() == expected
    try:
        got = float(model_key)
    except (TypeError, ValueError):
        return False
    # JEE Main numerical answers are integers (sometimes rounded); allow 1% or 0.01 slack.
    return math.isclose(got, expected, rel_tol=0.01, abs_tol=0.01) or round(got) == round(expected) == expected


def content_key(q: dict, thinking) -> str:
    payload = json.dumps([CACHE_VERSION, thinking, q["type"], q["stem"], q.get("options"), q.get("image")],
                         sort_keys=True, ensure_ascii=True)
    return hashlib.sha256(payload.encode()).hexdigest()[:24]


class Solver:
    def __init__(self, model, keys, thinking, fallback, cache_dir: Path):
        import httpx
        from google import genai
        from google.genai import errors, types

        self.genai, self.errors, self.types = genai, errors, types
        self.network_errors = (httpx.TransportError, OSError)
        self.model, self.keys, self.thinking, self.fallback = model, keys, thinking, fallback
        self.key_index = 0
        self.client = genai.Client(api_key=keys[0])
        self.cache_dir = cache_dir
        self.usage = {"calls": 0, "input": 0, "output": 0, "thinking": 0}

    def solve(self, q, chapter, subtopics, thinking):
        cache = self.cache_dir / f"{q['ref']}-{content_key(q, thinking)}.json"
        if cache.exists():
            return json.loads(cache.read_text(encoding="utf-8"))
        parts = [self.types.Part.from_text(text=prompt_for(q, chapter, subtopics))]
        if q.get("image"):
            path = PUBLIC / q["image"]["url"].lstrip("/")
            parts.append(self.types.Part.from_bytes(data=path.read_bytes(), mime_type=MIME.get(path.suffix.lower(), "image/png")))
        numerical = q["type"] == "numerical"
        labels = [o["label"] for o in q.get("options", [])]
        result = self._generate(parts, schema(numerical, labels), thinking)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        cache.write_text(json.dumps(result, ensure_ascii=False, indent=1), encoding="utf-8")
        return result

    def _generate(self, parts, response_schema, thinking):
        while True:
            try:
                return self._call(parts, response_schema, thinking)
            except self.errors.APIError as e:
                if e.code not in RETRYABLE or not self.fallback or self.fallback == self.model:
                    raise
                print(f"    {self.model} still unavailable; switching to {self.fallback}")
                self.model, self.fallback = self.fallback, None

    def _call(self, parts, response_schema, thinking):
        config = self.types.GenerateContentConfig(
            system_instruction=SYSTEM,
            response_mime_type="application/json",
            response_schema=response_schema,
            temperature=0.2 if self.model.startswith("gemini-2") else None,
            max_output_tokens=MAX_OUTPUT_TOKENS,
            thinking_config=thinking_config(self.types, self.model, thinking),
            automatic_function_calling=self.types.AutomaticFunctionCallingConfig(disable=True),
        )
        for attempt in range(1, RETRIES + 1):
            try:
                response = self.client.models.generate_content(
                    model=self.model, contents=[self.types.Content(role="user", parts=parts)], config=config)
                self.usage["calls"] += 1
                if usage := response.usage_metadata:
                    self.usage["input"] += usage.prompt_token_count or 0
                    self.usage["output"] += usage.candidates_token_count or 0
                    self.usage["thinking"] += usage.thoughts_token_count or 0
                data = json.loads(response.text or "")
                if not isinstance(data, dict) or "key" not in data:
                    raise ValueError("response is not an answer object")
                return data
            except self.errors.APIError as e:
                if e.code not in RETRYABLE or attempt == RETRIES:
                    raise
                if e.code == 429 and len(self.keys) > 1:
                    self.key_index = (self.key_index + 1) % len(self.keys)
                    self.client = self.genai.Client(api_key=self.keys[self.key_index])
                reason = f"{e.code} {e.status}"
            except ValueError as e:
                if attempt >= 2:
                    raise
                reason = str(e)
            except self.network_errors as e:
                if attempt == RETRIES:
                    raise
                reason = f"network error: {e}"
            wait = 5 * 2 ** (attempt - 1)
            print(f"    {reason}; retrying in {wait}s")
            time.sleep(wait)


def apply(q: dict, answer: dict, subtopics: list[dict]):
    """Write our solution and metadata into a question whose key was confirmed."""
    q["solution"] = repair_latex(str(answer.get("sol") or "").strip())
    slug = slugify(answer.get("sub")) or "general"
    if slug not in {s["slug"] for s in subtopics}:
        name = str(answer.get("sub_name") or "").strip() or slug.replace("-", " ").title()
        position = max((s.get("position", 0) for s in subtopics if s["slug"] != "general"), default=0) + 1
        subtopics.append({"slug": slug, "name": name, "position": position})
    q["subtopic"] = slug
    try:
        q["difficulty"] = min(max(int(answer.get("diff")), DIFFICULTY_MIN), DIFFICULTY_MAX)
    except (TypeError, ValueError):
        pass
    try:
        secs = int(answer.get("secs"))
        if 30 <= secs <= 600:
            q["expected_time_sec"] = secs
    except (TypeError, ValueError):
        pass
    q["status"] = "reviewed"


def verify_file(path: Path, solver, args) -> dict:
    data = json.loads(path.read_text(encoding="utf-8"))
    chapter, subtopics = data["chapter"]["name"], data["subtopics"]
    report_file = path.parent.parent / ".reports" / f"{data['chapter']['slug']}.verify.json"
    old_report = json.loads(report_file.read_text(encoding="utf-8")) if report_file.exists() else {}
    disputed = {d["ref"]: d for d in old_report.get("disputed", [])}
    counts = {"agreed": 0, "agreed_second_try": 0, "disputed": 0, "skipped": 0, "errors": 0}

    todo = [q for q in data["questions"] if q.get("status") not in SKIP_STATUSES]
    counts["skipped"] = len(data["questions"]) - len(todo)
    if args.limit:
        todo = todo[:args.limit]
    print(f"{path.relative_to(ROOT)}: checking {len(todo)} questions")

    for i, q in enumerate(todo, 1):
        if args.dry_run:
            if i == 1:
                print("\n--- prompt for first question ---\n" + prompt_for(q, chapter, subtopics) + "\n---")
            continue
        try:
            first = solver.solve(q, chapter, subtopics, args.thinking)
            if same_answer(q, first["key"]):
                apply(q, first, subtopics)
                disputed.pop(q["ref"], None)
                counts["agreed"] += 1
                print(f"  {i:>3} agree     {q['ref']}  key {scraped_key(q)}")
                continue
            second = solver.solve(q, chapter, subtopics, SECOND_TRY_THINKING)
            if same_answer(q, second["key"]):
                apply(q, second, subtopics)
                disputed.pop(q["ref"], None)
                counts["agreed_second_try"] += 1
                print(f"  {i:>3} agree(2)  {q['ref']}  key {scraped_key(q)}")
                continue
            q["status"] = "draft"
            disputed[q["ref"]] = {
                "ref": q["ref"], "shift": q.get("shift"), "stem": q["stem"],
                "scraped_key": scraped_key(q), "model_keys": [first["key"], second["key"]],
                "model_solution": repair_latex(str(second.get("sol") or "")),
            }
            counts["disputed"] += 1
            print(f"  {i:>3} DISPUTE   {q['ref']}  scraped {scraped_key(q)}  model {first['key']} / {second['key']}")
        except Exception as e:  # keep going; one bad question shouldn't lose the rest of the run
            if getattr(e, "code", None) in (401, 403):
                raise
            counts["errors"] += 1
            print(f"  {i:>3} error     {q['ref']}: {e}")

    if not args.dry_run:
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        report_file.parent.mkdir(parents=True, exist_ok=True)
        report_file.write_text(json.dumps({"chapter": data["chapter"]["slug"], "counts": counts,
                                           "disputed": list(disputed.values())}, ensure_ascii=False, indent=2) + "\n",
                               encoding="utf-8")
        print(f"  {counts}\n  disputes listed in {report_file.relative_to(ROOT)}")
    return counts


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("files", nargs="+", type=Path, help="scraped chapter files")
    parser.add_argument("--limit", type=int, default=0, help="only the first N questions per file")
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--fallback-model", default=DEFAULT_FALLBACK_MODEL)
    parser.add_argument("--thinking", default="low", help="first-try thinking: minimal/low/medium/high or a token budget")
    parser.add_argument("--dry-run", action="store_true", help="print the first prompt per file; no API calls")
    args = parser.parse_args()

    solver = None
    if not args.dry_run:
        load_env()
        keys = api_keys()
        if not keys:
            sys.exit("No Gemini key: put GEMINI_API_KEY=... in scripts/.env")
        cache_dir = args.files[0].resolve().parent.parent / ".verify-cache"
        solver = Solver(args.model, keys, args.thinking, args.fallback_model, cache_dir)

    for f in args.files:
        verify_file(f.resolve(), solver, args)
    if solver:
        print(f"Gemini usage: {solver.usage}")


if __name__ == "__main__":
    main()
