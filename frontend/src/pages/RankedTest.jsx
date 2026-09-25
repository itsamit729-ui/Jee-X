import { useEffect, useRef, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { request } from '../lib/api.js'
import MathText from '../components/MathText.jsx'
import QuestionAssets from '../components/QuestionAssets.jsx'
import AppHeader from '../components/AppHeader.jsx'
import { useCrackJeeStyles } from '../crackjee/screens.jsx'
import '../ranking.css'

export default function RankedTest() {
  useCrackJeeStyles()
  const { id } = useParams()

  const [attempt,setAttempt]=useState(null), [answers,setAnswers]=useState({}), [error,setError]=useState(''), [status,setStatus]=useState(''), [remaining,setRemaining]=useState(0), [done,setDone]=useState(false), [busy,setBusy]=useState(false)
  const latest=useRef({}), queue=useRef(Promise.resolve()), offset=useRef(0)
  useEffect(()=>{
    let alive=true
    ;(async()=>{try {
      const a=await request(`/api/ranking/contests/${id}/start`,{method:'POST'})
      if(!alive)return
      offset.current=Date.parse(a.server_time)-Date.now()
      latest.current=a.answers; setAnswers(a.answers); setAttempt(a)
      setRemaining(Math.max(0,Math.ceil((Date.parse(a.deadline)-Date.now()-offset.current)/1000)))
    }catch(e){if(alive)setError(e.message)}})()
    return()=>{alive=false}
  },[id])
  useEffect(()=>{
    if(!attempt||done)return
    const tick=()=>{const n=Math.max(0,Math.ceil((Date.parse(attempt.deadline)-Date.now()-offset.current)/1000));setRemaining(n);if(n===0){setDone(true);setStatus('Time is up. Answers saved before the deadline will be graded.')}}
    const timer=setInterval(tick,500)
    return()=>clearInterval(timer)
  },[attempt,done])
  useEffect(()=>{
    if(!attempt||done)return
    const warn=e=>{e.preventDefault();e.returnValue=''}
    window.addEventListener('beforeunload',warn)
    return()=>window.removeEventListener('beforeunload',warn)
  },[attempt,done])
  function save(next,submit=false) {
    setStatus('Saving…')
    // Serialize requests so an older autosave cannot overwrite a newer answer.
    const job=queue.current.catch(()=>{}).then(async()=>{
      await request(`/api/ranking/entries/${attempt.id}`,{method:'PUT',body:{answers:Object.values(next),submit}})
      setError('');setStatus(submit?'Submitted. Results arrive after the contest closes.':'All answers saved')
      if(submit)setDone(true)
    })
    queue.current=job
    return job.catch(e=>{setError(e.message);setStatus('Save failed — retry before the timer ends.');throw e})
  }
  function update(q,value) {
    const next={...latest.current,[q.id]:{question_id:q.id,option_ids:[],numeric_answer:null,...value}}
    latest.current=next;setAnswers(next)
    save(next).catch(()=>{})
  }
  async function submit() {
    if(!window.confirm('Submit this contest? You cannot change answers afterwards.'))return
    setBusy(true)
    try{await save(latest.current,true)}catch{}finally{setBusy(false)}
  }
  return <div className="crackjee-root"><AppHeader/><main className="wrap ranking-page"><Link className="ranking-back" to="/ranking">← Back to rankings</Link><div className="ranking-heading"><div><p className="ranking-eyebrow">RATED CONTEST</p><h1>{attempt?.title || 'Contest arena'}</h1><p>+4 correct · −1 wrong · 0 skipped. No partial credit.</p></div>{attempt&&!done&&<strong className="contest-clock" aria-label="Time remaining">{Math.floor(remaining/60)}:{String(remaining%60).padStart(2,'0')}</strong>}</div>
    {error&&<div className="ranking-panel" role="alert">{error} {attempt&&!done&&<button onClick={()=>save(latest.current).catch(()=>{})} className="btn btn-secondary btn-sm">Retry save</button>}</div>}
    {!attempt&&!error&&<p role="status">Opening your attempt…</p>}
    <p role="status" className="ranking-muted">{status}</p>
    {done?<section className="ranking-panel"><h2>Your attempt has ended.</h2><p>Rating changes are published once the contest closes. Your saved answers are retained.</p><Link to="/ranking" className="btn btn-primary">View rankings</Link></section>:attempt&&<><div className="contest-note">Answers save as you work. Reopening this page resumes the same timer. Check the save status before leaving.</div>{attempt.questions.map((q,i)=><section className="ranking-panel contest-question" key={q.id}><p className="ranking-eyebrow">QUESTION {i+1} / {attempt.questions.length} · {q.type.replaceAll('_',' ')}</p>{q.passage&&<blockquote><MathText text={q.passage}/></blockquote>}<h2><MathText text={q.stem}/></h2><QuestionAssets assets={q.assets}/><fieldset disabled={busy}><legend className="sr-only">Answer question {i+1}</legend>{q.type==='numerical'?<label className="numeric-answer">Your numerical answer<input type="number" step="any" value={answers[q.id]?.numeric_answer??''} onChange={e=>update(q,{numeric_answer:e.target.value===''?null:Number(e.target.value)})}/></label>:q.options.map(o=><label className="contest-option" key={o.id}><input type={q.type==='multi_correct'?'checkbox':'radio'} name={`q-${q.id}`} checked={(answers[q.id]?.option_ids||[]).includes(o.id)} onChange={()=>{const old=answers[q.id]?.option_ids||[];update(q,{option_ids:q.type==='multi_correct'?old.includes(o.id)?old.filter(x=>x!==o.id):[...old,o.id]:[o.id]})}}/><span className="option-label">{o.label}</span><MathText text={o.content}/></label>)}<button className="visibility-button" onClick={()=>update(q,{})}>Clear answer</button></fieldset></section>)}<div className="contest-submit"><span>{Object.values(answers).filter(a=>a.option_ids?.length||a.numeric_answer!=null).length} / {attempt.questions.length} answered</span><button className="btn btn-primary" disabled={busy||remaining===0} onClick={submit}>{busy?'Submitting…':'Submit contest'}</button></div></>}
  </main></div>
}

