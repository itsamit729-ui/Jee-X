"""Solve and verify the next batch of questions from the question pack.

For each question (see README.md for the diagram):
  1. jee-solver solves it blind (never sees the answer key)
  2. the script compares the final answer with the key          -> mismatch: retry once, then flag key_mismatch
  3. the script checks the formatting (LaTeX, line breaks)      -> problems: retry once with the reasons
  4. jee-checker reviews every step and recomputes in Python    -> rejected: retry once with its objections
  5. passed -> "verified"; failed twice -> flagged for a person

Results go to data/results/<ref>.json (one file per question, so runs can stop and resume at any point).
Questions already in data/results are skipped. When the plan's usage limit is hit the batch stops
cleanly and the next run continues.

Usage:
  python pipeline/run_batch.py                      # next `questions_per_run` questions (config.json)
  python pipeline/run_batch.py --limit 20
  python pipeline/run_batch.py --shard 1/2          # this machine takes half 1 of 2 (friend runs --shard 2/2)
  python pipeline/run_batch.py --refs PYQ-PHY-abc   # specific questions
"""

import argparse
import json
import sys
import tempfile
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from claude_runner import UsageLimitReached, call  # noqa: E402
from common import (CONFIG, answer_key, check_calculations, clean_solution, figure_file, format_problems, in_shard,  # noqa: E402
                    load_agent, load_questions, matches_key, path, question_text)

SOLVER_SCHEMA = {
    "type": "object",
    "properties": {
        "solution": {"type": "string", "description": "step-by-step solution, LaTeX in $...$, one step per line"},
        "final_answer": {"type": "string", "description": "option letter(s) like B or A,C; or the number only"},
        "confidence": {"type": "string", "enum": ["high", "medium", "low"]},
    },
    "required": ["solution", "final_answer", "confidence"],
}
CHECKER_SCHEMA = {
    "type": "object",
    "properties": {
        "verdict": {"type": "string", "enum": ["correct", "incorrect"]},
        "issues": {"type": "array", "items": {"type": "string"}},
        "calculations": {"type": "array", "items": {
            "type": "object",
            "properties": {"expression": {"type": "string"}, "claimed": {"type": "string"}},
            "required": ["expression", "claimed"]}},
    },
    "required": ["verdict", "issues", "calculations"],
}

_lock = threading.Lock()
_stop = threading.Event()


