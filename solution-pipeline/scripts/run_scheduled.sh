#!/usr/bin/env bash
# Runs one batch (macOS/Linux). Schedule it every 5 hours with cron, e.g. `crontab -e`:
#   7 */5 * * *  /path/to/solution-pipeline/scripts/run_scheduled.sh 2/2
# The optional argument is the shard ("1/2" on one laptop, "2/2" on the other).
set -u
cd "$(dirname "$0")/.."
mkdir -p data/logs
log="data/logs/run-$(date +%Y%m%d-%H%M).log"
export PYTHONIOENCODING=utf-8 PYTHONUNBUFFERED=1
export PATH="$HOME/.local/bin:/opt/homebrew/bin:/usr/local/bin:$PATH"   # so cron finds `claude` and python
if [ -n "${1:-}" ]; then
  python3 pipeline/run_batch.py --shard "$1" >"$log" 2>&1
else
  python3 pipeline/run_batch.py >"$log" 2>&1
fi
python3 pipeline/status.py >>"$log" 2>&1
