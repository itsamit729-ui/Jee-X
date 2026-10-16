import test from 'node:test'
import assert from 'node:assert/strict'
import { INSTRUCTION_SECONDS, instructionSeconds, canEnterTest, testInstructions } from '../src/lib/testPreparation.js'

const startedAt = 100000
const paper = { is_mock: true, title: '2025 · Shift 1', duration_sec: 10800, questions: [{ type: 'single_correct', marks_wrong: 1 }, { type: 'numerical', marks_wrong: 1 }] }
test('preparation keeps the full 90 seconds separate from the exam and waits for both loading and reading', () => {
  assert.equal(INSTRUCTION_SECONDS, 90)
  const session = { startedAt, paper, loading: false, error: '' }
  assert.equal(instructionSeconds(startedAt, startedAt), 90)
  assert.equal(instructionSeconds(startedAt, startedAt + 89999), 1)
  assert.equal(canEnterTest(session, startedAt + 89999), false)
  assert.equal(canEnterTest(session, startedAt + 90000), true)
  assert.equal(canEnterTest({ ...session, loading: true }, startedAt + 100000), false)
  assert.equal(canEnterTest({ ...session, paper: null }, startedAt + 100000), false)
  assert.equal(canEnterTest({ ...session, error: 'Retry required' }, startedAt + 100000), false)
  assert.equal(canEnterTest(null, startedAt + 100000), false)
  assert.equal(instructionSeconds(startedAt, startedAt + 180000), 0)
  assert.equal(paper.duration_sec, 10800)
})
test('instructions use actual paper length and exam-specific marking and sections', () => {
  const jee = testInstructions({ exam: 'jee_main', mock: true }, paper)
  assert.equal(jee.count, 2)
  assert.equal(jee.minutes, 180)
  assert.ok(jee.rules.some(r => r.includes('including numerical')))
  const topic = testInstructions({}, { ...paper, is_mock: false, questions: [{ type: 'numerical', marks_wrong: 0 }] })
  assert.ok(topic.rules.some(r => r.includes('Incorrect numerical answer: 0')))
  const pyq = testInstructions({ pyq: true }, { ...paper, is_mock: false })
  assert.ok(pyq.rules.some(r => r.includes('including numerical')))
  const cet = testInstructions({ exam: 'mht_cet', mock: true }, paper)
  assert.ok(cet.rules.some(r => r.includes('No negative marking')))
  assert.ok(cet.rules.some(r => r.includes('First 90 minutes')))
  assert.ok(!testInstructions({ exam: 'mht_cet' }).rules.some(r => r.includes('First 90 minutes')))
  assert.ok(testInstructions({ exam: 'bitsat' }).rules.some(r => r.includes('+3')))
})
