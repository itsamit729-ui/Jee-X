import test from 'node:test'
import assert from 'node:assert/strict'
import { omrReadiness, scheduleError, downloadTeacherFile } from '../src/lib/teacherPaper.js'
const q={question_id:1,type:'single_correct',options:['A','B','C','D'].map((label,i)=>({id:i,label,is_correct:i===0}))}

test('OMR readiness distinguishes mixed formats, malformed labels and ambiguous keys',()=>{
  assert.equal(omrReadiness([]).eligible,false)
  assert.equal(omrReadiness([q]).eligible,true)
  assert.equal(omrReadiness([{...q,type:'multi_correct',options:q.options.map(o=>({...o,is_correct:true}))},{question_id:2,type:'numerical',answer_min:-0.125,answer_max:-0.12,options:[]}]).eligible,true)
  const report=omrReadiness([q,{...q,question_id:2,type:'numerical'},{...q,question_id:3,options:q.options.slice(0,1)}])
  assert.equal(report.eligible,false);assert.equal(report.eligible_count,1)
  assert.deepEqual(report.issues.map(i=>i.number),[2,3])
  assert.equal(omrReadiness([{...q,options:q.options.map(o=>({...o,is_correct:true}))}]).eligible,false)
  assert.equal(omrReadiness([{...q,options:q.options.map(o=>({...o,label:'A'}))}]).eligible,false)
  assert.equal(omrReadiness(Array(201).fill(q)).eligible,false)
})

test('schedule validation handles missing, expired and premature solution dates',()=>{
  const now=Date.parse('2026-10-13T12:00:00Z')
  const schedule={opens_at:'2026-10-13T11:00:00Z',due_at:'2026-10-14T12:00:00Z',solutions_at:'2026-10-14T12:00:00Z'}
  assert.equal(scheduleError(schedule,now),'')
  assert.match(scheduleError({...schedule,opens_at:''},now),/three dates/)
  assert.match(scheduleError({...schedule,due_at:'2026-10-13T10:00:00Z'},now),/future/)
  assert.match(scheduleError({...schedule,solutions_at:'2026-10-14T11:00:00Z'},now),/after the deadline/)
})

test('PDF failures remain readable errors rather than downloads of JSON or HTML',async()=>{
  globalThis.fetch=async()=>new Response(JSON.stringify({detail:'Questions 2 and 3 do not support OMR.'}),{status:422,headers:{'content-type':'application/json'}})
  await assert.rejects(downloadTeacherFile('/api/teacher/papers/1/blank-omr.pdf','paper.pdf'),/Questions 2 and 3/)
  globalThis.fetch=async()=>new Response('<html>Login</html>',{headers:{'content-type':'text/html'}})
  await assert.rejects(downloadTeacherFile('/api/teacher/papers/1/blank-omr.pdf','paper.pdf'),/did not return a download/)
})
