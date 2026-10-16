#!/usr/bin/env bash
# One key-mode round for 2025 + 2024, then save the keys and move answered questions into the chapter files.
# Run from the repo root (the worktree). Stops at the usage limit; run again after it resets.
set -u
SP="$(cd .. && pwd)"
export PYTHONIOENCODING=utf-8 PYTHONUNBUFFERED=1
(cd solution-pipeline && python pipeline/find_keys.py --limit 1000 --workers "${WORKERS:-1}" >> data/logs/find-keys-2025.log 2>&1)
python scripts/answer_sources.py --year 2025 --pw "$SP/ds/pw2025" --pipeline-keys solution-pipeline/data/keys \
  --nta "$SP/ntakeys/2025-s1.pdf" "$SP/ntakeys/2025-s2.pdf" --apply | tail -2
python scripts/answer_sources.py --year 2024 --grafite "$SP/ds/grafite.csv" --pipeline-keys solution-pipeline/data/keys \
  --nta "$SP/ntakeys/2024-s1.pdf" "$SP/ntakeys/2024-s2.pdf" --apply | tail -2
for y in 2025 2024; do
  python scripts/scrape_pyqs.py --all --min-year $y --max-year $y --recent-only --delay 2.5 \
    > generated/scraped/.reports/promote-$y.log 2>&1
  tail -1 generated/scraped/.reports/promote-$y.log
done
tail -2 solution-pipeline/data/logs/find-keys-2025.log
