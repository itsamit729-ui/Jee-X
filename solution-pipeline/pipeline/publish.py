"""Publish verified solutions to the database (weekly). Dry run unless --apply.

For every result in data/results with verdict "verified" that is not yet in data/published.jsonl:
  - skip it if the question changed in the database since the pack was exported (content hash differs)
    or its answer key no longer matches the one the solution was verified against
  - set questions.solution, bump questions.version, add a question_revisions row whose change_note
    starts with "verified-solution" (export_questions.py uses it to never re-queue the question)
  - when the repository's question files are next to this folder (../generated/...), write the solution
    into the question's JSON entry too and store that entry's content hash, so a later re-import of
    those files keeps the solution instead of wiping it
Only verified solutions are ever written; flagged questions stay without a solution.

Results from a friend's laptop: copy their data/results/*.json into this data/results first.

Usage:
  python pipeline/publish.py            # dry run: what would be published
  python pipeline/publish.py --apply
"""

import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from sqlalchemy import text  # noqa: E402

from common import HOME, path  # noqa: E402
from db import VERIFIED_NOTE, engine  # noqa: E402

REPO_QUESTION_DIRS = [HOME.parent / "generated"]


def importer_hash(question: dict) -> str:
    """Same as backend/app/importer.py _content_hash."""
    return hashlib.sha256(json.dumps(question, sort_keys=True, ensure_ascii=True).encode("utf-8")).hexdigest()


def repo_index():
    """ref -> chapter file, for the repository's question files (skips dot folders like .cache)."""
    index = {}
    for root in REPO_QUESTION_DIRS:
        if not root.is_dir():
            continue
        for f in root.rglob("*.json"):
            if any(part.startswith(".") for part in f.relative_to(root).parts):
                continue
            try:
                data = json.loads(f.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, UnicodeDecodeError):
                continue
            if isinstance(data, dict) and isinstance(data.get("questions"), list):
                for q in data["questions"]:
                    if isinstance(q, dict) and "ref" in q:
                        index.setdefault(q["ref"], f)
    return index


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()

    ledger = path("published_ledger")
    published = {json.loads(l)["ref"] for l in ledger.read_text(encoding="utf-8").splitlines() if l.strip()} \
        if ledger.exists() else set()
    pack = {}
    if path("questions_file").exists():
        for line in path("questions_file").read_text(encoding="utf-8").splitlines():
            if line.strip():
                q = json.loads(line)
                pack[q["ref"]] = q
    results = []
    for f in sorted(path("results_dir").glob("*.json")):
        r = json.loads(f.read_text(encoding="utf-8"))
        if r["verdict"] == "verified" and r.get("solution") and r["ref"] not in published:
            results.append(r)
    flagged = sum(1 for f in path("results_dir").glob("*.json")
                  if json.loads(f.read_text(encoding="utf-8"))["verdict"] != "verified")
    print(f"{len(results)} verified solutions to publish ({len(published)} published earlier, {flagged} flagged, never published)")
    if not results:
        return

    files = repo_index()
    changed_files = {}
    ok, skipped = [], []
    with engine().connect() as db:
        for r in results:
            row = db.execute(text("SELECT id, type, answer_min, answer_max, content_hash, version FROM questions "
                                  "WHERE ref = :ref"), {"ref": r["ref"]}).mappings().first()
            if not row:
                skipped.append((r["ref"], "not in database"))
                continue
            exported = pack.get(r["ref"])
            if exported and exported.get("content_hash") and exported["content_hash"] != row["content_hash"]:
                skipped.append((r["ref"], "question changed since export; re-export and re-solve"))
                continue
            if row["type"] == "numerical":
                key = str(row["answer_min"] if row["answer_min"] == row["answer_max"] else f"{row['answer_min']} to {row['answer_max']}")
            else:
                key = ",".join(o[0] for o in db.execute(text(
                    "SELECT label FROM question_options WHERE question_id = :id AND is_correct = 1 ORDER BY label"),
                    {"id": row["id"]}).all())
            if str(r["answer_key"]) != key and not (row["type"] == "numerical" and float(r["answer_key"]) == float(row["answer_min"])):
                skipped.append((r["ref"], f"answer key changed ({r['answer_key']} -> {key})"))
                continue
            ok.append((r, row))
    print(f"ready: {len(ok)}, skipped: {len(skipped)}")
    for ref, why in skipped[:20]:
        print(f"  skip {ref}: {why}")
    if not args.apply:
        print("Dry run: nothing written. Add --apply to publish.")
        return

    now = datetime.now(timezone.utc).replace(tzinfo=None)
    done = 0
    with engine().connect() as db:
        for r, row in ok:
            file = files.get(r["ref"])
            entry = None
            if file:
                data = changed_files.get(file) or json.loads(file.read_text(encoding="utf-8"))
                changed_files[file] = data
                entry = next(q for q in data["questions"] if q.get("ref") == r["ref"])
                previous_solution = entry.get("solution", "")
                entry["solution"] = r["solution"]
                new_hash = importer_hash(entry)
                snapshot = entry
            else:
                snapshot = {"ref": r["ref"], "solution": r["solution"], "previous_content_hash": row["content_hash"]}
                new_hash = importer_hash(snapshot)
            version = row["version"] + 1
            note = (f"{VERIFIED_NOTE}: solver={r['solver_model']} checker={r['checker_model']} "
                    f"attempts={len(r['attempts'])} finished={r['finished_at']}")
            try:
                with db.begin():
                    res = db.execute(text("UPDATE questions SET solution = :s, version = :v, content_hash = :h, "
                                          "updated_at = :now WHERE id = :id AND content_hash = :old"),
                                     {"s": r["solution"], "v": version, "h": new_hash, "now": now, "id": row["id"],
                                      "old": row["content_hash"]})
                    if res.rowcount != 1:
                        raise RuntimeError("question changed while publishing")
                    db.execute(text("INSERT INTO question_revisions (question_id, version, content, change_note, created_at) "
                                    "VALUES (:id, :v, :c, :note, :now)"),
                               {"id": row["id"], "v": version, "c": json.dumps(snapshot, ensure_ascii=False),
                                "note": note[:1000], "now": now})
            except RuntimeError as e:
                print(f"  skip {r['ref']}: {e}")
                if file:
                    entry["solution"] = previous_solution  # keep the file in step with the database
                continue
            if file:  # right after the commit, so database and files never disagree for long
                file.write_text(json.dumps(changed_files[file], ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            with open(ledger, "a", encoding="utf-8") as f:
                f.write(json.dumps({"ref": r["ref"], "version": version, "published_at": now.isoformat()}) + "\n")
            done += 1
            if done % 25 == 0:
                print(f"  published {done}/{len(ok)}", flush=True)
    print(f"Published {done} solutions. Updated {len(changed_files)} repository question files "
          f"(commit them so a future re-import keeps the solutions).")


if __name__ == "__main__":
    main()
