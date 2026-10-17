import test from 'node:test'
import assert from 'node:assert/strict'
import { observeFullscreen, MAX_FULLSCREEN_EXITS, requestFullscreen } from '../src/lib/fullscreen.js'

function fakeDocument(fullscreen = false, webkit = false) {
  const doc = new EventTarget()
  const property = webkit ? 'webkitFullscreenElement' : 'fullscreenElement'
  doc[property] = fullscreen ? {} : null
  doc.transition = value => {
    doc[property] = value ? {} : null
    doc.dispatchEvent(new Event('fullscreenchange'))
    doc.dispatchEvent(new Event('webkitfullscreenchange'))
  }
  return doc
}
test('fullscreen counts actual exits once, allows three, and reaches the limit on the fourth', () => {
  const doc = fakeDocument(true), states = []
  const stop = observeFullscreen(state => states.push(state), doc)
  for (let exit = 1; exit <= 4; exit++) {
    doc.transition(false)
    assert.deepEqual(states.at(-1), { exited: true, exitCount: exit })
    assert.equal(states.at(-1).exitCount > MAX_FULLSCREEN_EXITS, exit === 4)
    const length = states.length
    doc.transition(false)
    assert.equal(states.length, length, 'duplicate exit events do not notify again')
    doc.transition(true)
    assert.deepEqual(states.at(-1), { exited: false, exitCount: exit })
  }
  stop()
})
test('unsupported or denied entry is not an exit; WebKit transitions are supported', () => {
  const doc = fakeDocument(false, true), states = []
  const stop = observeFullscreen(state => states.push(state), doc)
  doc.transition(false)
  assert.deepEqual(states, [])
  doc.transition(true); doc.transition(false)
  assert.deepEqual(states.at(-1), { exited: true, exitCount: 1 })
  stop()
})
test('submission cleanup removes listeners and a new attempt starts at zero', () => {
  const doc = fakeDocument(true), previous = [], next = []
  const stop = observeFullscreen(state => previous.push(state), doc)
  doc.transition(false);stop()
  doc.transition(true);doc.transition(false)
  assert.equal(previous.length, 1)
  const stopNext = observeFullscreen(state => next.push(state), doc)
  doc.transition(true);doc.transition(false)
  assert.equal(next.at(-1).exitCount, 1)
  stopNext()
})
test('fullscreen requests safely handle unsupported APIs, rejection and synchronous throws', async () => {
  assert.equal(await requestFullscreen({}), false)
  assert.equal(await requestFullscreen({requestFullscreen: () => Promise.reject(Error('denied'))}), false)
  assert.equal(await requestFullscreen({requestFullscreen: () => {throw Error('denied')}}), false)
})
