import test from 'node:test'
import assert from 'node:assert/strict'
import { assignmentDeadline } from '../src/lib/assignmentClock.js'

test('assignment countdown uses server time independently of device clock and timezone', () => {
  const deadline = assignmentDeadline('2026-09-28T10:30:00Z', '2026-09-28T15:30:00+05:30', 1000)
  assert.equal(deadline, 1801000)
  assert.equal(assignmentDeadline('2026-09-28T10:00:00Z', '2026-09-28T10:01:00Z', 1000), -59000)
  assert.throws(() => assignmentDeadline('invalid', '2026-09-28T10:00:00Z'), /timer/)
})
