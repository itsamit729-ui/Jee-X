import test from 'node:test'
import assert from 'node:assert/strict'
import path from 'node:path'
import {fileURLToPath} from 'node:url'
import Module from 'node:module'
import {buildSync} from 'esbuild'
import {matchesSearch,rankedSearch} from '../src/lib/search.js'
const filename=fileURLToPath(import.meta.url),root=path.resolve(path.dirname(filename),'..')
const code=buildSync({stdin:{contents:`import React from 'react';import {renderToStaticMarkup} from 'react-dom/server';import {MemoryRouter} from 'react-router-dom';import TestSession,{clock} from './src/components/TestSession.jsx';import MhtExam from './src/components/MhtExam.jsx';import {WeekPlan} from './src/components/PlanWorkspace.jsx';import ChapterPicker from './src/components/ChapterPicker.jsx';
export {clock};export const session=props=>renderToStaticMarkup(<TestSession {...props}/>);export const cet=props=>renderToStaticMarkup(<MhtExam {...props}/>);export const week=props=>renderToStaticMarkup(<MemoryRouter><WeekPlan {...props}/></MemoryRouter>);export const chapters=props=>renderToStaticMarkup(<ChapterPicker {...props}/>);`,resolveDir:root,loader:'jsx'},bundle:true,write:false,platform:'node',format:'cjs',jsx:'automatic',external:['react','react-dom/server','react-router-dom'],define:{'import.meta.env':'{}'},loader:{'.css':'empty'}}).outputFiles[0].text
const compiled=new Module(filename);compiled.paths=Module._nodeModulePaths(path.dirname(filename));compiled._compile(code,filename)
const ui=compiled.exports
const q={question_id:1,ref:'DO-NOT-SHOW-QUESTION-CODE',subject_code:'PHY',type:'single_correct',stem:'Find $x$ when $2x=4$.',options:[{id:1,label:'A',content:'2'},{id:2,label:'B',content:'4'}],marks_correct:4,marks_wrong:1,assets:[]}
const props={test:{title:'JEE test',questions:[q],is_mock:true},index:0,answers:{1:{option_ids:[1]}},remaining:120,elapsed:65,questionSeconds:12,onIndex:()=>{},onOption:()=>{},onNumeric:()=>{},onClear:()=>{},onSubmit:()=>{},onExit:()=>{},submitting:false,timed:true}
test('active test has its own header, visible clock and controls without reference codes or the site menu',()=>{
 const html=ui.session(props)
 assert.match(html,/Time remaining/);assert.match(html,/02:00/);assert.match(html,/This question 00:12/)
 assert.match(html,/Next|Submit test/);assert.match(html,/aria-checked="true"/)
 assert.doesNotMatch(html,/DO-NOT-SHOW|studio-topbar|Explore menu/)
 const practice=ui.session({...props,test:{...props.test,is_mock:false},timed:false})
 assert.match(practice,/Practice time elapsed/);assert.match(practice,/01:05/)
 assert.equal(ui.clock(3601),'1:00:01')
})
test('MHT exam keeps the question, palette toggle, section timer and save actions available',()=>{
 const html=ui.cet({...props,remaining:10700,onAnswer:()=>{}})
 assert.match(html,/Section time remaining/);assert.match(html,/Save &amp; Next/);assert.match(html,/Close questions/)
 assert.doesNotMatch(html,/DO-NOT-SHOW|studio-topbar/)
})
test('chapter selector shows the selected chapter and supports a loading gate',()=>{
 const html=ui.chapters({chapters:[{id:7,name:'Rotational motion'}],value:'7',onChange:()=>{}})
 assert.match(html,/Rotational motion/);assert.match(html,/Choose chapter/);assert.doesNotMatch(html,/<select/)
 assert.match(ui.chapters({chapters:[],loading:true,onChange:()=>{}}),/disabled=""/)
})
test('search matches reordered terms, subject abbreviations, punctuation and ranked exact chapter names',()=>{
 assert.equal(matchesSearch('JEE Main full mock paper','mock jee'),true)
 assert.equal(matchesSearch('Physics rotational motion','phys rotation'),true)
 assert.equal(matchesSearch('Mathematics · three-dimensional geometry','3d maths'),true)
 assert.equal(matchesSearch('Physics motion','chem'),false)
 assert.deepEqual(rankedSearch([{name:'Wave optics'},{name:'Optics'},{name:'Ray optics'}],'optics').map(x=>x.name),['Optics','Wave optics','Ray optics'])
})
test('weekly plan exposes direct week navigation and topic search without nested later-week disclosures',()=>{
 const html=ui.week({plan:{weekly_hours:6},topics:[{week:1,topic_id:1,subject:'PHY',chapter:'Motion',topic:'Speed',minutes:30,within_horizon:true},{week:2,topic_id:2,subject:'CHEM',chapter:'Atomic',topic:'Atoms',minutes:45,within_horizon:true}],onChoose:()=>{}})
 assert.match(html,/Next week →/);assert.match(html,/1 topics · 30 minutes scheduled/);assert.match(html,/Search scheduled topics/)
 assert.doesNotMatch(html,/mp-later-week|<details/)
})
