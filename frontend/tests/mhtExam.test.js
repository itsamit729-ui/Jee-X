import test from 'node:test'
import assert from 'node:assert/strict'
import { cetPhase, cetCanAnswer, cetStatus } from '../src/lib/mhtExam.js'
test('CET section boundaries lock Physics/Chemistry and unlock Mathematics', () => {
  assert.equal(cetPhase(10800), 'PC')
  assert.equal(cetCanAnswer('MATH', 5401), false)
  assert.equal(cetCanAnswer('CHEM', 5401), true)
  assert.equal(cetPhase(5400), 'MATH')
  assert.equal(cetCanAnswer('PHY', 5400), false)
  assert.equal(cetCanAnswer('MATH', 1), true)
  assert.equal(cetCanAnswer('MATH', 0), false)
  assert.equal(cetPhase(-1), 'DONE')
})
test('palette distinguishes saved marked answers from unanswered review', () => {
  assert.equal(cetStatus(1, {}, {}, {}), 'unvisited')
  assert.equal(cetStatus(1, {}, {1:true}, {}), 'unanswered')
  assert.equal(cetStatus(1, {}, {1:true}, {1:true}), 'review')
  assert.equal(cetStatus(1, {1:{option_ids:[8]}}, {}, {1:true}), 'answered-review')
  assert.equal(cetStatus(1, {1:{option_ids:[8]}}, {}, {}), 'answered')
})
