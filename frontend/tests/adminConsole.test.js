import test from 'node:test'
import assert from 'node:assert/strict'
import path from 'node:path'
import { fileURLToPath } from 'node:url'
import Module from 'node:module'
import { buildSync } from 'esbuild'
const filename=fileURLToPath(import.meta.url)
const output=buildSync({stdin:{contents:`import React from 'react';import {renderToStaticMarkup} from 'react-dom/server';import Overview,{TeachingSummary} from './src/components/admin/AdminOverview.jsx';import {DataTable,Pager,validSection,SECTIONS} from './src/components/admin/AdminShared.jsx';import {OperationsLedger,PeopleDirectory} from './src/components/admin/AdminResources.jsx';
export {validSection,SECTIONS};export const overview=data=>renderToStaticMarkup(<Overview data={data} onSection={()=>{}}/>);export const teaching=data=>renderToStaticMarkup(<TeachingSummary data={data}/>);export const table=rows=>renderToStaticMarkup(<DataTable rows={rows} empty="No matching people." columns={[{key:'name',label:'Person'}]}/>);export const pager=data=>renderToStaticMarkup(<Pager data={data} offset={0} busy={false} setOffset={()=>{}}/>);export const scans=()=>renderToStaticMarkup(<OperationsLedger token="test" initialQueue="scans"/>);export const people=()=>renderToStaticMarkup(<PeopleDirectory token="test"/>);`,resolveDir:path.resolve(path.dirname(filename),'..'),loader:'jsx'},bundle:true,write:false,platform:'node',format:'cjs',jsx:'automatic',external:['react','react-dom/server'],loader:{'.css':'empty'}}).outputFiles[0].text
const compiled=new Module(filename);compiled.paths=Module._nodeModulePaths(path.dirname(filename));compiled._compile(output,filename)
const ui=compiled.exports
const data={overview:{total_users:0,student_users:0,teacher_users:0,new_users_today:0,new_users_7d:0,active_users_today:0,total_questions:0,published_questions:0,submitted_attempts:0,attempts_today:0,questions_solved:0,average_accuracy:0},community:{open_question_reports:0,pending_redemptions:0,rated_users:0,rated_contests:0,outstanding_coins:0},daily:{completion_rate:0,assigned_today:0,completed_today:0},growth:[{date:'2026-10-14',signups:0,active_users:0,attempts:0}],recent_users:[],recent_attempts:[],teaching:{classrooms:0,students:0,assignments:0,papers:0,finalized_papers:0,scans:{}}}

test('overview handles an empty platform without misleading chart values and exposes actionable queues',()=>{
 const empty=ui.overview(data)
 assert.doesNotMatch(empty,/NaN|Infinity|undefined/)
 assert.match(empty,/No submitted tests yet/)
 assert.match(empty,/View exact daily numbers/)
 assert.match(empty,/aria-valuenow="0"/)
 const pending=ui.overview({...data,community:{...data.community,open_question_reports:3,pending_redemptions:2}})
 assert.match(pending,/3 question reports to review/)
 assert.match(pending,/2 reward requests pending/)
 assert.match(pending,/Reels &amp; YouTube Shorts/)
 assert.match(ui.teaching(data),/No OMR sheets uploaded yet/)
})
test('tables have headings, preserve escaped user text, and pagers stop on empty or final results',()=>{
 const html=ui.table([{id:1,name:'<script>alert(1)</script>'}])
 assert.match(html,/<th scope="col">Person/)
 assert.match(html,/&lt;script&gt;/)
 assert.doesNotMatch(html,/<script>/)
 assert.match(ui.table([]),/No matching people/)
 for(const total of [0,1,25])assert.equal((ui.pager({total,limit:25}).match(/disabled=""/g)||[]).length,2)
 assert.equal((ui.pager({total:26,limit:25}).match(/disabled=""/g)||[]).length,1)
})
test('all sections are reachable and teaching opens the OMR queue with labelled search',()=>{
 assert.equal(ui.SECTIONS.length,7)
 for(const [key] of ui.SECTIONS)assert.equal(ui.validSection(key),key)
 assert.equal(ui.validSection('unknown'),'overview')
 assert.match(ui.scans(),/aria-pressed="true">OMR scans/)
 assert.match(ui.people(),/aria-label="Find a person or OMR ID"/)
 assert.match(ui.people(),/Account type/)
})
