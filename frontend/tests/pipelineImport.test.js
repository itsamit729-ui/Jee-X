import test from 'node:test'
import assert from 'node:assert/strict'
import {runPipelineImport} from '../src/lib/pipelineImport.js'
const preview={year:2024,digest:'reviewed',eligible:75}
const state=offset=>({digest:'reviewed',year:2024,offset,total:75,finished:offset===75,added:offset,updated:0,unchanged:0,skipped:0,conflicts:0})
const error=status=>Object.assign(new Error('Connection failed'),{status})

test('reload resumes at the server cursor instead of processing the first records again',async()=>{
  const offsets=[],updates=[]
  const result=await runPipelineImport({preview,wait:async()=>{},onProgress:p=>updates.push(p.offset),request:async(path,options)=>{
    if(path.endsWith('/progress'))return state(50)
    offsets.push(options.body.offset);return {progress:state(75)}
  }})
  assert.deepEqual(offsets,[50]);assert.deepEqual(updates,[50,75]);assert.equal(result.added,75)
})

test('lost response after a committed batch checks progress before retry and does not double-count',async()=>{
  const offsets=[],reads=[],waits=[];let saved=0,first=true
  const result=await runPipelineImport({preview,wait:async ms=>waits.push(ms),request:async(path,options)=>{
    if(path.endsWith('/progress')){reads.push(saved);return state(saved)}
    offsets.push(options.body.offset);saved+=25
    if(first){first=false;throw error(502)}
    return {progress:state(saved)}
  }})
  assert.deepEqual(offsets,[0,25,50]);assert.deepEqual(reads,[0,25]);assert.equal(result.added,75);assert.equal(waits.length,1)
})

test('a failed status check never causes a blind POST retry',async()=>{
  let reads=0,posts=0;const offsets=[]
  const result=await runPipelineImport({preview,wait:async()=>{},request:async(path,options)=>{
    if(path.endsWith('/progress')){
      reads+=1
      if(reads===2)throw error(503)
      return state(reads===1?0:50)
    }
    offsets.push(options.body.offset);posts+=1
    if(posts===1)throw error(504)
    return {progress:state(75)}
  }})
  assert.deepEqual(offsets,[0,50]);assert.equal(result.finished,true)
})

test('authentication failures stop immediately without automatic resubmission',async()=>{
  let posts=0
  await assert.rejects(runPipelineImport({preview,wait:async()=>{},request:async path=>{
    if(path.endsWith('/progress'))return state(25)
    posts+=1;throw error(401)
  }}),/Connection failed/)
  assert.equal(posts,1)
})

test('repeated server failures have a bounded retry count',async()=>{
  let posts=0
  await assert.rejects(runPipelineImport({preview,wait:async()=>{},request:async path=>{
    if(path.endsWith('/progress'))return state(0)
    posts+=1;throw error(503)
  }}),/Connection failed/)
  assert.equal(posts,4)
})

test('a completed import does not submit any further work',async()=>{
  const result=await runPipelineImport({preview,request:async path=>{
    assert.ok(path.endsWith('/progress'));return state(75)
  }})
  assert.equal(result.finished,true)
})

test('changed dataset and a cursor that fails to advance stop safely',async()=>{
  await assert.rejects(runPipelineImport({preview,request:async()=>({...state(25),digest:'different'})}),/does not match/)
  let posts=0
  await assert.rejects(runPipelineImport({preview,request:async path=>{
    if(path.endsWith('/progress'))return state(0)
    posts+=1;return {progress:state(0)}
  }}),/did not confirm/)
  assert.equal(posts,1)
})

test('pausing finishes the current batch and stops before submitting another',async()=>{
  let active=true,posts=0
  const result=await runPipelineImport({preview,isActive:()=>active,onProgress:p=>{if(p.offset===25)active=false},request:async path=>{
    if(path.endsWith('/progress'))return state(0)
    posts+=1;return {progress:state(25)}
  }})
  assert.equal(posts,1);assert.equal(result.offset,25);assert.equal(result.finished,false)
})
