import test from 'node:test'
import assert from 'node:assert/strict'
import path from 'node:path'
import { fileURLToPath } from 'node:url'
import Module from 'node:module'
import { buildSync } from 'esbuild'

const filename=fileURLToPath(import.meta.url)
const output=buildSync({
  stdin:{contents:`import React from 'react';import {renderToStaticMarkup} from 'react-dom/server';import MathText from './src/components/MathText.jsx';import DeferredDetails from './src/components/DeferredDetails.jsx';import SearchField from './src/components/SearchField.jsx';import StudentOmrId from './src/components/StudentOmrId.jsx';
    export const omr=studentId=>renderToStaticMarkup(<StudentOmrId studentId={studentId}/>);
    export const search=()=>renderToStaticMarkup(<SearchField label="Find a student" placeholder="Find by name, username or OMR ID…" value="Aditi" onChange={()=>{}}/>);
    export const math=text=>renderToStaticMarkup(<MathText text={text}/>);
    export function report(open){let renders=0;function HeavyQuestion(){renders++;return <MathText text={'Solve $x^2=4$'}/>};const html=renderToStaticMarkup(<DeferredDetails summary="Question 1" initialOpen={open}><HeavyQuestion/></DeferredDetails>);return {html,renders}}`,resolveDir:path.resolve(path.dirname(filename),'..'),loader:'jsx'},
  bundle:true,write:false,platform:'node',format:'cjs',jsx:'automatic',external:['react','react-dom/server'],loader:{'.css':'empty'},
}).outputFiles[0].text
const compiled=new Module(filename)
compiled.paths=Module._nodeModulePaths(path.dirname(filename))
compiled._compile(output,filename)
const {math,report,search,omr}=compiled.exports

test('closed report rows defer actual question rendering and opened rows retain maths',()=>{
  const closed=report(false),opened=report(true)
  assert.equal(closed.renders,0)
  assert.match(closed.html,/<summary>Question 1<\/summary>/)
  assert.doesNotMatch(closed.html,/class="katex"/)
  assert.equal(opened.renders,1)
  assert.match(opened.html,/<details[^>]*open=""/)
  assert.match(opened.html,/class="katex"/)
})

test('math keeps inline and display equations contained, preserves lines and escapes plain HTML',()=>{
  const html=math('Speed $v=2$\n$$\\frac{1}{2}$$\n<img src=x onerror=alert(1)>')
  assert.match(html,/math-fragment math-inline/)
  assert.match(html,/math-fragment math-block/)
  assert.match(html,/<br\/>/)
  assert.match(html,/&lt;img/)
  assert.doesNotMatch(html,/<img/)
  assert.equal(math(''),'')
})

test('search keeps the icon separate from a labelled, editable search input',()=>{
  const html=search()
  assert.match(html,/<svg[^>]*aria-hidden="true"/)
  assert.match(html,/<\/svg><input/)
  assert.match(html,/aria-label="Find a student"/)
  assert.match(html,/type="search"/)
  assert.match(html,/value="Aditi"/)
  assert.equal((html.match(/<input/g)||[]).length,1)
})

test('student profile shows the existing ten-digit OMR identity and a copy control',()=>{
  const html=omr(11)
  assert.match(html,/0000000011/)
  assert.match(html,/Your permanent OMR ID/)
  assert.match(html,/Copy your OMR ID/)
  assert.match(html,/leading zeros/)
  assert.doesNotMatch(html,/<input/)
  assert.equal(omr(undefined),'')
})
