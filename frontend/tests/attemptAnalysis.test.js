import test from 'node:test'
import assert from 'node:assert/strict'
import fs from 'node:fs'
import path from 'node:path'
import { fileURLToPath } from 'node:url'
import Module from 'node:module'
import { buildSync } from 'esbuild'
import { filterQuestions, yourAnswer, correctAnswer, splitChapters, chartChapters, attemptKind, nextTestPath, isSlow, isRushed,
  practiceChapterPath, buddyResult, changeSincePrevious } from '../src/lib/attemptAnalysis.js'

const filename = fileURLToPath(import.meta.url)
const root = path.resolve(path.dirname(filename), '..')
const output = buildSync({
  stdin: { contents: `import React from 'react';import {renderToStaticMarkup} from 'react-dom/server';import {MemoryRouter} from 'react-router-dom';import AttemptReport from './src/components/AttemptReport.jsx';import {SummaryOnly} from './src/pages/AttemptAnalysis.jsx';
    export const report=(data,tab)=>renderToStaticMarkup(<MemoryRouter initialEntries={['/results/9'+(tab&&tab!=='overview'?'?tab='+tab:'')]}><AttemptReport data={data}/></MemoryRouter>);
    export const summary=data=>renderToStaticMarkup(<SummaryOnly data={data}/>);`, resolveDir: root, loader: 'jsx' },
  bundle: true, write: false, platform: 'node', format: 'cjs', jsx: 'automatic',
  external: ['react', 'react-dom/server', 'react-router-dom', 'recharts', 'lucide-react'], loader: { '.css': 'empty' },
  define: { 'import.meta.env': '{}' },
}).outputFiles[0].text
const compiled = new Module(filename)
compiled.paths = Module._nodeModulePaths(path.dirname(filename))
compiled._compile(output, filename)
const { report, summary } = compiled.exports

const option = (id, label) => ({ id, label, content: `Option ${label}` })
const question = (over) => ({
  position: 1, question_id: 1, ref: 'Q1', type: 'single_correct', subject_code: 'PHY', chapter: 'Kinematics',
  stem: 'Stem', passage: null, assets: [], options: [option(1, 'A'), option(2, 'B')], selected_option_ids: [2],
  numeric_answer: null, correct_option_ids: [1], answer_min: null, answer_max: null, outcome: 'wrong',
  marks_awarded: -1, marks_correct: 4, time_taken_sec: 200, expected_time_sec: 90, solution: 'Because.', ...over,
})
const questions = [
  question({}),
  question({ position: 2, question_id: 2, outcome: 'correct', selected_option_ids: [1], marks_awarded: 4, time_taken_sec: 60 }),
  question({ position: 3, question_id: 3, type: 'numerical', options: [], selected_option_ids: [], correct_option_ids: [],
    outcome: 'skipped', marks_awarded: 0, time_taken_sec: 0, answer_min: 2, answer_max: 2.5, chapter: 'Optics' }),
  question({ position: 4, question_id: 4, time_taken_sec: 20, chapter: 'Optics' }),
]
const bucket = (over) => ({ correct: 1, wrong: 1, skipped: 1, total: 3, marks: 3, max_marks: 12, time_sec: 260, accuracy: 50, ...over })
const data = {
  detail_available: true,
  meta: { attempt_id: 9, title: 'Physics practice', kind: 'chapter', pattern: 'jee_main', is_mock: false, duration_sec: 900, submitted_at: '2026-10-01T10:00:00Z' },
  summary: { score: 3, max_score: 12, total_questions: 3, correct: 1, wrong: 1, skipped: 1, accuracy: 50, time_sec: 260, marks_lost: 2 },
  subjects: [{ code: 'PHY', name: 'Physics', ...bucket() }],
  chapters: [{ chapter_id: 1, name: 'Kinematics', subject_code: 'PHY', ...bucket({ skipped: 0, total: 2, marks: 3, max_marks: 8 }) },
    { chapter_id: 2, name: 'Optics', subject_code: 'PHY', ...bucket({ correct: 0, wrong: 1, total: 2, marks: -1, max_marks: 8, accuracy: 0 }) },
    { chapter_id: 3, name: 'Waves', subject_code: 'PHY', ...bucket({ correct: 1, wrong: 0, skipped: 0, total: 1, marks: 4, max_marks: 4, accuracy: 100 }) }],
  questions,
}

test('question filters, answers and chapter grouping', () => {
  assert.deepEqual(filterQuestions(questions, 'wrong').map(q => q.question_id), [1, 4])
  assert.deepEqual(filterQuestions(questions, 'rushed').map(q => q.question_id), [4])
  assert.equal(isRushed(questions[0]), false)
  assert.deepEqual(filterQuestions(questions, 'skipped').map(q => q.question_id), [3])
  assert.deepEqual(filterQuestions(questions, 'slow').map(q => q.question_id), [1])
  assert.equal(filterQuestions(questions, 'all').length, 4)
  assert.equal(isSlow({ ...questions[0], expected_time_sec: 0 }), false)
  assert.equal(isSlow(questions[2]), false)
  assert.equal(yourAnswer(questions[0]), 'B')
  assert.equal(correctAnswer(questions[0]), 'A')
  assert.equal(yourAnswer(questions[2]), '–')
  assert.equal(correctAnswer(questions[2]), '2 to 2.5')
  assert.equal(correctAnswer({ ...questions[2], answer_max: 2 }), '2')
  const { weak, strong, tooFew } = splitChapters(data.chapters)
  assert.deepEqual(weak.map(c => c.name), ['Optics'])
  assert.deepEqual(strong.map(c => c.name), ['Kinematics'])
  assert.deepEqual(tooFew.map(c => c.name), ['Waves'])
  assert.deepEqual(chartChapters(data.chapters, 2).map(c => c.name), ['Optics', 'Kinematics'])
})

