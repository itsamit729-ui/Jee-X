import { Component, lazy, Suspense, useCallback, useEffect, useState } from 'react'
import { ArrowUpRight, KeyRound, LogOut, RefreshCw, ShieldCheck } from 'lucide-react'
import { request } from '../lib/api.js'
import { SECTIONS, validSection, date, Notice } from '../components/admin/AdminShared.jsx'
import '../admin.css'
const Overview=lazy(()=>import('../components/admin/AdminOverview.jsx'))
const TeachingSummary=lazy(()=>import('../components/admin/AdminOverview.jsx').then(m=>({default:m.TeachingSummary})))
const ContentSummary=lazy(()=>import('../components/admin/AdminOverview.jsx').then(m=>({default:m.ContentSummary})))
const People=lazy(()=>import('../components/admin/AdminResources.jsx').then(m=>({default:m.PeopleDirectory})))
const Registrations=lazy(()=>import('../components/admin/AdminResources.jsx').then(m=>({default:m.RegistrationDirectory})))
const PipelineQuestions=lazy(()=>import('../components/admin/AdminPipelineQuestions.jsx'))
const Questions=lazy(()=>import('../components/admin/AdminResources.jsx').then(m=>({default:m.QuestionDirectory})))
const Coverage=lazy(()=>import('../components/admin/AdminResources.jsx').then(m=>({default:m.PaperCoverage})))
const Classrooms=lazy(()=>import('../components/admin/AdminResources.jsx').then(m=>({default:m.ClassroomDirectory})))
const Operations=lazy(()=>import('../components/admin/AdminResources.jsx').then(m=>({default:m.OperationsLedger})))
const Social=lazy(()=>import('../components/AdminSocialAutomation.jsx'))
const Teachers=lazy(()=>import('../components/classroom/AdminTeacherAccess.jsx'))
const Plans=lazy(()=>import('../components/AdminPlanInterests.jsx'))
const Acquisition=lazy(()=>import('../components/AdminPaperAcquisition.jsx'))
const KEY='jeeedge_admin_session'
function Brand(){return <div className="adm-brand">JEE <span>EDGE</span><b>ADMIN</b></div>}
function Login({done}){
 const[password,setPassword]=useState(''),[error,setError]=useState(''),[busy,setBusy]=useState(false)
 async function login(event){event.preventDefault();setBusy(true);setError('');try{const result=await request('/api/admin/login',{method:'POST',body:{password}});sessionStorage.setItem(KEY,result.token);done(result.token)}catch(e){setError(e.message)}finally{setBusy(false)}}
 return <main className="adm-login"><form onSubmit={login} className="adm-login-card"><Brand/><div className="adm-login-icon"><ShieldCheck size={25}/></div><p className="adm-kicker">Private workspace</p><h1>Admin workspace</h1><p>People, teaching, content and publishing. One place to keep things moving.</p><label htmlFor="admin-password">Admin password</label><div className="adm-input"><KeyRound size={17}/><input id="admin-password" type="password" autoComplete="current-password" value={password} onChange={e=>setPassword(e.target.value)} required autoFocus placeholder="Enter your admin password"/></div>{error&&<Notice error={error}/>}<button disabled={busy||!password.trim()}>{busy?<RefreshCw size={17} className="spin"/>:<ShieldCheck size={17}/>} {busy?'Signing in…':'Open admin workspace'}</button><small>Your session stays in this browser tab. Sign out when you finish.</small><a href="/">Back to Jee Edge <ArrowUpRight size={14}/></a></form></main>
}
class SectionBoundary extends Component {state={error:false};static getDerivedStateFromError(){return{error:true}};render(){return this.state.error?<Notice error="This section could not be displayed." retry={()=>this.setState({error:false})}/>:this.props.children}}
function Dashboard({token,exit}){
 const[section,setSection]=useState(()=>validSection(location.hash.slice(1))),[data,setData]=useState(null),[error,setError]=useState(''),[busy,setBusy]=useState(true),[revision,setRevision]=useState(0),[peopleView,setPeopleView]=useState('profiles')
 const load=useCallback(async()=>{setBusy(true);setError('');try{setData(await request('/api/admin/dashboard',{token,cache:false}))}catch(e){if(e.status===401){sessionStorage.removeItem(KEY);exit()}else setError(e.message)}finally{setBusy(false)}},[token,exit])
 useEffect(()=>{load()},[load])
 useEffect(()=>{const changed=()=>{if(location.hash!=='#admin-content')setSection(validSection(location.hash.slice(1)))};window.addEventListener('hashchange',changed);return()=>window.removeEventListener('hashchange',changed)},[])
 function choose(value){const destination=value==='signups'?'people':value;if(destination==='people')setPeopleView(value==='signups'?'signups':'profiles');setSection(destination);history.replaceState(null,'','#'+destination)}
 async function logout(){try{await request('/api/admin/logout',{token,method:'POST'})}catch{}sessionStorage.removeItem(KEY);exit()}
 const selected=SECTIONS.find(([key])=>key===section),props={token,revision}
 return <main className="adm-page"><a className="adm-skip" href="#admin-content">Skip to dashboard content</a><header className="adm-top"><Brand/><div><span className="adm-private"><ShieldCheck size={14}/>Private workspace</span><button disabled={busy} onClick={()=>{load();setRevision(v=>v+1)}} aria-label="Refresh current section"><RefreshCw className={busy?'spin':''} size={16}/><span>Refresh</span></button><button onClick={logout} aria-label="Sign out of admin"><LogOut size={16}/><span>Sign out</span></button></div></header><div className="adm-wrap"><section className="adm-hero"><div><p className="adm-kicker">Jee Edge / Control room</p><h1>Your platform, at a glance.</h1><p>Know what’s happening, find what needs attention, and keep the platform moving.</p></div><span className="adm-updated">{busy?'Updating overview…':data?`Updated ${date(data.generated_at)} IST`:'Overview unavailable'}</span></section><nav className="adm-nav" aria-label="Admin sections">{SECTIONS.map(([key,label])=><button key={key} aria-current={section===key?'page':undefined} onClick={()=>choose(key)}>{label}</button>)}</nav><section className="adm-section-heading"><div><h2>{selected[1]}</h2><p>{selected[2]}</p></div><span>All times in IST</span></section>{error&&<Notice error={error} retry={load}/>}<div id="admin-content" tabIndex={-1}><SectionBoundary key={section+revision}><Suspense fallback={<div className="adm-section-loading" role="status"><RefreshCw size={19} className="spin"/>Opening {selected[1].toLowerCase()}…</div>}><div className="adm-section-stack">
 {section==='overview'&&(data?<Overview data={data} onSection={choose}/>:busy?<div className="adm-skeleton" role="status" aria-label="Loading platform overview">{Array.from({length:6},(_,i)=><div key={i}/>)}</div>:<p className="adm-description">Retry the overview above, or open another section.</p>)}
 {section==='people'&&<><div className="adm-subnav" role="group" aria-label="People views"><button aria-pressed={peopleView==='profiles'} onClick={()=>setPeopleView('profiles')}>Profiles</button><button aria-pressed={peopleView==='signups'} onClick={()=>setPeopleView('signups')}>Signup accounts{data?.overview.pending_profiles?` · ${data.overview.pending_profiles} pending`:''}</button></div>{peopleView==='profiles'?<People {...props}/>:<Registrations {...props}/>}<Teachers key={revision} token={token}/></>}
 {section==='teaching'&&<>{data&&<TeachingSummary data={data}/>}<Classrooms {...props}/><Operations key={'scans'+revision} {...props} initialQueue="scans"/></>}
 {section==='content'&&<>{data&&<ContentSummary data={data}/>}<PipelineQuestions token={token} onPublished={()=>setRevision(v=>v+1)}/><Questions {...props}/><Coverage {...props}/></>}
 {section==='growth'&&<><Acquisition key={revision} token={token}/><Plans key={'plans'+revision} token={token}/></>}
 {section==='publishing'&&<Social key={revision} token={token}/>}
 {section==='operations'&&<Operations {...props}/>}
 </div></Suspense></SectionBoundary></div><footer className="adm-footer"><span>JEE EDGE · Admin workspace</span><span>Live records · Refresh to fetch the latest data</span></footer></div></main>
}
export default function Admin(){const[token,setToken]=useState(()=>sessionStorage.getItem(KEY)||'');const exit=useCallback(()=>setToken(''),[]);return token?<Dashboard token={token} exit={exit}/>:<Login done={setToken}/>}
