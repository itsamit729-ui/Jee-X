import { api } from './api.js'

/**
 * Bridges a free-test result across the account signup flow.
 *
 * The free test is taken before the student has an account. If they choose
 * to save it, we stash the result in localStorage, send them through signup
 * signup, and once they land back in the app (authenticated, onboarded),
 * Dashboard picks the pending result up and POSTs it to the backend.
 *
 * This runs in the student's own browser as part of a real deployed app —
 * not inside an in-chat preview — so localStorage is a safe, normal choice
 * here (unlike inside Claude.ai's Artifacts sandbox, where it's unsupported).
 */

const KEY = 'jee-edge.pendingFreeTestResult'
const MAX_AGE_MS = 30 * 60 * 1000 // stale after 30 minutes — don't resurrect an old test

export function savePendingFreeTest(result) {
  try {
    localStorage.setItem(KEY, JSON.stringify({ ...result, savedAt: Date.now() }))
  } catch {
    // localStorage can fail (private browsing, storage full) — non-fatal, just skip saving.
  }
}

export function readPendingFreeTest() {
  try {
    const raw = localStorage.getItem(KEY)
    if (!raw) return null
    const parsed = JSON.parse(raw)
    if (Date.now() - parsed.savedAt > MAX_AGE_MS) {
      localStorage.removeItem(KEY)
      return null
    }
    return parsed
  } catch {
    return null
  }
}

export function clearPendingFreeTest() {
  try {
    localStorage.removeItem(KEY)
  } catch {
    // ignore
  }
}

// Coalesce effect replays and quick return visits so a pending result is sent once.
let syncing = null
export function syncPendingFreeTest() {
  if (syncing) return syncing
  const pending = readPendingFreeTest()
  if (!pending) return Promise.resolve()
  const { savedAt, ...payload } = pending
  syncing = api.submitTestAttempt(payload).then(() => {
    if (readPendingFreeTest()?.savedAt === savedAt) clearPendingFreeTest()
  }).catch(() => {
    // Keep the result for a later visit if offline or not onboarded yet.
  }).finally(() => { syncing = null })
  return syncing
}