def solve_one(q, solver, checker, results_dir: Path, calls_log: Path):
    if _stop.is_set():
        return None
    text = question_text(q)
    figure = figure_file(q)
    calls, attempts = [], []
    feedback, verdict = None, None
    with tempfile.TemporaryDirectory(prefix="jee-") as tmp:
        work = Path(tmp)
        for attempt in (1, 2):
            model = solver["model"] if attempt == 1 else (CONFIG.get("retry_model") or solver["model"])
            prompt = text if not feedback else f"{text}\n\n{feedback}"
            sol, st = call(solver, prompt, SOLVER_SCHEMA, work, figure, model)
            calls.append({"stage": f"solve{attempt}", **st})
            if not sol:
                attempts.append({"attempt": attempt, "error": st.get("error")})
                feedback = "A previous attempt failed to produce a solution. Solve it again carefully."
                continue
            sol["solution"] = clean_solution(sol["solution"])
            ok = matches_key(q, sol["final_answer"])
            record = {"attempt": attempt, "final_answer": sol["final_answer"], "matches_key": ok,
                      "confidence": sol["confidence"], "solution": sol["solution"]}
            attempts.append(record)
            if not ok:
                feedback = ("A previous attempt at this question reached a different result than expected. "
                            "Re-derive it from scratch, checking every assumption, formula and calculation.")
                continue
            problems = format_problems(sol["solution"])
            if problems:
                record["checker"] = {"verdict": "incorrect", "issues": problems, "by": "format_check"}
                feedback = ("A previous solution was rejected for formatting:\n" + "\n".join(f"- {p}" for p in problems) +
                            "\nSolve and write it again following the format rules.")
                continue
            check_prompt = (f"QUESTION\n{text}\n\nANSWER KEY: {answer_key(q)}\n\nCANDIDATE SOLUTION\n{sol['solution']}\n\n"
                            f"Candidate final answer: {sol['final_answer']}")
            chk, cst = call(checker, check_prompt, CHECKER_SCHEMA, work, figure)
            calls.append({"stage": f"check{attempt}", **cst})
            record["checker"] = chk or {"error": cst.get("error")}
            if chk:
                # Recompute every calculation the checker listed, in Python, here (no model tokens).
                mismatches, calc_log = check_calculations(chk.get("calculations"))
                record["calc_check"] = calc_log
                if mismatches:
                    chk = {**chk, "verdict": "incorrect", "issues": list(chk.get("issues") or []) + mismatches}
                    record["checker"] = chk
            if chk and chk["verdict"] == "correct":
                verdict = "verified"
                break
            issues = "\n".join(f"- {i}" for i in (chk or {}).get("issues", [])) or "- the reviewer could not verify it"
            feedback = ("A reviewer rejected a previous solution for these reasons:\n" + issues +
                        "\nSolve it again from scratch, avoiding these problems.")
    if verdict is None:
        last = attempts[-1] if attempts else {}
        verdict = ("checker_rejected" if last.get("matches_key") else
                   "error" if not any("final_answer" in a for a in attempts) else "key_mismatch")
    final = next((a for a in reversed(attempts) if verdict == "verified" and "solution" in a), None)
    result = {
        "ref": q["ref"], "subject": q["subject"], "chapter": q["chapter"], "type": q["type"],
        "has_figure": bool(figure), "answer_key": answer_key(q), "verdict": verdict,
        "solution": final["solution"] if final else None, "final_answer": final["final_answer"] if final else None,
        "solver_model": solver["model"], "checker_model": checker["model"],
        "attempts": attempts, "calls": calls, "finished_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }
    (results_dir / f"{q['ref']}.json").write_text(json.dumps(result, ensure_ascii=False, indent=1), encoding="utf-8")
    tokens = sum(c.get("input", 0) + c.get("cache_create", 0) + c.get("cache_read", 0) + c.get("output", 0) for c in calls)
    with _lock:
        with open(calls_log, "a", encoding="utf-8") as f:
            for c in calls:
                f.write(json.dumps({"ref": q["ref"], **c}) + "\n")
        print(f"  {q['ref']:<24} {q['subject']:<4} {q['type']:<14} {'fig' if figure else '   '} -> {verdict:<16} "
              f"attempts {len(attempts)}  tokens {tokens:,}", flush=True)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--limit", type=int, default=CONFIG["questions_per_run"])
    parser.add_argument("--shard", help='"k/n": take slice k of n (e.g. you 1/2, your friend 2/2)')
    parser.add_argument("--refs", nargs="*", help="only these question refs")
    parser.add_argument("--workers", type=int, default=CONFIG["workers"])
    args = parser.parse_args()

    solver, checker = load_agent("jee-solver"), load_agent("jee-checker")
    results_dir = path("results_dir")
    # "error" results (network failures, timeouts) are retried; verified and flagged ones are final.
    done = {p.stem for p in results_dir.glob("*.json")
            if json.loads(p.read_text(encoding="utf-8")).get("verdict") != "error"}
    todo = [q for q in load_questions()
            if q["ref"] not in done and in_shard(q["ref"], args.shard) and (not args.refs or q["ref"] in args.refs)]
    todo = todo[:args.limit]
    stamp = datetime.now().strftime("%Y%m%d-%H%M")
    calls_log = path("logs_dir") / f"calls-{stamp}.jsonl"
    print(f"{len(done)} already done; solving {len(todo)} now (shard {args.shard or 'all'}, "
          f"solver {solver['model']}, checker {checker['model']}, {args.workers} workers)")

    results, stopped = [], None
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        futures = [pool.submit(solve_one, q, solver, checker, results_dir, calls_log) for q in todo]
        for future in as_completed(futures):
            try:
                r = future.result()
                if r:
                    results.append(r)
            except UsageLimitReached as e:
                stopped = str(e)[:300]
                _stop.set()
            except Exception as e:  # one broken question must not stop the batch
                print(f"  error: {e.__class__.__name__}: {e}", flush=True)

    verdicts = {}
    for r in results:
        verdicts[r["verdict"]] = verdicts.get(r["verdict"], 0) + 1
    tokens = sum(c.get("input", 0) + c.get("cache_create", 0) + c.get("cache_read", 0) + c.get("output", 0)
                 for r in results for c in r["calls"])
    print(f"\nThis run: {len(results)} questions, {verdicts}, {tokens:,} tokens "
          f"({tokens // max(1, len(results)):,} per question)")
    if stopped:
        print(f"Stopped early: usage limit reached ({stopped}). The next run continues from here.")


if __name__ == "__main__":
    main()
