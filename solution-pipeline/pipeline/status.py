"""Progress: questions in the pack, solved, verified, flagged, published, and tokens used.

Usage: python pipeline/status.py [--shard 1/2]
"""

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import in_shard, load_questions, path  # noqa: E402


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--shard")
    args = parser.parse_args()
    pack = [q for q in load_questions() if in_shard(q["ref"], args.shard)]
    refs = {q["ref"] for q in pack}
    results = [json.loads(f.read_text(encoding="utf-8")) for f in path("results_dir").glob("*.json")]
    results = [r for r in results if r["ref"] in refs]
    ledger = path("published_ledger")
    published = {json.loads(l)["ref"] for l in ledger.read_text(encoding="utf-8").splitlines() if l.strip()} \
        if ledger.exists() else set()
    verdicts = Counter(r["verdict"] for r in results)
    calls = [c for r in results for c in r["calls"]]
    tokens = sum(c.get("input", 0) + c.get("cache_create", 0) + c.get("cache_read", 0) + c.get("output", 0) for c in calls)
    by_subject = Counter((r["subject"], r["verdict"]) for r in results)
    print(f"pack: {len(pack)} questions (shard {args.shard or 'all'}) | solved: {len(results)} | "
          f"remaining: {len(pack) - len(results)}")
    print(f"verdicts: {dict(verdicts)}")
    print(f"published: {len(published & refs)}")
    print(f"tokens: {tokens:,} total, {tokens // max(1, len(results)):,} per question")
    for subject in sorted({s for s, _ in by_subject}):
        print(f"  {subject:<12} " + ", ".join(f"{v}: {n}" for (s, v), n in sorted(by_subject.items()) if s == subject))


if __name__ == "__main__":
    main()
