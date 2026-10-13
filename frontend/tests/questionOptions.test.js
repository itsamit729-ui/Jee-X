import test from 'node:test'
import assert from 'node:assert/strict'
import { optionDisplay, missingOptions } from '../src/lib/questionOptions.js'

test('actual text, mathematical choices, zero and letter answers remain visible',()=>{
  for(const value of ['Velocity','$\\frac{1}{2}$',0,'A'])assert.equal(optionDisplay({assets:[]},{label:'A',content:value}).kind,'text')
  assert.equal(optionDisplay({assets:[]},{label:'B',content:0}).text,'0')
})

test('image-only choices reference their source diagram rather than empty labels',()=>{
  const q={assets:[{url:'/question-images/source.png'}]}
  for(const value of ['A','(A)'])assert.equal(optionDisplay(q,{label:'A',content:value}).kind,'diagram')
  assert.equal(optionDisplay(q,{label:'A',content:'Acceleration'}).kind,'text')
  assert.match(optionDisplay(q,{label:'C',content:'C'}).text,/Option C.*image/)
})

test('missing content without a usable source image is identified, numerical questions stay valid',()=>{
  const q={question_id:42,type:'single_correct',assets:[],options:[{label:'A',content:'  '},{label:'B',content:'2'}]}
  assert.deepEqual(missingOptions([q]),[{number:1,question_id:42,label:'A'}])
  assert.equal(optionDisplay({assets:[{url:'javascript:alert(1)'}]},{label:'A',content:''}).kind,'missing')
  assert.deepEqual(missingOptions([{type:'numerical',options:[]}]),[])
  assert.equal(missingOptions([{...q,options:[]}]).length,1)
})


test('legacy snapshots recover choices embedded in the source stem',()=>{
  const q={stem:'Choose the correct statement.\n(A) Energy increases\n(B) Energy decreases',options:[{label:'A',content:'A'},{label:'B',content:''}]}
  assert.equal(optionDisplay(q,q.options[0]).text,'Energy increases')
  assert.equal(optionDisplay(q,q.options[1]).text,'Energy decreases')
  assert.deepEqual(missingOptions([q]),[])
  assert.equal(optionDisplay({assets:[{url:'/stem-only.png'}]},{label:'A',content:''}).kind,'missing')
})
