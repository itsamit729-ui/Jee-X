import test from 'node:test'
import assert from 'node:assert/strict'
import path from 'node:path'
import {fileURLToPath} from 'node:url'
import Module from 'node:module'
import {buildSync} from 'esbuild'
const filename=fileURLToPath(import.meta.url)
const root=path.resolve(path.dirname(filename),'..')
const result=buildSync({stdin:{contents:`import React from 'react';import {renderToStaticMarkup} from 'react-dom/server';import {PublicationActions} from './src/components/admin/AdminPipelineQuestions.jsx';export const render=props=>renderToStaticMarkup(<PublicationActions {...props}/>);`,resolveDir:root,loader:'jsx'},bundle:true,write:false,platform:'node',format:'cjs',jsx:'automatic',external:['react','react-dom/server'],define:{'import.meta.env':'{}'}}).outputFiles[0].text
const compiled=new Module(filename);compiled.paths=Module._nodeModulePaths(path.dirname(filename));compiled._compile(result,filename)
const render=counts=>compiled.exports.render({preview:{exam:'mht_cet',year:2020,eligible:443,database:{counts:{add:0,update:0,unchanged:0,conflict:0,skip:0,...counts}}},busy:false,onPublish:()=>{},onReview:()=>{}})
test('already imported MHT questions explain publication and expose the live year instead of a disabled Publish button',()=>{
 const html=render({unchanged:443})
 assert.match(html,/Already published/)
 assert.match(html,/All 443 eligible questions/)
 assert.match(html,/href="\/pyq\?exam=mht_cet&amp;year=2020"/)
 assert.doesNotMatch(html,/Publish eligible|disabled/)
})
test('new or draft records still offer an enabled Publish button',()=>{
 const html=render({add:400,update:43})
 assert.match(html,/Publish eligible 2020 questions/)
 assert.doesNotMatch(html,/disabled/)
 assert.doesNotMatch(html,/Already published/)
})
test('all-held and mixed published/held previews explain the reason and offer a review action',()=>{
 for(const counts of [{conflict:443},{unchanged:400,conflict:40,skip:3}]){
  const html=render(counts)
  assert.match(html,/held for review/)
  assert.match(html,/Review held questions/)
  assert.doesNotMatch(html,/Publish eligible|disabled/)
 }
})
