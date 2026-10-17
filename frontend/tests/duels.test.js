import test from 'node:test'
import assert from 'node:assert/strict'
import path from 'node:path'
import {fileURLToPath} from 'node:url'
import Module from 'node:module'
import {buildSync} from 'esbuild'
import {formats,secondsUntil,resultTitle,duelService} from '../src/lib/duels.js'
import {setCacheIdentity} from '../src/lib/requestCache.js'
const filename=fileURLToPath(import.meta.url),root=path.resolve(path.dirname(filename),'..')
const code=buildSync({stdin:{contents:`import React from 'react';import {renderToStaticMarkup} from 'react-dom/server';import {MemoryRouter} from 'react-router-dom';import {MatchPlayers,DuelResults} from './src/pages/Duels.jsx';import FullscreenGuard from './src/components/FullscreenGuard.jsx';export const players=props=>renderToStaticMarkup(<MemoryRouter><MatchPlayers {...props}/></MemoryRouter>);export const results=props=>renderToStaticMarkup(<MemoryRouter><DuelResults {...props}/></MemoryRouter>);export const guard=props=>renderToStaticMarkup(<FullscreenGuard {...props}/>);`,resolveDir:root,loader:'jsx'},bundle:true,write:false,platform:'node',format:'cjs',jsx:'automatic',external:['react','react-dom/server','react-router-dom'],define:{'import.meta.env':'{}'},loader:{'.css':'empty'}}).outputFiles[0].text
const compiled=new Module(filename);compiled.paths=Module._nodeModulePaths(path.dirname(filename));compiled._compile(code,filename)
const ui=compiled.exports
const question={question_id:'bank:1',subject_code:'PHY',type:'single_correct',stem:'What is $2+2$?',assets:[],options:[{id:'A',label:'A',content:'4'},{id:'B',label:'B',content:'5'}]}
const review={outcome:'correct',marks:4,selected_option_ids:['A'],correct_option_ids:['A'],solution:'Add two and two.'}
const match={id:'m',state:'completed',winner_id:12,question_count:1,questions:[question],players:[{user_id:12,username:'alice',ready:true,submitted:true,result:{score:4,possible_marks:4,correct:1,wrong:0,skipped:0,questions:[review]}},{user_id:14,username:'bobby',ready:true,submitted:true,result:{score:-1,possible_marks:4,correct:0,wrong:1,skipped:0,questions:[{...review,outcome:'wrong',marks:-1,selected_option_ids:['B']}]}}]}
test('match players use the server participant identity, show progress without scores',()=>{
 const html=ui.players({match:{...match,state:'active'},myId:12})
 assert.match(html,/@alice/);assert.match(html,/you/);assert.match(html,/@bobby/)
 assert.doesNotMatch(html,/PRIVATE|score|Add two/)
})
test('finished match shows both scores, actual selected options, solution and rematch',()=>{
 const html=ui.results({match,myId:12,onRematch:()=>{}})
 assert.match(html,/You won this round/);assert.match(html,/Question 1/);assert.match(html,/You selected:.*A/)
 assert.match(html,/Opponent selected:.*B/);assert.match(html,/Add two and two/);assert.match(html,/Challenge to a rematch/)
 assert.doesNotMatch(html,/bank:1/)
})
test('clock uses server offset, clamps expiry, and ties do not invent a speed winner',()=>{
 const t=Date.parse('2026-10-18T12:00:00Z')
 assert.equal(secondsUntil('2026-10-18T12:00:10Z',t-3000,3000),10)
 assert.equal(secondsUntil('2026-10-18T12:00:10Z',t+11000),0)
 assert.equal(resultTitle({...match,winner_id:null},12),'A draw. Well played.')
 assert.equal(resultTitle(match,14),'A rematch awaits.')
 assert.deepEqual(formats.map(f=>f.count),[5,10,15])
})
test('initial fullscreen denial explains entry without counting it as an exit',()=>{
 const html=ui.guard({exited:true,exitCount:0,onResume:()=>{},onSubmit:()=>{}})
 assert.match(html,/Enter full-screen to continue/);assert.match(html,/Resume test/)
 assert.doesNotMatch(html,/Fullscreen exit 0/)
})
test('match reads bypass cached lobby and persist answers using the authenticated API',async()=>{
 const original=globalThis.fetch,calls=[]
 globalThis.fetch=async(url,options)=>{calls.push({url,options});return new Response(JSON.stringify({id:'a'}),{headers:{'Content-Type':'application/json'}})}
 try{
  setCacheIdentity('duel-player-12')
  await duelService.get('a',false);await duelService.get('a',false)
  await duelService.save('a','bank:1',{option_ids:['A'],numeric_answer:null})
  assert.equal(calls.length,3)
  assert.match(calls[0].url,/paper=false/)
  assert.equal(calls[2].options.method,'PUT')
  assert.equal(calls[2].options.credentials,'include')
  assert.deepEqual(JSON.parse(calls[2].options.body),{option_ids:['A'],numeric_answer:null})
 }finally{globalThis.fetch=original;setCacheIdentity(null)}
})
