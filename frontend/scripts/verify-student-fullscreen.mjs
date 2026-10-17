// Browser integration checks. Set PLAYWRIGHT_MODULE and CHROMIUM_EXECUTABLE
// when using a managed browser installation instead of local Playwright.
import assert from 'node:assert/strict'
import { createServer } from 'node:http'
import { readFile } from 'node:fs/promises'
import { createRequire } from 'node:module'
import { build } from 'esbuild'
const require = createRequire(import.meta.url)
const { chromium } = require(process.env.PLAYWRIGHT_MODULE || 'playwright')
const entry = `
import React,{useState} from 'react'; import {createRoot} from 'react-dom/client';
import TestInstructions from './src/components/TestInstructions.jsx';
import FullscreenGuard from './src/components/FullscreenGuard.jsx';
import {useFullscreenLock} from './src/lib/fullscreen.js';
let element=null; Object.defineProperty(document,'fullscreenElement',{get:()=>element});
window.denied=false; document.documentElement.requestFullscreen=()=>{if(window.denied)return Promise.reject(Error('denied'));window.transition(true);return Promise.resolve()};
document.exitFullscreen=()=>{window.transition(false);return Promise.resolve()};
window.transition=value=>{element=value?document.documentElement:null;document.dispatchEvent(new Event('fullscreenchange'));document.dispatchEvent(new Event('webkitfullscreenchange'))};
function App(){const [active,setActive]=useState(false),[loading,setLoading]=useState(false),[submissions,setSubmissions]=useState(0),[error,setError]=useState('');
 const submit=()=>{setSubmissions(n=>n+1);setError('Connection failed. Retry submission.');};
 const fs=useFullscreenLock(active,submit);
 return <><TestInstructions session={{startedAt:Date.now(),details:{exam:'mht_cet',mock:true},paper:{title:'MHT CET · Shift mock',questions:[{type:'single_correct'}],is_mock:true,duration_sec:10800},loading,error:''}} onEnter={()=>{document.documentElement.requestFullscreen().catch(()=>{});setActive(true)}}/>
 <button id="loading" onClick={()=>setLoading(v=>!v)}>Toggle loading</button><button id="stop" onClick={()=>setActive(false)}>Stop</button><button id="start" onClick={()=>setActive(true)}>Start again</button>
 <output id="state">{JSON.stringify({active,submissions,count:fs.exitCount,limit:fs.limitReached,exited:fs.exited})}</output>
 <FullscreenGuard {...fs} onResume={fs.resume} onSubmit={submit} error={error}/></>}
createRoot(document.getElementById('root')).render(<React.StrictMode><App/></React.StrictMode>);
`
const bundle = await build({stdin:{contents:entry,resolveDir:process.cwd(),loader:'jsx'},bundle:true,write:false,format:'iife',jsx:'automatic',loader:{'.css':'empty'},plugins:[{name:'header-stub',setup(b){b.onResolve({filter:/\/AppHeader\.jsx$/},()=>({path:'header',namespace:'stub'}));b.onLoad({filter:/.*/,namespace:'stub'},()=>({contents:'export default function Header(){return null}',loader:'jsx'}))}}]})
const css = await readFile('src/index.css','utf8') + await readFile('src/components/test-instructions.css','utf8')
const server=createServer((req,res)=>{res.setHeader('Content-Type','text/html');res.end(`<html><head><style>${css}</style></head><body><div id="root"></div><script>${bundle.outputFiles[0].text}</script></body></html>`)})
await new Promise(resolve=>server.listen(0,'127.0.0.1',resolve))
let browser
try {
 browser=await chromium.launch({headless:true,...(process.env.CHROMIUM_EXECUTABLE?{executablePath:process.env.CHROMIUM_EXECUTABLE}:{}),args:['--no-sandbox',...(process.env.CHROMIUM_SINGLE_PROCESS ? ['--single-process','--no-zygote','--disable-gpu','--disable-dev-shm-usage'] : [])]})
 const page=await browser.newPage({viewport:{width:1365,height:900}})
 const errors=[];page.on('pageerror',e=>errors.push(e.message))
 await page.goto(`http://127.0.0.1:${server.address().port}`)
 const state=()=>page.locator('#state').textContent().then(JSON.parse)
 const settle=async()=>{await page.evaluate(()=>new Promise(r=>requestAnimationFrame(()=>requestAnimationFrame(r))))}
 const begin=page.getByRole('button',{name:'Begin test',exact:true})
 assert.equal(await begin.isEnabled(),false)
 await page.getByRole('checkbox').check()
 assert.equal(await begin.isEnabled(),true,'ready paper starts without a 90-second wait')
 await page.locator('#loading').click();assert.equal(await begin.isEnabled(),false)
 await page.locator('#loading').click();assert.equal(await begin.isEnabled(),true)
 const colors=await page.locator('.test-instructions-card').evaluate(el=>({bg:getComputedStyle(el).backgroundColor,fg:getComputedStyle(el).color}))
 assert.equal(colors.bg,'rgb(255, 255, 255)');assert.equal(colors.fg,'rgb(32, 33, 38)')
 await begin.click();await settle()
 for(let count=1;count<=3;count++){
   await page.evaluate(()=>window.transition(false));await settle()
   assert.equal((await state()).count,count);assert.equal((await state()).submissions,0)
   await page.getByRole('button',{name:'Submit & exit test'}).waitFor()
   if(count===1){
     await page.evaluate(()=>window.denied=true);await page.getByRole('button',{name:'Resume test'}).click();await settle()
     assert.equal((await state()).exited,true,'denied resume keeps the guard visible')
     assert.equal((await state()).count,1,'denial is not another exit')
     await page.evaluate(()=>window.denied=false)
   }
   await page.getByRole('button',{name:'Resume test'}).click();await settle()
 }
 await page.evaluate(()=>window.transition(false));await settle()
 assert.equal((await state()).count,4);assert.equal((await state()).submissions,1)
 assert.equal(await page.getByRole('button',{name:'Resume test'}).count(),0)
 await page.evaluate(()=>{window.transition(false);window.transition(false)});await settle()
 assert.equal((await state()).submissions,1,'duplicate events cannot submit twice')
 await page.getByRole('button',{name:'Retry submission'}).click();await settle()
 assert.equal((await state()).submissions,2,'failed submission has an explicit retry')
 await page.evaluate(()=>document.getElementById('stop').click());await settle()
 assert.equal((await state()).count,0)
 await begin.click();await settle();await page.evaluate(()=>window.transition(false));await settle()
 await page.getByRole('button',{name:'Submit & exit test'}).click();await settle()
 assert.equal((await state()).submissions,3,'student can submit early from the exit dialog')
 assert.deepEqual(errors,[])
 await page.setViewportSize({width:390,height:844})
 await page.evaluate(()=>document.getElementById('stop').click());await settle()
 assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),true,'instructions fit mobile width')
 console.log('PASS: immediate begin, loading gate, contrast, mobile width, three warnings, fourth-exit submission, duplicate events, denied resume, retry, early exit, reset (React StrictMode).')
} finally {if(browser)await browser.close();await new Promise(resolve=>server.close(resolve))}
