"""Find answer keys for questions that have none (key mode).

For each question in the keyless pack (data/keyless.jsonl, made by scripts/answer_sources.py --export-pack):
  1. jee-solver solves it twice, independently (neither attempt sees the other)
  2. the two answers agree            -> that is the candidate key
     they differ                      -> a third solve; two of three agreeing is the candidate, else needs_person
  3. jee-checker reviews the solution for the candidate (told it is NOT an official key) and the script
     recomputes its calculations      -> correct: "key_found" (key + checked solution); otherwise needs_person
Numerical keys are checked once more against NTA's official values by answer_sources.py when applied.

Results go to data/keys/<ref>.json; finished questions are skipped, so runs stop and resume freely.

Usage:
  python pipeline/find_keys.py --limit 20
  python pipeline/find_keys.py --shard 1/2
"""

import argparse
import json
import math
import re
import sys
import tempfile
import threading
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from claude_runner import UsageLimitReached, call  # noqa: E402
from common import (CONFIG, HOME, check_calculations, clean_solution, figure_file, format_problems, in_shard,  # noqa: E402
                    load_agent, question_text)
from run_batch import CHECKER_SCHEMA, SOLVER_SCHEMA  # noqa: E402

_lock = threading.Lock()
_stop = threading.Event()


def canonical(q, answer):
    """comparable form of a final answer: "A,C" for options, a rounded number for numericals, None if unreadable"""
    if q["type"] == "numerical":
        m = re.search(r"-?\d+(?:\.\d+)?(?:[eE]-?\d+)?", str(answer).replace(",", ""))
        if not m:
            return None
        v = float(m.group(0))
        return str(round(v)) if math.isclose(v, round(v), abs_tol=1e-6) else f"{v:.2f}"
    letters = sorted(set(re.findall(r"[A-D]", str(answer).upper())))
    return ",".join(letters) or None


def find_one(q, solver, checker, out_dir: Path):
    if _stop.is_set():
        return None
    text, figure = question_text(q), figure_file(q)
    calls, solves = [], []
    with tempfile.TemporaryDirectory(prefix="jee-key-") as tmp:
        work = Path(tmp)

        def solve():
            sol, st = call(solver, text, SOLVER_SCHEMA, work, figure)
            calls.append({"stage": f"solve{len(solves) + 1}", **st})
            if sol:
                sol["solution"] = clean_solution(sol["solution"])
                sol["canonical"] = canonical(q, sol["final_answer"])
            solves.append(sol or {"error": st.get("error"), "canonical": None})

        solve()
        solve()
        votes = Counter(s["canonical"] for s in solves if s["canonical"])
        if not votes or votes.most_common(1)[0][1] < 2:
            solve()
            votes = Counter(s["canonical"] for s in solves if s["canonical"])
        candidate = next((a for a, n in votes.most_common(1) if n >= 2), None)
        verdict, check, chosen = "needs_person", None, None
        if candidate:
            # the cleanest agreeing solution goes to the checker
            agreeing = [s for s in solves if s["canonical"] == candidate]
            chosen = next((s for s in agreeing if not format_problems(s["solution"])), agreeing[0])
            prompt = (f"QUESTION\n{text}\n\nPROPOSED ANSWER: {candidate} (independent solves agree; this is NOT an "
                      f"official key - judge the solution on its own merits)\n\nCANDIDATE SOLUTION\n{chosen['solution']}\n\n"
                      f"Candidate final answer: {chosen['final_answer']}")
            chk, cst = call(checker, prompt, CHECKER_SCHEMA, work, figure)
            calls.append({"stage": "check", **cst})
            check = chk or {"error": cst.get("error")}
            if chk:
                mismatches, calc_log = check_calculations(chk.get("calculations"))
                check["calc_check"] = calc_log
                if mismatches:
                    check.update(verdict="incorrect", issues=list(chk.get("issues") or []) + mismatches)
                if check["verdict"] == "correct":
                    verdict = "key_found"
    if not any(s["canonical"] for s in solves) and all("error" in s for s in solves):
        verdict = "error"
    result = {
        "ref": q["ref"], "subject": q["subject"], "chapter": q["chapter"], "type": q["type"], "shift": q.get("shift"),
        "has_figure": bool(figure), "verdict": verdict, "key": candidate if verdict == "key_found" else None,
        "votes": dict(votes), "solution": chosen["solution"] if verdict == "key_found" else None,
        "solution_format_ok": not format_problems(chosen["solution"]) if verdict == "key_found" else None,
        "solves": solves, "check": check, "solver_model": solver["model"], "checker_model": checker["model"],
        "calls": calls, "finished_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }
    (out_dir / f"{q['ref']}.json").write_text(json.dumps(result, ensure_ascii=False, indent=1), encoding="utf-8")
    tokens = sum(c.get("input", 0) + c.get("cache_create", 0) + c.get("cache_read", 0) + c.get("output", 0) for c in calls)
    with _lock:
        print(f"  {q['ref']:<24} {q['type']:<14} {'fig' if figure else '   '} votes {dict(votes)} -> {verdict:<12} "
              f"tokens {tokens:,}", flush=True)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--pack", default=str(HOME / "data" / "keyless.jsonl"))
    parser.add_argument("--limit", type=int, default=CONFIG["questions_per_run"])
    parser.add_argument("--shard")
    parser.add_argument("--refs", nargs="*")
    parser.add_argument("--workers", type=int, default=CONFIG["workers"])
    args = parser.parse_args()

    pack = Path(args.pack)
    if not pack.exists():
        raise SystemExit(f"{pack} not found; make it with scripts/answer_sources.py --export-pack")
    questions = [json.loads(line) for line in pack.read_text(encoding="utf-8").splitlines() if line.strip()]
    out_dir = HOME / "data" / "keys"
    out_dir.mkdir(parents=True, exist_ok=True)
    done = {p.stem for p in out_dir.glob("*.json")
            if json.loads(p.read_text(encoding="utf-8")).get("verdict") != "error"}
    todo = [q for q in questions if q["ref"] not in done and in_shard(q["ref"], args.shard)
            and (not args.refs or q["ref"] in args.refs)][:args.limit]
    solver, checker = load_agent("jee-solver"), load_agent("jee-checker")
    print(f"{len(done)} already done; finding keys for {len(todo)} now ({solver['model']}, {args.workers} workers)")

    results, stopped = [], None
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        for future in as_completed([pool.submit(find_one, q, solver, checker, out_dir) for q in todo]):
            try:
                r = future.result()
                if r:
                    results.append(r)
            except UsageLimitReached as e:
                stopped = str(e)[:300]
                _stop.set()
            except Exception as e:
                print(f"  error: {e.__class__.__name__}: {e}", flush=True)
    tokens = sum(c.get("input", 0) + c.get("cache_create", 0) + c.get("cache_read", 0) + c.get("output", 0)
                 for r in results for c in r["calls"])
    print(f"\nThis run: {len(results)} questions, {dict(Counter(r['verdict'] for r in results))}, {tokens:,} tokens "
          f"({tokens // max(1, len(results)):,} per question)")
    if stopped:
        print(f"Stopped early: usage limit reached ({stopped}). The next run continues from here.")


if __name__ == "__main__":
    main()
