import test from 'node:test'
import assert from 'node:assert/strict'
import { teacherSection, teacherHref, paperBuildProblem } from '../src/lib/teacherWorkspace.js'

test('teacher deep links preserve reports, legacy builders and a safe overview',()=>{
  assert.equal(teacherSection(new URLSearchParams()),'overview')
  assert.equal(teacherSection(new URLSearchParams('tab=classes')),'classes')
  assert.equal(teacherSection(new URLSearchParams('tab=build')),'papers')
  assert.equal(teacherSection(new URLSearchParams('tab=classes&report=5')),'tests')
  assert.equal(teacherSection(new URLSearchParams('tab=missing')),'overview')
  assert.equal(teacherHref('overview'),'/teacher')
  assert.equal(teacherHref('papers'),'/teacher?tab=papers')
})

test('paper steps prevent empty papers and invalid marking or time settings',()=>{
  const form={title:'Weekly class test',duration_minutes:60,marks_correct:4,marks_wrong:1}
  assert.equal(paperBuildProblem(form,[{}]),'')
  assert.match(paperBuildProblem(form,[]),/Add at least one question/)
  assert.match(paperBuildProblem({...form,title:'  '},[{}]),/title/)
  assert.match(paperBuildProblem({...form,duration_minutes:0},[{}]),/duration/)
  assert.match(paperBuildProblem({...form,duration_minutes:241},[{}]),/duration/)
  assert.match(paperBuildProblem({...form,duration_minutes:1.5},[{}]),/duration/)
  assert.match(paperBuildProblem({...form,marks_correct:NaN},[{}]),/marks/)
  assert.match(paperBuildProblem({...form,marks_wrong:-1},[{}]),/deduction/)
  assert.equal(paperBuildProblem({...form,marks_wrong:0},[{}]),'')
})
