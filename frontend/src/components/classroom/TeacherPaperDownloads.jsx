import { useEffect, useRef, useState } from 'react'
import { ArrowRight, Check, Download, FileText, LoaderCircle, ScanLine } from 'lucide-react'
import { downloadTeacherFile } from '../../lib/teacherPaper.js'
import { ErrorMessage } from './shared.jsx'

export default function TeacherPaperDownloads({result,onOpen}) {
  const paper=result.paper,variants=paper.sets_enabled?['A','B']:['A']
  const [files,setFiles]=useState({}),[error,setError]=useState(''),[downloading,setDownloading]=useState('')
  const heading=useRef(null)
  const preparing=useRef(new Set()),alive=useRef(true)
  async function prepareVariant(variant){
    if(preparing.current.has(variant))return
    preparing.current.add(variant)
    setFiles(state=>({...state,[variant]:{status:'preparing',percent:2}}))
    try{
      const {preparePaperPdf}=await import('../../lib/teacherPaperPdf.jsx')
      await preparePaperPdf(paper,variant,progress=>{if(alive.current)setFiles(state=>({...state,[variant]:{status:'preparing',...progress}}))})
      if(alive.current)setFiles(state=>({...state,[variant]:{status:'ready',percent:100}}))
    }catch(e){if(alive.current)setFiles(state=>({...state,[variant]:{status:'error',error:e.message}}))}
    finally{preparing.current.delete(variant)}
  }
  useEffect(()=>{
    let active=true
    alive.current=true
    heading.current?.focus({preventScroll:true})
    async function prepare() {
      for(const v of (paper.sets_enabled?['A','B']:['A'])) {
        if(!active)return
        await prepareVariant(v)
      }
    }
    const timer=setTimeout(prepare,120)
    return()=>{active=false;alive.current=false;clearTimeout(timer)}
  },[paper])
  async function download(variant,omr) {
    if(downloading||(!omr&&files[variant]?.status!=='ready'))return
    setDownloading(`${variant}-${omr?'omr':'paper'}`);setError('')
    try {
      if(omr)await downloadTeacherFile(result.downloads.find(d=>d.variant===variant).omr,`omr-${paper.id}-${variant}.pdf`)
      else {
        const {downloadPaperPdf}=await import('../../lib/teacherPaperPdf.jsx')
        await downloadPaperPdf(paper,variant)
        setFiles(state=>({...state,[variant]:{status:'ready',percent:100}}))
      }
    }catch(e){setError(e.message)}finally{setDownloading('')}
  }
  return <section className="qp-result" aria-label="Paper downloads">
    <header ref={heading} tabIndex={-1}><span className="qp-success"><Check size={23}/></span><div><span className="qp-eyebrow">SAVED & READY</span><h2>Your paper is ready</h2><p>{paper.title}</p></div></header>
    <p className="qp-result-summary">{paper.questions.length} questions <span>·</span> {paper.settings.duration_minutes} minutes <span>·</span> +{paper.settings.marks_correct} / −{paper.settings.marks_wrong}</p>
    <div className="qp-downloads">{variants.map(v=>{
      const state=files[v]||{status:'queued'},ready=state.status==='ready'
      return <article key={v}><div className="qp-download-label"><FileText size={22}/><h3>{paper.sets_enabled?`Set ${v}`:'Question paper'}</h3><span>{ready?<><Check size={13}/>PDF ready</>:state.status==='error'?'Retry available':'Preparing PDF…'}</span></div>
        {!ready&&state.status!=='error'&&<progress max="100" value={state.percent||0} aria-label={`Preparing ${v} PDF`}/>}
        {state.error&&<><p className="cl-error" role="alert">{state.error}</p><button type="button" className="btn btn-quiet" onClick={()=>prepareVariant(v)}>Retry PDF preparation</button></>}
        <button type="button" className="btn btn-primary" disabled={!!downloading||!ready} aria-busy={!ready&&state.status!=='error'} onClick={()=>download(v,false)}>{!ready||downloading===`${v}-paper`?<LoaderCircle size={16} className={!ready&&state.status==='error'?'':'spin'}/>:<Download size={16}/>}<span>{ready?'Download paper PDF':state.status==='error'?'PDF unavailable':'Preparing PDF…'}</span></button>
        <button type="button" className="btn btn-secondary" disabled={!!downloading} onClick={()=>download(v,true)}><ScanLine size={16}/>Download OMR PDF</button>
      </article>
    })}</div>
    <ErrorMessage error={error}/>
    <div className="qp-result-footer"><p>Print on A4 at 100% scale. Your paper is saved; no test has been assigned.</p><button type="button" className="btn btn-quiet" onClick={()=>onOpen(paper)}>Open paper & answer key<ArrowRight size={15}/></button></div>
  </section>
}
