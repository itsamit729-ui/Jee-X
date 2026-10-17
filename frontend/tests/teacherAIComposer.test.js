import test from 'node:test'
import assert from 'node:assert/strict'
import path from 'node:path'
import {fileURLToPath} from 'node:url'
import Module from 'node:module'
import {buildSync} from 'esbuild'
const filename=fileURLToPath(import.meta.url)
const output=buildSync({stdin:{contents:`import React from 'react';import {renderToStaticMarkup} from 'react-dom/server';import TeacherAIPaper from './src/components/classroom/TeacherAIPaper.jsx';export const html=renderToStaticMarkup(<TeacherAIPaper onCreated={()=>{}} onOpen={()=>{}} onBusy={()=>{}}/>);`,resolveDir:path.resolve(path.dirname(filename),'..'),loader:'jsx'},bundle:true,write:false,platform:'node',format:'cjs',jsx:'automatic',external:['react','react-dom/server'],loader:{'.css':'empty'},logLevel:'silent'}).outputFiles[0].text
const compiled=new Module(filename);compiled.paths=Module._nodeModulePaths(path.dirname(filename));compiled._compile(output,filename)

test('AI paper entry renders one labelled composer with optional examples and no parameter selector',()=>{
  const {html}=compiled.exports
  assert.match(html,/What are we testing today/)
  assert.match(html,/for="ai-paper-request"/)
  assert.match(html,/id="ai-paper-request"/)
  assert.match(html,/Create paper &amp; OMR/)
  assert.match(html,/Try an example/)
  assert.match(html,/type="submit" disabled=""/)
  assert.doesNotMatch(html,/<select|<fieldset|type="checkbox"/)
})
