// Track visible, focused time; repeated visits accumulate rather than reset.
export function createPracticeTimer(now = () => performance.now()) {
  const totals = new Map()
  let current = null, started = null
  function flush() {
    if (current !== null && started !== null) totals.set(current, (totals.get(current) || 0) + Math.max(0, now() - started))
    started = null
  }
  return {
    activate(id, active = true) { flush(); current = id; if (active) started = now() },
    pause: flush,
    seconds(id) { const elapsed = (totals.get(id) || 0) + (id === current && started !== null ? Math.max(0, now() - started) : 0); return Math.min(86400, Math.round(elapsed / 1000)) },
    reset() { flush(); totals.clear(); current = null },
  }
}
