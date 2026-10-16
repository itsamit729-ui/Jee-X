import test from 'node:test'
import assert from 'node:assert/strict'
import { paperDiagramUrls, fetchPaperDiagram } from '../src/lib/teacherPaperImages.js'
const image=()=>new Response(new Uint8Array([137,80,78,71]),{headers:{'Content-Type':'image/png'}})

test('saved paper and passage diagrams keep one stable index across A/B orders',()=>{
  assert.deepEqual(paperDiagramUrls({questions:[{assets:[{url:'/a'}],passage:{assets:[{url:'/p'}]}},{assets:[{url:'/p'},{url:'/b'}]}]}),['/a','/p','/b'])
})

test('legacy hosted bank diagrams resolve through the authenticated saved-paper route',async()=>{
  const calls=[]
  const blob=await fetchPaperDiagram(17,2,'https://old-site.example/question-images/mht-cet/a.png',{apiBase:'',fetchImpl:async (url,options)=>{calls.push({url,options});return image()}})
  assert.equal(blob.type,'image/png')
  assert.equal(calls.length,1)
  assert.equal(calls[0].url,'/api/teacher/papers/17/diagrams/2')
  assert.equal(calls[0].options.headers['X-Jee-Request'],'1')
})

test('a missing saved-paper route can use the original resource in older deployments',async()=>{
  const calls=[]
  await fetchPaperDiagram(17,0,'https://old.example/question-images/a.png',{apiBase:'',fetchImpl:async url=>{calls.push(url);return calls.length===1?new Response('',{status:404}):image()}})
  assert.deepEqual(calls,['/api/teacher/papers/17/diagrams/0','https://old.example/question-images/a.png'])
})

test('temporary render failures retry once, but auth failures remain visible',async()=>{
  let count=0
  await fetchPaperDiagram(17,0,'https://images.example/a.png',{fetchImpl:async()=>++count===1?new Response('',{status:503}):image()})
  assert.equal(count,2)
  count=0
  await assert.rejects(fetchPaperDiagram(17,0,'/question-images/a.png',{fetchImpl:async()=>{count++;return new Response('',{status:401})}}),/Sign in again/)
  assert.equal(count,1)
})

test('PDF export never accepts an HTML fallback or an unsafe URL as a figure',async()=>{
  await assert.rejects(fetchPaperDiagram(1,0,'/question-images/missing.png',{fetchImpl:async()=>new Response('<html>fallback</html>',{headers:{'Content-Type':'text/html'}})}),/page instead/)
  await assert.rejects(fetchPaperDiagram(1,0,'javascript:alert(1)'),/Invalid diagram URL/)
})


test('current relative diagrams use static delivery without database reads or preflight headers',async()=>{
  const calls=[]
  await fetchPaperDiagram(17,0,'/question-images/a.png',{apiBase:'https://api.example',fetchImpl:async(url,options)=>{calls.push({url,options});return image()}})
  assert.equal(calls.length,1)
  assert.equal(calls[0].url,'/question-images/a.png')
  assert.deepEqual(calls[0].options.headers,{})
})
