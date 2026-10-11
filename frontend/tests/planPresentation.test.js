import assert from 'node:assert/strict'
import test from 'node:test'
import { evidenceLabel, goalPayload, planGoal, planTopics, topicPracticeOptions } from '../src/lib/planPresentation.js'
import { subjectTestBuilderService } from '../src/lib/subjectTests.js'

const topics = [
  { topic_id: 71, chapter_id: 9, subject: 'PHY', week: 1 },
  { topic_id: 82, chapter_id: 10, subject: 'CHEM', week: 1 },
  { topic_id: 73, chapter_id: 9, subject: 'PHY', week: 2 },
]

test('chapter links retain backend priority and never substitute an unrelated topic', () => {
  assert.deepEqual(planTopics({ topics }, 'PHY', '9').map(topic => topic.topic_id), [71, 73])
  assert.deepEqual(planTopics({ topics }, 'CHEM', '9'), [])
  assert.deepEqual(planTopics(null), [])
})

test('a selected later-week topic launches a 15-minute exact-topic test, not an assessment', async () => {
  const original = globalThis.fetch
  let sent
  globalThis.fetch = async (path, options) => {
    sent = { path, method: options.method, body: JSON.parse(options.body) }
    return { ok: true, status: 201, json: async () => ({ attempt_id: 4, questions: [] }) }
  }
  try {
    await subjectTestBuilderService.start(topicPracticeOptions(topics[2]))
    assert.equal(sent.path, '/api/subject-tests')
    assert.equal(sent.method, 'POST')
    assert.deepEqual(sent.body, { assessment: false, subject_code: 'PHY', chapter_id: 9, topic_id: 73, count: 10, mode: 'recommended', duration_minutes: 15 })
  } finally { globalThis.fetch = original }
})

test('changing from college goals to marks clears college IDs and preserves rank-list inputs', () => {
  const admission = { category: 'SC', category_rank: 3100, crl: 56000, state: 'Maharashtra', pwd: false }
  const result = goalPayload({ goal_type: 'marks', target_marks: '180', available_hours: '', college_choices: [3, 5], admission })
  assert.deepEqual(result, { goal_type: 'marks', target_marks: 180, available_hours: null, college_choices: [], admission })
  assert.equal(result.admission.category_rank, 3100)
  assert.equal(result.admission.crl, 56000)
})

test('changing to college goals clears marks and retains the chosen weekly time', () => {
  const result = goalPayload({ goal_type: 'colleges', target_marks: 180, available_hours: '4', college_choices: [3, 5], admission: {} })
  assert.equal(result.target_marks, null)
  assert.equal(result.available_hours, 4)
  assert.deepEqual(result.college_choices, [3, 5])
})

test('a default target is labelled suggested until the student saves it', () => {
  const settings = { goal_type: 'marks', target_marks: 150 }
  assert.equal(planGoal(settings, false).label, 'Suggested goal')
  assert.equal(planGoal(settings, true).label, 'Your goal')
  assert.equal(planGoal({ goal_type: 'colleges', choices: [{ id: 2 }] }, true).value, '1 college choice')
})

test('zero accuracy remains evidence instead of being presented as missing history', () => {
  assert.match(evidenceLabel({ accuracy: 0, fresh_answers: 8, study_days: 2 }), /0% correct · 8 fresh answers · 2 study days/)
  assert.match(evidenceLabel({ accuracy: null }), /No fresh answers yet/)
})
