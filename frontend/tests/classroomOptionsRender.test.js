import test from 'node:test'
import assert from 'node:assert/strict'
import path from 'node:path'
import { fileURLToPath } from 'node:url'
import Module from 'node:module'
import { buildSync } from 'esbuild'

// Render the real shared component so the option preview cannot disappear while
// option-data unit tests still pass. No browser or network is required.
const filename=fileURLToPath(import.meta.url)
const output=buildSync({
  stdin:{contents:"import React from 'react'; import {renderToStaticMarkup} from 'react-dom/server'; import QuestionContent from './src/components/classroom/QuestionContent.jsx'; export function render(question, props={options:true}) { return renderToStaticMarkup(<QuestionContent question={question} {...props}/>); }",resolveDir:path.resolve(path.dirname(filename),'..'),loader:'jsx'},
  bundle:true,write:false,platform:'node',format:'cjs',jsx:'automatic',external:['react','react-dom/server'],loader:{'.css':'empty'},
}).outputFiles[0].text
const compiled=new Module(filename)
compiled.paths=Module._nodeModulePaths(path.dirname(filename))
compiled._compile(output,filename)
const {render}=compiled.exports
const base={stem:'Choose an answer.',subject:'PHY',chapter:'Motion',ref:'PREVIEW',type:'single_correct',assets:[],options:[{id:1,label:'A',content:'Velocity increases',is_correct:true},{id:2,label:'B',content:'$\\frac{1}{2}$',is_correct:false}]}

test('teacher picker renders actual choice text and mathematics beside labels',()=>{
  const html=render(base)
  assert.match(html,/aria-label="Answer options"/)
  assert.match(html,/Velocity increases/)
  assert.match(html,/class="katex"/)
  assert.equal((html.match(/cl-choice-letter/g)||[]).length,2)
})

test('source graph choices stay explicit and genuinely empty choices are flagged',()=>{
  const image={url:'/question-images/choices.png',alt_text:'Source graphs'}
  const html=render({...base,assets:[image],options:base.options.map(o=>({...o,content:o.label}))})
  assert.match(html,/src="\/question-images\/choices.png"/)
  assert.match(html,/Option A is shown in the question image/)
  const missing=render({...base,assets:[image],options:base.options.map(o=>({...o,content:''}))})
  assert.match(missing,/Option A text is unavailable/)
  assert.doesNotMatch(missing,/Option A is shown in the question image/)
})

test('released review includes choices and keys; numerical papers show their format',()=>{
  assert.match(render(base,{solution:true}),/Velocity increases/)
  assert.match(render(base,{solution:true}),/Correct answer/)
  assert.match(render({...base,type:'numerical',options:[]}),/Numerical answer/)
})
