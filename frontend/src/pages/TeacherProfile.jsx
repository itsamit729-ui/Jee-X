import { useEffect, useState } from 'react'
import { Link, useLocation } from 'react-router-dom'
import { useAuth } from '../auth/AuthContext.jsx'
import { API_URL, request } from '../lib/api.js'
import { Shell, useLoad, LoadState, ErrorMessage, classApi } from '../components/classroom/shared.jsx'
import '../components/classroom/teacher-papers.css'

const profileSignature = f => JSON.stringify([f?.name,f?.institution,f?.subjects,f?.bio])
const subjects=['Physics','Chemistry','Mathematics','English','Logical reasoning','Biology']
export default function TeacherProfile() {
  const load=useLoad('/teacher/profile'), {refreshSession}=useAuth()
  const account=useLocation().pathname==='/teacher/account'
  const [form,setForm]=useState(null),[savedSignature,setSavedSignature]=useState(''),[busy,setBusy]=useState(false),[error,setError]=useState(''),[message,setMessage]=useState(''),[photoVersion,setPhotoVersion]=useState(0)
  useEffect(()=>{if(load.data){setForm(load.data);setSavedSignature(profileSignature(load.data))}},[load.data])
  const dirty=!account&&form&&profileSignature(form)!==savedSignature
  useEffect(()=>{if(!dirty)return;const unload=e=>{e.preventDefault();e.returnValue=''};const navigate=e=>{if(e.target.closest?.('a[href]')&&!window.confirm('Leave without saving your profile changes?')){e.preventDefault();e.stopPropagation()}};window.addEventListener('beforeunload',unload);document.addEventListener('click',navigate,true);return()=>{window.removeEventListener('beforeunload',unload);document.removeEventListener('click',navigate,true)}},[dirty])
  const set=(key,value)=>setForm(f=>({...f,[key]:value}))
  async function action(fn){setError('');setMessage('');setBusy(true);try{await fn()}catch(e){setError(e.message)}finally{setBusy(false)}}
  async function save(event){event.preventDefault();await action(async()=>{const {name,institution,subjects,bio,version}=form;const saved=await classApi('/teacher/profile',{method:'PUT',body:{name,institution,subjects,bio,version}});setForm(saved);setSavedSignature(profileSignature(saved));await refreshSession();setMessage('Teacher profile saved.')})}
  async function photo(file){if(!file)return;await action(async()=>{if(file.size>4*1024*1024)throw Error('Choose an image under 4 MB.');const result=await request('/api/teacher/profile/avatar',{method:'PUT',body:file,raw:true});setForm(f=>({...f,avatar_url:result.avatar_url}));setPhotoVersion(v=>v+1);setMessage('Profile photo updated.')})}
  const support=import.meta.env.VITE_SUPPORT_EMAIL||'admin@jeeedge.in'
  return <Shell eyebrow="TEACHER ACCOUNT" title={account?'Account & support':'Your teacher profile'} intro={account?'Manage access, security and help for your teaching workspace.':'Introduce yourself and keep your teaching details up to date.'} action={<Link className="btn btn-secondary" to="/teacher">Back to overview</Link>}>
    <nav className="tw-profile-tabs" aria-label="Teacher account"><Link aria-current={!account?'page':undefined} to="/teacher/profile">Profile</Link><Link aria-current={account?'page':undefined} to="/teacher/account">Account & support</Link></nav>
    <LoadState {...load}/><ErrorMessage error={error}/>{message&&<p className="cl-success" role="status">{message}</p>}
    {form&&<div className="cl-columns tp-workspace tw-profile-layout"><section className="cl-main">{!account?<form className="cl-card tp-form tw-profile-form" onSubmit={save}><fieldset className="tw-profile-fields" disabled={busy}>
      <div className="cl-row"><div className="teacher-profile-avatar">{form.avatar_url?<img src={`${API_URL}${form.avatar_url}?v=${photoVersion}`} alt="Your teacher profile"/>:<span>{form.name?.slice(0,1).toUpperCase()}</span>}</div><div><h2>{form.name}</h2><p>Teacher account · @{form.username}</p></div></div>
      <label>Profile photo<input type="file" accept="image/jpeg,image/png,image/webp" disabled={busy} onChange={e=>{photo(e.target.files?.[0]);e.target.value=''}}/><small>JPEG, PNG or WebP, up to 4 MB. Visible in your account.</small></label>
      {form.avatar_url&&<button type="button" className="btn btn-quiet" disabled={busy} onClick={()=>action(async()=>{await classApi('/teacher/profile/avatar',{method:'DELETE'});setForm(f=>({...f,avatar_url:null}));setMessage('Profile photo removed.')})}>Remove photo</button>}
      <div className="cl-form-grid"><label>Your name<input value={form.name} minLength={2} maxLength={100} required onChange={e=>set('name',e.target.value)}/><small>Students see this name alongside your classes.</small></label>
      <label>School, institute or coaching centre <small>Optional</small><input value={form.institution} maxLength={150} onChange={e=>set('institution',e.target.value)}/></label></div>
      <fieldset><legend>Subjects you teach</legend><div className="tp-checks">{subjects.map(subject=><label key={subject}><input type="checkbox" checked={form.subjects.includes(subject)} onChange={e=>set('subjects',e.target.checked?[...form.subjects,subject]:form.subjects.filter(s=>s!==subject))}/>{subject}</label>)}</div></fieldset>
      <label>About your teaching <small>Optional</small><textarea value={form.bio} maxLength={1000} onChange={e=>set('bio',e.target.value)} placeholder="Your teaching experience, approach or specialisms"/></label><small>Your teaching details help students recognise you and your classes.</small>
      <div className="tw-profile-save"><button className="btn btn-primary" disabled={busy||!dirty}>{busy?'Saving…':'Save teacher profile'}</button><span role="status">{dirty?'Unsaved changes':'All details saved'}</span></div></fieldset>
    </form>:<section className="cl-card"><span className="cl-pill">Access active</span><h2>Teacher Studio</h2><p>Your workspace includes classes, student rosters, paper creation, PDF and OMR tools, and class reports.</p><p>Preparing your first class? Start with a paper, invite your students and choose an online or printed test. We can help you get set up.</p><div className="tp-actions"><Link className="btn btn-primary" to="/teacher?tab=papers&create=1">Create a paper</Link><Link className="btn btn-secondary" to="/teacher?tab=students">View students</Link></div></section>}</section>
    <aside className="cl-sidebar"><section className="cl-card"><h2>Sign-in & security</h2><p>{form.email}</p><p>Manage your password and connect Google for sign-in.</p><Link className="btn btn-secondary" to="/account/security">Open security settings</Link></section><section className="cl-card"><h2>Need help?</h2><p>For account access, class setup, papers or OMR support:</p><a href={`mailto:${support}`}>{support}</a><div className="tp-actions"><Link to="/terms">Terms</Link><Link to="/privacy">Privacy</Link></div></section></aside></div>}
  </Shell>
}
