import { useEffect, useRef, useState } from 'react'
import { Sparkles, Download, ArrowRight, ArrowUpRight, Check, Plus, LoaderCircle, FileText, ScanLine } from 'lucide-react'
import { classApi, ErrorMessage } from './shared.jsx'
import { downloadTeacherFile } from '../../lib/teacherPaper.js'
import './teacher-ai-paper.css'

const subjects={PHY:'Physics',CHEM:'Chemistry',MATH:'Mathematics',ENG:'English',LR:'Logical reasoning'}
const examples=[
  {label:'MHT-CET · Physics',text:'Create an MHT-CET Physics paper with 30 questions on Electrostatics, balanced difficulty, 60 minutes, and two shuffled sets A and B. Award 1 mark per correct answer with no negative marking.'},
  {label:'JEE Main · Full syllabus',text:'Create a JEE Main paper with 30 questions on the full syllabus, balanced difficulty, for 60 minutes.'},
]
export default function TeacherAIPaper({onCreated, onOpen, onBusy}) {
  const inputRef=useRef(null),chatRef=useRef(null),readyRef=useRef(null)
  const [input,setInput]=useState(''),[messages,setMessages]=useState([]),[result,setResult]=useState(null),[pending,setPending]=useState(null)
  const [busy,setBusy]=useState(false),[error,setError]=useState(''),[pdfs,setPdfs]=useState({}),[downloading,setDownloading]=useState(''),[omrBusy,setOmrBusy]=useState('')
  const [retryWait,setRetryWait]=useState(0)
  const waiting=retryWait>0
  useEffect(()=>{if(!waiting)return;const timer=setInterval(()=>setRetryWait(value=>Math.max(0,value-1)),1000);return()=>clearInterval(timer)},[waiting])
  const paper=result?.paper
  const currentPaper=useRef(paper);currentPaper.current=paper
  useEffect(()=>{if(!busy&&!paper)inputRef.current?.focus()},[busy,paper,messages.length])
  useEffect(()=>{if(chatRef.current)chatRef.current.scrollTop=chatRef.current.scrollHeight},[messages.length])
  useEffect(()=>{
    if(!paper)return
    let active=true
    readyRef.current?.focus({preventScroll:true})
    const variants=paper.sets_enabled?['A','B']:['A']
    setPdfs(Object.fromEntries(variants.map(v=>[v,{status:'queued',percent:0}])))
    async function prepare() {
      try {
        const {preparePaperPdf}=await import('../../lib/teacherPaperPdf.jsx')
        for(const variant of variants) {
          if(!active)return
          setPdfs(state=>({...state,[variant]:{status:'preparing',percent:2}}))
          await preparePaperPdf(paper,variant,value=>{if(active)setPdfs(state=>({...state,[variant]:{status:'preparing',...value}}))})
          if(active)setPdfs(state=>({...state,[variant]:{status:'ready',percent:100}}))
        }
      } catch(e) {
        if(active)setPdfs(state=>Object.fromEntries(variants.map(v=>[v,state[v]?.status==='ready'?state[v]:{status:'error',error:e.message}])))
      }
    }
    // Let the ready screen paint before starting the print work.
    const timer=setTimeout(prepare,120)
    return()=>{active=false;clearTimeout(timer)}
  },[paper])

  async function submit(retry=false) {
    const turns=retry?pending?.messages:[...messages,{role:'teacher',text:input.trim()}]
    const request=retry?pending:{messages:turns,key:crypto.randomUUID(),prompt:turns.map(m=>`${m.role}: ${m.text}`).join('\n')}
    if(!request||busy||(retry&&waiting))return
    if(request.prompt.length>6000){setError('This conversation is too long. Start a new request with the complete paper requirements.');return}
    if(!retry){setMessages(turns);setInput('');setPending(request)}
    setBusy(true);onBusy(true);setError('');setRetryWait(0)
    try {
      const next=await classApi('/teacher/papers/ai-create',{method:'POST',body:{prompt:request.prompt,strict_details:true,request_key:request.key},timeoutMs:40_000})
      if(next.state==='needs_details'){setMessages([...turns,{role:'assistant',text:next.question}]);setPending(null)}
      else{setResult(next);setPending(null);onCreated(next.paper)}
    } catch(e){setError(e.message);if(e.status===429)setRetryWait(e.retryAfter||60)}
    finally{setBusy(false);onBusy(false)}
  }
  async function download(variant,omr=false) {
    const saved=paper
    if(omr)setOmrBusy(variant);else setDownloading(variant)
    setError('')
    try {
      if(omr)await downloadTeacherFile(result.downloads.find(d=>d.variant===variant).omr,`omr-${paper.id}-${variant}.pdf`)
      else {
        const {downloadPaperPdf}=await import('../../lib/teacherPaperPdf.jsx')
        await downloadPaperPdf(paper,variant)
        if(currentPaper.current===saved)setPdfs(state=>({...state,[variant]:{status:'ready',percent:100}}))
      }
    } catch(e){if(currentPaper.current===saved)setError(e.message)}
    finally{if(currentPaper.current===saved){if(omr)setOmrBusy('');else setDownloading('')}}
  }
  function reset(){setInput('');setMessages([]);setResult(null);setPending(null);setError('');setPdfs({});setDownloading('');setOmrBusy('');setRetryWait(0)}
  function editRequest(){if(!pending)return;setMessages(pending.messages.slice(0,-1));setInput(pending.messages.at(-1).text);setPending(null);setError('');setRetryWait(0);inputRef.current?.focus()}
  const variants=paper?.sets_enabled?['A','B']:['A'],counts={}
  paper?.questions.forEach(q=>{counts[q.subject]=(counts[q.subject]||0)+1})
  const followup=messages.at(-1)?.role==='assistant'
  const conversation=<div className="tp-ai-chat ai-conversation" ref={chatRef} role="log" aria-label="Paper creation conversation">{messages.map((m,i)=><div className={`tp-ai-message ${m.role}`} key={i}><strong>{m.role==='teacher'?'Your request':'Jee Edge · A little more detail'}</strong><p>{m.text}</p></div>)}</div>
  return <section className="studio-ai" aria-label="AI paper creator">
    {!paper?<>
      <header className="ai-intro"><span className="ai-eyebrow"><Sparkles size={15}/>AI PAPER STUDIO</span><h2>What are we testing today?</h2><p>Describe your test. We’ll find the questions and prepare the paper and OMR.</p></header>
      {messages.length>0&&conversation}
      <form className={`ai-composer${followup?' has-followup':''}`} onSubmit={e=>{e.preventDefault();submit()}}>
        <label htmlFor="ai-paper-request">{followup?'Add the missing details':'Describe your paper'}</label>
        <textarea id="ai-paper-request" ref={inputRef} rows={messages.length?3:4} maxLength={1500} disabled={busy} value={input} onChange={e=>setInput(e.target.value)} onKeyDown={e=>{if(e.key==='Enter'&&(e.ctrlKey||e.metaKey)){e.preventDefault();if(input.trim().length>=1)submit()}}} placeholder={messages.length?'Reply here — your earlier details are remembered.':'30 MHT-CET Physics questions on Electrostatics, 60 minutes, balanced difficulty, two shuffled sets…'} aria-describedby="ai-request-help"/>
        <div className="ai-composer-footer"><span id="ai-request-help">Exam · Question count · Topics · Duration</span><button className="btn btn-primary" type="submit" disabled={busy||!input.trim().length}>{busy?<LoaderCircle size={17} className="spin"/>:<ArrowRight size={17}/>}<span>{busy?'Creating your paper…':followup?'Send details':'Create paper & OMR'}</span></button></div>
      </form>
      {!messages.length&&<div className="ai-examples"><span>Try an example</span>{examples.map(example=><button type="button" key={example.label} onClick={()=>{setInput(example.text);inputRef.current?.focus()}}>{example.label}<ArrowUpRight size={14}/></button>)}</div>}
      {busy&&<div className="ai-creating" role="status"><span className="ai-pulse"/><span>Finding matching questions and saving your paper…</span></div>}
      {pending&&!busy&&error&&<div className="tp-actions"><button className="btn btn-secondary" type="button" disabled={waiting} onClick={()=>submit(true)}>{waiting?(retryWait>60?`Retry in ${Math.ceil(retryWait/60)} min`:`Retry in ${retryWait}s`):'Retry same request'}</button><button className="btn btn-quiet" type="button" onClick={editRequest}>Edit request</button><span>Your request is kept here. You can edit it now.</span></div>}
      <p className="ai-note">We’ll ask if anything is missing. Balanced difficulty and one set are the defaults; marking follows your exam.</p>
    </>:<>
      <header className="ai-ready-head" ref={readyRef} tabIndex={-1}><span className="ai-success-icon"><Check size={23}/></span><div><span className="ai-eyebrow">SAVED TO YOUR LIBRARY</span><h2>Your paper is ready.</h2><p>{paper.title}</p></div></header>
      <div className="ai-paper-metrics"><div><strong>{paper.questions.length}</strong><span>questions</span></div><div><strong>{paper.settings.duration_minutes}<small> min</small></strong><span>duration</span></div><div><strong>+{paper.settings.marks_correct} / −{paper.settings.marks_wrong}</strong><span>marking</span></div><p>{Object.entries(counts).map(([s,n])=>`${subjects[s]||s} · ${n}`).join('  /  ')}</p></div>
      <div className="ai-download-grid" role="region" aria-label="Paper downloads">{variants.map(variant=>{
        const state=pdfs[variant]||{status:'queued',percent:0},ready=state.status==='ready'
        return <article className="ai-download-card" key={variant}><header><span className="ai-set-label">{paper.sets_enabled?`SET ${variant}`:'YOUR PAPER'}</span><span className={`ai-file-status${ready?' ready':''}`}>{ready?<><Check size={13}/>PDF ready</>:state.status==='error'?'Preparation paused':<><LoaderCircle size={13} className="spin"/>{state.status==='queued'?'Queued':'Preparing PDF'}</>}</span></header><div className="ai-file-preview"><FileText size={25}/><div><h3>{paper.sets_enabled?`Question paper · ${variant}`:'Question paper'}</h3><p>{paper.questions.length} questions with matching OMR</p></div></div>{!ready&&state.status!=='error'&&<div className="ai-pdf-progress"><progress max="100" value={state.percent||0} aria-label={`Preparing ${paper.sets_enabled?'Set '+variant:'paper'} PDF`}/><span>{state.label||'Preparing your download…'}</span></div>}{state.error&&<p className="ai-pdf-error" role="alert">{state.error}</p>}<button className="btn btn-primary" type="button" disabled={!!downloading} onClick={()=>download(variant)}>{downloading===variant?<LoaderCircle size={16} className="spin"/>:<Download size={16}/>}<span>{downloading===variant?'Preparing download…':ready?'Download paper PDF':state.status==='error'?'Retry paper PDF':'Prepare & download PDF'}</span></button><button className="btn btn-secondary" type="button" disabled={!!omrBusy} onClick={()=>download(variant,true)}>{omrBusy===variant?<LoaderCircle size={16} className="spin"/>:<ScanLine size={16}/>}<span>{omrBusy===variant?'Downloading OMR…':'Download OMR PDF'}</span></button></article>
      })}</div>
      <p className="ai-print-note">Print each paper with its matching OMR at A4, 100% scale. Nothing is assigned to students automatically.</p>
      <div className="ai-result-actions"><button className="btn btn-secondary" type="button" disabled={!!downloading||!!omrBusy} onClick={reset}><Plus size={16}/>Create another paper</button><button className="btn btn-quiet" type="button" onClick={()=>onOpen(paper)}>Open saved paper<ArrowRight size={15}/></button></div>
      <details className="ai-request-history"><summary>Your request</summary>{conversation}</details>
    </>}
    <ErrorMessage error={error}/>
    {!paper&&messages.length>0&&!busy&&<button className="btn btn-quiet ai-start-over" type="button" onClick={reset}>Start a new request</button>}
  </section>
}
