// Only public catalog data survives reloads. Student data stays in memory.
const PREFIX = 'jee-cache:v1:'
const values = new Map()
const pending = new Map()
let generation = 0
let identity = null

export function cachePolicy(path) {
  if (/^\/api\/subjects(?:\/[^/]+\/chapters)?$/.test(path)) return { ttl: 300_000, persist: true }
  if (/^\/api\/(me|test-attempts(?:\/dashboard)?|ranking\/me|rewards)$/.test(path)) return { ttl: 30_000 }
  return null // Never cache auth, admin, live exams, daily assignments or mutations.
}
function storage() { try { return globalThis.sessionStorage } catch { return null } }
export function invalidateCache(clearPublic = true) {
  generation++
  for (const [key, entry] of values) {
    if (clearPublic || !entry.persist) values.delete(key)
  }
  pending.clear()
  if (!clearPublic) return
  try {
    const store = storage()
    for (let i = (store?.length || 0) - 1; i >= 0; i--) {
      const key = store.key(i)
      if (key?.startsWith(PREFIX)) store.removeItem(key)
    }
  } catch { /* Storage is optional. */ }
}
export function setCacheIdentity(next) {
  if (identity !== next) { identity = next; invalidateCache(false) }
}
export async function cachedRead(key, policy, fetcher) {
  let entry = values.get(key)
  if (!entry && policy?.persist) {
    try { entry = JSON.parse(storage()?.getItem(PREFIX + key) || 'null') } catch { /* Ignore corrupt storage. */ }
  }
  if (policy && entry && Number.isFinite(entry.expires) && entry.expires > Date.now()) return structuredClone(entry.data)
  if (!pending.has(key)) {
    const version = generation
    const task = Promise.resolve().then(fetcher).then(data => {
      if (policy && version === generation) {
        const next = { data, expires: Date.now() + policy.ttl, persist: Boolean(policy.persist) }
        if (values.size >= 80) values.delete(values.keys().next().value)
        values.set(key, next)
        if (policy.persist) { try { storage()?.setItem(PREFIX + key, JSON.stringify(next)) } catch { /* Full/disabled storage. */ } }
      }
      return data
    }).finally(() => { if (pending.get(key) === task) pending.delete(key) })
    pending.set(key, task)
  }
  return structuredClone(await pending.get(key))
}
