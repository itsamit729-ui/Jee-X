import test from 'node:test'
import assert from 'node:assert/strict'
import { rememberPaperReturn, pendingPaperReturn, clearPaperReturn } from '../src/lib/paperReturn.js'
test('paper selection survives verification and expires or clears after return', () => {
  const data = new Map()
  const storage = { setItem: (k,v) => data.set(k,v), getItem:k => data.get(k), removeItem:k => data.delete(k) }
  const path = '/pyq?exam=mht_cet&year=2025&shift=19+Apr+2025&source=teacher'
  rememberPaperReturn(path, storage, 100)
  assert.equal(pendingPaperReturn(storage, 200), path)
  assert.equal(pendingPaperReturn(storage, 1800101), null)
  rememberPaperReturn('https://other.test', storage, 100)
  assert.equal(pendingPaperReturn(storage, 200), null)
  rememberPaperReturn(path, storage, 100)
  clearPaperReturn(storage)
  assert.equal(pendingPaperReturn(storage, 200), null)
})
