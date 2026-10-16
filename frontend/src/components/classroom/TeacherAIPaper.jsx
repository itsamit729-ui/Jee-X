import { useEffect, useRef, useState } from 'react'
import { Sparkles, Download, ArrowRight } from 'lucide-react'
import { classApi, ErrorMessage } from './shared.jsx'
import { downloadTeacherFile } from '../../lib/teacherPaper.js'

const subjects={PHY:'Physics',CHEM:'Chemistry',MATH:'Mathematics',ENG:'English',LR:'Logical reasoning'}
export default function TeacherAIPaper({exam, defaults, onCreated, onOpen, onBusy}) {
  const inputRef=useRef(null)
  const [input,setInput]=useState(''),[messages,setMessages]=useState([]),[result,setResult]=useState(null),[pending,setPending]=useState(null)
  const [busy,setBusy]=useState(false),[error,setError]=useState(''),[progress,setProgress]=useState('')
  useEffect(()=>{if(!busy&&!result)inputRef.current?.focus()},[busy,result,messages.length])
  async function run(fn){setBusy(true);onBusy(true);setError('');try{await fn()}catch(e){setError(e.message)}finally{setBusy(false);onBusy(false);setProgress('')}}
  async function submit(retry=false) {
    const turns=retry?pending.messages:[...messages,{role:'teacher',text:input.trim()}]
    const request=retry?pending:{messages:turns,key:crypto.randomUUID(),prompt:turns.map(m=>`${m.role}: ${m.text}`).join('\n')}
    if(!request)return
    if(request.prompt.length>6000){setError('This conversation is too long. Start a new request with the complete paper requirements.');return}
    if(!retry){setMessages(turns);setInput('');setPending(request)}
    await run(async()=>{
      const next=await classApi('/teacher/papers/ai-create',{method:'POST',body:{prompt:request.prompt,exam,defaults,request_key:request.key},timeoutMs:40_000})
      if(next.state==='needs_details'){setMessages([...turns,{role:'assistant',text:next.question}]);setPending(null)}
      else{setResult(next);setPending(null);onCreated(next.paper)}
    })
  }
  function reset(){setInput('');setMessages([]);setResult(null);setPending(null);setError('')}
  const paper=result?.paper,counts={}
  paper?.questions.forEach(q=>{counts[q.subject]=(counts[q.subject]||0)+1})
  const variants=paper?.sets_enabled?['A','B']:['A']
  return <section className="cl-card tp-form tp-ai"><div><span className="cl-eyebrow">OPTIONAL · AI ASSISTANT</span><h2>Describe it. Download it.</h2><p>Tell us what you need. We’ll ask only for missing details, then prepare your question paper and matching OMR sheet.</p></div><small>{exam.replaceAll('_',' ').toUpperCase()} · {defaults.duration_minutes} minutes · +{defaults.marks_correct} / −{defaults.marks_wrong} · {defaults.sets_enabled?'Sets A and B':'Single paper'}. Include any changes in your message.</small>{messages.length>0&&<div className="tp-ai-chat" role="log" aria-label="Paper creation conversation">{messages.map((m,i)=><div className={`tp-ai-message ${m.role}`} key={i}><strong>{m.role==='teacher'?'You':'Jee Edge'}</strong><p>{m.text}</p></div>)}</div>}{!paper&&<><label>{messages.at(-1)?.role==='assistant'?'Your reply':messages.length?'Add or change requirements':'Your request'}<textarea ref={inputRef} rows={messages.length?2:4} maxLength={1500} value={input} onChange={e=>setInput(e.target.value)} placeholder={messages.length?'Reply with the missing detail…':'Create 30 JEE Main questions from electrostatics and current electricity, balanced difficulty, for a 60-minute test.'}/></label>{!messages.length&&<button type="button" className="btn btn-quiet" onClick={()=>setInput('Create 30 questions with 10 each in Physics, Chemistry and Mathematics, balanced difficulty, for 60 minutes.')}>Try a balanced 30-question paper</button>}<div className="tp-actions"><button className="btn btn-primary" type="button" disabled={busy||input.trim().length<(messages.length?1:10)} onClick={()=>submit()}><Sparkles size={17}/>{busy?'Preparing your paper…':messages.at(-1)?.role==='assistant'?'Send reply':messages.length?'Update request':'Create paper & OMR'}</button>{pending&&!busy&&error&&<button className="btn btn-secondary" type="button" onClick={()=>submit(true)}>Retry same request</button>}</div></>}{busy&&<p role="status">{progress||'Checking your request and preparing the downloads…'}</p>}<ErrorMessage error={error}/>{paper&&<div className="tp-ai-draft" role="region" aria-label="Paper downloads"><div><span className="cl-eyebrow">READY TO DOWNLOAD</span><h3>{paper.title}</h3><p>{paper.questions.length} questions · {paper.settings.duration_minutes} minutes · +{paper.settings.marks_correct} / −{paper.settings.marks_wrong}</p><p>{Object.entries(counts).map(([s,n])=>`${subjects[s]||s}: ${n}`).join(' · ')}</p></div>{variants.map(variant=><div className="tp-actions" key={variant}><button className="btn btn-primary" type="button" disabled={busy} onClick={()=>run(async()=>{const {downloadPaperPdf}=await import('../../lib/teacherPaperPdf.jsx');await downloadPaperPdf(paper,variant,setProgress)})}><Download size={16}/>Download paper PDF{paper.sets_enabled?` · Set ${variant}`:''}</button><button className="btn btn-secondary" type="button" disabled={busy} onClick={()=>run(()=>downloadTeacherFile(result.downloads.find(d=>d.variant===variant).omr,`omr-${paper.id}-${variant}.pdf`))}><Download size={16}/>Download OMR PDF{paper.sets_enabled?` · Set ${variant}`:''}</button></div>)}<small>Saved in your paper library. Print each question paper with its matching OMR sheet at A4, 100% scale. Nothing is assigned to students automatically.</small><button className="btn btn-quiet" type="button" onClick={()=>onOpen(paper)}>Open saved paper<ArrowRight size={15}/></button></div>}{messages.length>0&&<button className="btn btn-quiet" type="button" disabled={busy} onClick={reset}>Create another paper</button>}<small>Manual generation, bank selection and private questions remain available.</small></section>
}
