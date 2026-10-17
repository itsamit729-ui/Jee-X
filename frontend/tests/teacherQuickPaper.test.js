import test from 'node:test'
import assert from 'node:assert/strict'
import path from 'node:path'
import {fileURLToPath} from 'node:url'
import Module from 'node:module'
import {buildSync} from 'esbuild'
import {defaultMarking,quickPaperBody,quickPaperProblem} from '../src/lib/teacherQuickPaper.js'

const form={exam:'jee_main',scope:'PHY',count:2,duration:10,method:'topics',chapters:[7],reference:'',fullPaper:false,
  level:'balanced',source:'all',type:'',sets:false,title:'',instructions:'',correct:'',wrong:''}

test('compact manual request has explicit filters and leaves automatic marking and title to server',()=>{
  const body=quickPaperBody(form,null,'request-key')
  assert.equal(body.count,2)
  assert.equal(body.duration_minutes,10)
  assert.deepEqual(body.subjects,['PHY'])
  assert.deepEqual(body.chapter_ids,[7])
  assert.equal(body.question_type,null)
  assert.equal(body.selection,'topics')
  assert.equal(body.request_key,'request-key')
  assert.ok(!('title' in body)&&!('marks_correct' in body)&&!('marks_wrong' in body)&&!('year' in body))
  assert.equal(quickPaperBody({...form,correct:'2',wrong:'0'},null,'x').marks_wrong,0)
})

test('a full past paper clears stale scope and type filters and preserves a null shift',()=>{
  const reference={year:2024,shift:null,count:75}
  const body=quickPaperBody({...form,method:'reference',fullPaper:true,type:'single_correct',count:''},reference,'x')
  assert.equal(body.selection,'exact')
  assert.equal(body.source,'pyq')
  assert.equal(body.subjects,null)
  assert.equal(body.question_type,null)
  assert.deepEqual(body.chapter_ids,[])
  assert.equal(body.shift,null)
  assert.equal(body.count,30)
  const subset=quickPaperBody({...form,method:'reference'},reference,'x')
  assert.equal(subset.selection,'from_paper')
  assert.deepEqual(subset.subjects,['PHY'])
})

test('invalid sizes, missing reference and marking are clear before saving',()=>{
  assert.equal(quickPaperProblem(form,null),'')
  assert.match(quickPaperProblem({...form,count:0},null),/1 and 200/)
  assert.match(quickPaperProblem({...form,duration:241},null),/duration/)
  assert.match(quickPaperProblem({...form,method:'reference'},null),/past paper/)
  assert.match(quickPaperProblem({...form,wrong:-1},null),/deduction/)
  assert.match(quickPaperProblem({...form,title:'a'},null),/title/)
  assert.equal(quickPaperProblem({...form,method:'reference',fullPaper:true,count:0},{year:2024,shift:null}),'')
  assert.deepEqual(defaultMarking('mht_cet','MATH'),{correct:2,wrong:0})
  assert.deepEqual(defaultMarking('bitsat','all'),{correct:3,wrong:1})
})

const filename=fileURLToPath(import.meta.url)
const output=buildSync({stdin:{contents:`import React from 'react';import {renderToStaticMarkup} from 'react-dom/server';import TeacherQuickPaper from './src/components/classroom/TeacherQuickPaper.jsx';import TeacherPaperDownloads from './src/components/classroom/TeacherPaperDownloads.jsx';
export const entry=renderToStaticMarkup(<TeacherQuickPaper references={{data:{papers:[]},loading:false}} onCreated={()=>{}} onOpen={()=>{}} onAdvanced={()=>{}} onBusy={()=>{}}/>);
export const ready=renderToStaticMarkup(<TeacherPaperDownloads result={{paper:{id:1,title:'Sample test',questions:[{},{}],sets_enabled:true,settings:{duration_minutes:10,marks_correct:4,marks_wrong:1}},downloads:[{variant:'A',omr:'a'},{variant:'B',omr:'b'}]}} onOpen={()=>{}}/>);`,resolveDir:path.resolve(path.dirname(filename),'..'),loader:'jsx'},bundle:true,write:false,platform:'node',format:'cjs',jsx:'automatic',external:['react','react-dom/server'],loader:{'.css':'empty'},logLevel:'silent'}).outputFiles[0].text
const compiled=new Module(filename);compiled.paths=Module._nodeModulePaths(path.dirname(filename));compiled._compile(output,filename)

test('manual entry has a single create action, chapter search, presets and collapsed extra options',()=>{
  const {entry}=compiled.exports
  assert.match(entry,/A few choices/)
  assert.match(entry,/Create paper &amp; OMR/)
  assert.match(entry,/Type a chapter/)
  assert.match(entry,/Quick quiz/)
  assert.match(entry,/Choose questions myself/)
  assert.match(entry,/<details class="qp-options">/)
  assert.doesNotMatch(entry,/Describe with AI|chat|ai-paper|<select multiple|STEP 1 OF 3/)
  assert.equal((entry.match(/type="submit"/g)||[]).length,1)
})

test('completion immediately exposes question paper and OMR downloads for each saved set',()=>{
  const {ready}=compiled.exports
  assert.match(ready,/Your paper is ready/)
  assert.equal((ready.match(/Download paper PDF/g)||[]).length,2)
  assert.equal((ready.match(/Download OMR PDF/g)||[]).length,2)
  assert.match(ready,/Open paper &amp; answer key/)
  assert.doesNotMatch(ready,/confirmation|<input|<select/)
})
