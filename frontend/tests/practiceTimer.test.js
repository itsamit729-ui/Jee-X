import { test } from 'node:test'
import assert from 'node:assert/strict'
import { createPracticeTimer } from '../src/lib/practiceTimer.js'
test('question timing accumulates revisits and excludes hidden or unfocused time', () => {
  let now=0; const timer=createPracticeTimer(()=>now)
  timer.activate(1);now=2000;timer.activate(2);now=5000
  timer.activate(2,false);now=100000;assert.equal(timer.seconds(2),3)
  timer.activate(1);now=101000;assert.equal(timer.seconds(1),3)
  timer.pause();now=110000;assert.equal(timer.seconds(1),3)
  timer.reset();assert.equal(timer.seconds(1),0)
})
