import test from 'node:test'
import assert from 'node:assert/strict'
import {createPaperPdfCache,pdfCaptureBatches} from '../src/lib/teacherPaperPdfCache.js'
const paper={id:17,version:1,title:'Physics',questions:[{question_id:1,stem:'A'}],settings:{duration_minutes:60},variant_b:[1],sets_enabled:true}

test('concurrent preparation, both sets and repeat downloads render the questions only once',async()=>{
  let renders=0,compositions=[]
  const prepare=createPaperPdfCache({render:async(p,report)=>{renders++;report({label:'Rendering',percent:50});await Promise.resolve();return 'rendered'},compose:async(p,v,content)=>{compositions.push(v);return new Blob([content+v])}})
  const progress=[]
  const [a,same,b]=await Promise.all([prepare(paper,'A',x=>progress.push(x.percent)),prepare(paper,'A'),prepare(paper,'B')])
  assert.equal(renders,1);assert.deepEqual(compositions,['A','B']);assert.strictEqual(a,same)
  assert.equal(await a.text(),'renderedA');assert.equal(await b.text(),'renderedB')
  assert.strictEqual(await prepare(structuredClone(paper),'A'),a)
  assert.equal(renders,1);assert.ok(progress.includes(50));assert.equal(progress.at(-1),100)
})

test('failed diagrams can be retried without retaining a rejected promise',async()=>{
  let attempts=0
  const prepare=createPaperPdfCache({render:async()=>{if(++attempts===1)throw Error('Image 404');return 'restored'},compose:async()=>new Blob(['PDF'])})
  await assert.rejects(prepare(paper),/Image 404/)
  assert.equal(await (await prepare(paper)).text(),'PDF');assert.equal(attempts,2)
})

test('changes to content or settings invalidate PDFs and old paper entries are bounded',async()=>{
  let renders=0
  const prepare=createPaperPdfCache({limit:2,render:async()=>++renders,compose:async()=>new Blob()})
  await prepare(paper)
  await prepare({...paper,settings:{duration_minutes:90}})
  await prepare({...paper,questions:[{question_id:1,stem:'Corrected'}]})
  assert.equal(renders,3)
  await prepare(paper);assert.equal(renders,4)
})

test('30 question captures are grouped into bounded batches without dropping tall questions',()=>{
  const blocks=Array.from({length:31},(_,id)=>({id,height:380}))
  const batches=pdfCaptureBatches(blocks)
  assert.equal(batches.length,6)
  assert.deepEqual(batches.flat(),blocks)
  assert.ok(batches.every(b=>b.length<=6&&b.reduce((n,x)=>n+x.height,0)<=3000))
  const tall=[{height:100},{height:4000},{height:500}]
  assert.deepEqual(pdfCaptureBatches(tall).map(b=>b.length),[1,1,1])
})