test('links to practice, the AI Buddy and the previous attempt', () => {
  assert.equal(practiceChapterPath(data.chapters[1]), '/practice?subject=PHY&chapter=2')
  assert.deepEqual(buddyResult(data), { score: 3, maxScore: 12, correct: 1, incorrect: 1, unattempted: 1,
    chapterScores: { Kinematics: { correct: 1, total: 2 }, Optics: { correct: 0, total: 2 }, Waves: { correct: 1, total: 1 } } })
  assert.equal(changeSincePrevious(data.meta, data.summary), null)
  assert.deepEqual(changeSincePrevious({ previous: { score: 5, accuracy: 40 } }, data.summary), { score: -2, accuracy: 10 })
})

test('attempt labels and next test paths follow the test type', () => {
  assert.equal(attemptKind({ title: 'JEE Main full mock', kind: 'mock', pattern: 'jee_main', is_mock: true }), 'Full mock')
  assert.equal(attemptKind({ title: 'Roadmap baseline assessment', kind: 'mock', pattern: 'jee_main', is_mock: true }), 'Baseline')
  assert.equal(attemptKind({ title: 'x', kind: 'mock', pattern: 'mht_cet', is_mock: true }), 'Shift mock')
  assert.equal(attemptKind({ title: 'x', kind: 'chapter', pattern: 'bitsat', is_mock: false }), 'PYQ practice')
  assert.equal(attemptKind({ title: 'x', kind: 'daily', pattern: 'jee_main' }), 'Daily question')
  assert.equal(attemptKind({ title: 'x', kind: 'chapter', pattern: 'jee_main' }), 'Practice')
  assert.equal(nextTestPath({ title: 'JEE Main full mock', kind: 'mock', pattern: 'jee_main', is_mock: true }), '/practice?mock=1')
  assert.equal(nextTestPath({ title: 'x', kind: 'mock', pattern: 'mht_cet', is_mock: true }), '/pyq?exam=mht_cet')
  assert.equal(nextTestPath({ title: 'x', kind: 'chapter', pattern: 'jee_main' }), '/practice')
})

test('report renders score, tabs and the question review with filters', () => {
  const overview = report(data, 'overview')
  assert.match(overview, /3<small>\/ 12<\/small>/)
  assert.match(overview, /1 correct, 1 wrong, 1 skipped/)
  assert.match(overview, /Time used of 15/)
  const chapters = report(data, 'chapters')
  assert.match(chapters, /Needs work[\s\S]*Optics[\s\S]*Practice this chapter[\s\S]*Strong[\s\S]*Kinematics/)
  assert.match(chapters, /href="\/practice\?subject=PHY&amp;chapter=2"/)
  assert.match(chapters, /Too few questions to judge: Waves \(1\/1\)/)
  assert.match(overview, /Marks lost to wrong answers/)
  const review = report(data, 'questions')
  assert.match(review, /Wrong <span class="faint">2<\/span>/)
  assert.match(review, /Rushed <span class="faint">1<\/span>/)
  assert.match(review, /20s \(rushed\)/)
  assert.match(review, /Slow <span class="faint">1<\/span>/)
  assert.match(review, /yours B · answer A · 200s \(slow\)/)
  assert.match(review, /answer 2 to 2.5/)
  // Closed rows defer the stem and solution.
  assert.doesNotMatch(review, /Because\./)
})

test('legacy attempts show their totals only', () => {
  const html = summary({ summary: { score: 40, total_questions: 75, accuracy: 50 }, subject_breakdown: { Physics: { correct: 10, total: 25 } } })
  assert.match(html, /40<small>\/ 75 correct<\/small>/)
  assert.match(html, /Physics[\s\S]*10\/25/)
  assert.match(html, /only its totals are available/)
})

test('results open from the dashboard and the result screen without replacing existing routes', () => {
  const app = fs.readFileSync(path.join(root, 'src/App.jsx'), 'utf8')
  assert.match(app, /path="\/results\/:attemptId" element=\{<ProtectedRoute><AttemptAnalysis \/><\/ProtectedRoute>\}/)
  assert.match(app, /path="\/buddy"/)
  const test = fs.readFileSync(path.join(root, 'src/pages/SubjectTest.jsx'), 'utf8')
  assert.match(test, /to=\{`\/results\/\$\{result\.attempt_id\}`\}>See full analysis/)
  const dashboard = fs.readFileSync(path.join(root, 'src/pages/Dashboard.jsx'), 'utf8')
  assert.match(dashboard, /to=\{`\/results\/\$\{row\.id\}`\}/)
})
