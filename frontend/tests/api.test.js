import { test, beforeEach } from 'node:test'
import assert from 'node:assert/strict'
import { request } from '../src/lib/api.js'
import { invalidateCache, setCacheIdentity, cachedRead } from '../src/lib/requestCache.js'

const stored = new Map()
globalThis.sessionStorage = {
  getItem: key => stored.get(key) || null,
  setItem: (key, value) => stored.set(key, value),
  removeItem: key => stored.delete(key),
  key: index => [...stored.keys()][index],
  get length() { return stored.size },
}
globalThis.window = new EventTarget()
const json = (value, status = 200) => new Response(JSON.stringify(value), { status })
beforeEach(() => { invalidateCache(); setCacheIdentity(null) })

test('concurrent reads and repeat visits use one request and independent objects', async () => {
  let calls = 0
  globalThis.fetch = async () => { calls++; return json({ profile: { name: 'A' } }) }
  const [a, b] = await Promise.all([request('/api/me'), request('/api/me')])
  a.profile.name = 'changed'
  assert.equal(b.profile.name, 'A')
  assert.equal((await request('/api/me')).profile.name, 'A')
  assert.equal(calls, 1)
  assert.equal(stored.size, 0)
})
test('only public catalog is persisted; sessions and live exams are always fetched', async () => {
  let calls = 0
  globalThis.fetch = async () => { calls++; return json({ ok: true }) }
  await request('/api/subjects'); await request('/api/subjects')
  assert.equal(calls, 1); assert.equal(stored.size, 1)
  for (const path of ['/api/auth/session', '/api/ranking/entries/1', '/api/daily-question', '/api/admin/dashboard']) {
    await request(path); await request(path)
  }
  assert.equal(calls, 9); assert.equal(stored.size, 1)
})
test('successful mutations and account switches invalidate student data', async () => {
  let calls = 0
  globalThis.fetch = async () => json({ version: ++calls })
  await request('/api/me')
  await request('/api/profile', { method: 'PATCH', body: {} })
  assert.equal((await request('/api/me')).version, 3)
  setCacheIdentity('other-student')
  assert.equal((await request('/api/me')).version, 4)
})
test('old in-flight reads cannot repopulate invalidated cache', async () => {
  let finish
  const old = cachedRead('key', { ttl: 1000 }, () => new Promise(r => { finish = r }))
  await Promise.resolve()
  invalidateCache()
  const fresh = await cachedRead('key', { ttl: 1000 }, async () => 'new')
  finish('old'); await old
  assert.equal(fresh, 'new')
  assert.equal(await cachedRead('key', { ttl: 1000 }, async () => 'incorrect'), 'new')
})
test('expired entries and rejected requests are fetched again', async () => {
  let calls = 0
  const load = async () => ++calls
  await cachedRead('expired', { ttl: -1 }, load)
  await cachedRead('expired', { ttl: -1 }, load)
  assert.equal(calls, 2)
  await assert.rejects(cachedRead('failed', { ttl: 1000 }, async () => { throw Error('offline') }))
  assert.equal(await cachedRead('failed', { ttl: 1000 }, async () => 'recovered'), 'recovered')
})
test('temporary GET failures retry once; writes never retry', async () => {
  let calls = 0
  globalThis.fetch = async () => ++calls === 1 ? json({}, 503) : json({ ok: true })
  assert.equal((await request('/api/me')).ok, true); assert.equal(calls, 2)
  calls = 0
  globalThis.fetch = async () => { calls++; return json({}, 503) }
  await assert.rejects(request('/api/test-attempts', { method: 'POST', body: {} }))
  assert.equal(calls, 1)
})
test('401 is not retried and requests time out instead of hanging', async () => {
  let calls = 0, expired = 0
  const listener = () => expired++
  window.addEventListener('jee-session-expired', listener)
  globalThis.fetch = async () => { calls++; return json({}, 401) }
  await assert.rejects(request('/api/me'), { status: 401 })
  assert.equal(calls, 1); assert.equal(expired, 1)
  window.removeEventListener('jee-session-expired', listener)
  globalThis.fetch = (_, { signal }) => new Promise((_, reject) => {
    signal.addEventListener('abort', () => reject(new DOMException('Aborted', 'AbortError')))
  })
  await assert.rejects(request('/api/me', { timeoutMs: 5 }), /taking too long/)
})
test('corrupt or unavailable browser storage does not break reads', async () => {
  stored.set('jee-cache:v1:/api/subjects', '{broken')
  globalThis.fetch = async () => json(['physics'])
  assert.deepEqual(await request('/api/subjects'), ['physics'])
  invalidateCache()
  const original = sessionStorage.setItem
  sessionStorage.setItem = () => { throw Error('quota') }
  try { assert.deepEqual(await request('/api/subjects'), ['physics']) }
  finally { sessionStorage.setItem = original }
})
test('account identity changes retain public catalog but remove private memory data', async () => {
  let calls = 0
  globalThis.fetch = async () => json({ version: ++calls })
  await request('/api/subjects')
  await request('/api/me')
  setCacheIdentity('next-account')
  assert.equal(stored.size, 1)
  assert.equal((await request('/api/subjects')).version, 1)
  assert.equal((await request('/api/me')).version, 3)
})
