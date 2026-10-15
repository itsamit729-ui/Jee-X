import test from 'node:test'
import assert from 'node:assert/strict'
import path from 'node:path'
import { fileURLToPath } from 'node:url'
import Module from 'node:module'
import { buildSync } from 'esbuild'
import { PYQ_EXAMS, archiveReturn, paperMarks, practiceOffset, pyqExam, resultAnswer } from '../src/lib/pyqArchive.js'

test('archive supports JEE Main and keeps exam-specific paper marks separate', () => {
  assert.ok(PYQ_EXAMS.some(([code]) => code === 'jee_main'))
  assert.equal(pyqExam('jee_main'), 'jee_main')
  assert.equal(pyqExam('invalid'), 'mht_cet')
  const subjects = [{ code: 'PHY', available: 25 }, { code: 'CHEM', available: 25 }, { code: 'MATH', available: 25 }]
  assert.equal(paperMarks('jee_main', subjects), 300)
  assert.equal(paperMarks('mht_cet', subjects), 100)
  assert.equal(paperMarks('bitsat', subjects), 225)
})

test('practice return preserves the exam, subject and set without admitting external URLs', () => {
  const params = new URLSearchParams({ pyq: 'jee_main', year: '2026', subject: 'PHY', view: 'practice', offset: '30', count: '30', returnTo: 'https://other.test' })
  const returned = new URL(archiveReturn(params), 'https://jeeedge.in')
  assert.equal(returned.pathname, '/pyq')
  for (const [key, value] of [['exam', 'jee_main'], ['year', '2026'], ['offset', '30'], ['count', '30'], ['subject', 'PHY'], ['view', 'practice']]) assert.equal(returned.searchParams.get(key), value)
  assert.equal(returned.searchParams.has('returnTo'), false)
  for (const value of ['Infinity', 'NaN', '-1', '3.5', '2000001']) assert.equal(practiceOffset(value), 0)
  assert.equal(practiceOffset('30'), 30)
})

test('numerical results display zero and accepted ranges rather than hiding the answer key', () => {
  const question = { type: 'numerical', options: [] }
  assert.equal(resultAnswer(question, { answer_min: 0, answer_max: 0 }), '0')
  assert.equal(resultAnswer(question, { answer_min: 4.9, answer_max: 5.1 }), '4.9 to 5.1')
  assert.equal(resultAnswer(question, {}), 'See solution')
  assert.equal(resultAnswer({ type: 'single_correct', options: [{ id: 5, label: 'B' }] }, { correct_option_ids: [5] }), 'B')
})

const filename = fileURLToPath(import.meta.url)
const output = buildSync({
  stdin: { contents: `import React from 'react';import {renderToStaticMarkup} from 'react-dom/server';import {MemoryRouter} from 'react-router-dom';import {AuthProvider} from './src/auth/AuthContext.jsx';import PYQs from './src/pages/PYQs.jsx';export const page=()=>renderToStaticMarkup(<MemoryRouter initialEntries={['/pyq?exam=jee_main']}><AuthProvider><PYQs/></AuthProvider></MemoryRouter>);`, resolveDir: path.resolve(path.dirname(filename), '..'), loader: 'jsx' },
  bundle: true, write: false, platform: 'node', format: 'cjs', jsx: 'automatic', loader: { '.css': 'empty' }, define: { 'import.meta.env': '{}' }, external: ['react', 'react-dom/server', 'react-router-dom'],
}).outputFiles[0].text
const compiled = new Module(filename)
compiled.paths = Module._nodeModulePaths(path.dirname(filename))
compiled._compile(output, filename)
test('JEE Main section is visible and selected alongside both existing exams', () => {
  const html = compiled.exports.page()
  assert.match(html, /aria-pressed="true"[^>]*>.*?<strong>JEE Main<\/strong>/)
  assert.match(html, /MHT-CET/)
  assert.match(html, /BITSAT/)
  assert.match(html, /MCQ \+ Numerical/)
  assert.match(html, /including numerical questions/)
  assert.match(html, /Loading the archive/)
})
