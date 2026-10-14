import test from 'node:test'
import assert from 'node:assert/strict'
import path from 'node:path'
import { fileURLToPath } from 'node:url'
import Module from 'node:module'
import { buildSync } from 'esbuild'

const filename = fileURLToPath(import.meta.url)
const output = buildSync({
  stdin: { contents: `import React from 'react';import {renderToStaticMarkup} from 'react-dom/server';import {MemoryRouter} from 'react-router-dom';import Story,{activityCalendar} from './src/components/StudentProfileStory.jsx';import {LearningSnapshot} from './src/components/ProfileLearning.jsx';
    export {activityCalendar};export const story=profile=>renderToStaticMarkup(<Story profile={profile} onShare={()=>{}}/>);
    export const learning=data=>renderToStaticMarkup(<MemoryRouter><LearningSnapshot data={data}/></MemoryRouter>);`, resolveDir: path.resolve(path.dirname(filename), '..'), loader: 'jsx' },
  bundle: true, write: false, platform: 'node', format: 'cjs', jsx: 'automatic',
  external: ['react', 'react-dom/server', 'react-router-dom'], loader: { '.css': 'empty' }, define: { 'import.meta.env': '{}' },
}).outputFiles[0].text
const compiled = new Module(filename)
compiled.paths = Module._nodeModulePaths(path.dirname(filename))
compiled._compile(output, filename)
const { story, learning, activityCalendar } = compiled.exports
const student = { username: 'student1', display_name: '', bio: '', exam: 'jee_main', target_year: 2027, rank: null, activity: null,
  rating: { rating: null, peak: null, title: 'Unrated', contests: 0, placements_completed: 0, badges: [] } }

test('public student story shows exam goal, accurate placement state, and honest empty states', () => {
  const html = story({ ...student, email: 'private@example.com', dob: '2008-01-01', id: 12345, name: 'Private real name' })
  assert.match(html, /Public student profile/)
  assert.match(html, /JEE Main/)
  assert.match(html, /2027/)
  assert.match(html, /0 of 3 placement contests completed/)
  assert.match(html, /hasn’t added a bio yet/)
  assert.doesNotMatch(html, /private@example|2008-01-01|12345|Private real name|NaN|undefined/)
  assert.doesNotMatch(html, /pp-heatmap/)
})

test('public biography is escaped and finalized milestones reflect actual rating data', () => {
  const html = story({ ...student, display_name: '<script>hello</script>', bio: '<img src=x onerror=alert(1)>',
    rating: { ...student.rating, rating: 1500, peak: 1800, title: 'Achiever', contests: 5, next_tier: { title: 'Scholar' }, points_to_next: 500, badges: [{ title: 'Achiever', minimum: 1500 }] } })
  assert.match(html, /&lt;script&gt;/)
  assert.match(html, /&lt;img/)
  assert.doesNotMatch(html, /<script>|<img src="x"/)
  assert.match(html, /500 rating points to Scholar/)
  assert.match(html, /Current tier/)
  assert.match(html, /1800/)
})

test('activity calendar uses the IST day across midnight and includes exactly 182 days', () => {
  const days = activityCalendar(['2026-10-15', '2020-01-01'], new Date('2026-10-14T19:00:00Z'))
  assert.equal(days.length, 182)
  assert.equal(new Set(days.map(d => d.date)).size, 182)
  assert.deepEqual(days.at(-1), { date: '2026-10-15', active: true })
  assert.equal(days.filter(d => d.active).length, 1)
  assert.equal(activityCalendar([], new Date('2026-10-14T18:00:00Z')).at(-1).date, '2026-10-14')
  const html = story({ ...student, activity: { dates: [], current_streak: 0, longest_streak: 0 } })
  assert.equal((html.match(/<time /g) || []).length, 182)
  assert.match(html, /India Standard Time/)
})

test('private learning snapshot gives sample sizes and does not invent accuracy for an empty account', () => {
  const empty = { days: 90, exam: 'jee_main', completed_tests: 0, answered: 0, accuracy: null, subjects: [] }
  assert.match(learning(empty), /Only|ONLY YOU CAN SEE THIS/)
  assert.match(learning(empty), /Start practising/)
  assert.doesNotMatch(learning(empty), /NaN|undefined|0%/)
  const html = learning({ ...empty, answered: 4, accuracy: 50, subjects: [{ name: 'Physics', accuracy: 50, correct: 2, answered: 4 }] })
  assert.match(html, /2 of 4 answered/)
  assert.match(html, /Early sample/)
  assert.match(html, /aria-valuenow="50"/)
  assert.match(html, /Partial answers count as answered/)
})
