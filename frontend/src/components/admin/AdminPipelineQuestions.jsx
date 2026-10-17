import { useEffect, useRef, useState } from 'react'
import { request } from '../../lib/api.js'
import { runPipelineImport } from '../../lib/pipelineImport.js'
import { Notice, number } from './AdminShared.jsx'

// Publication availability comes from live rows, not from whether this importer
// has a saved cursor. Questions may already have been imported by another path.
export function PublicationActions({preview,progress,busy,onPublish,onReview}) {
  const counts=preview.database.counts
  const pending=counts.add+counts.update
  const published=counts.unchanged
  const held=counts.conflict+counts.skip
  const allPublished=preview.eligible>0&&published===preview.eligible
  const exam=preview.exam||'jee_main'
  return <div className="adm-publication-actions">
    {allPublished&&<p role="status"><strong>Already published.</strong> All {number(published)} eligible questions for {preview.year} are already in the live question bank. No additional publication is needed.</p>}
    {!pending&&held>0&&<p role="status">{number(published)} already published · {number(held)} held for review. Held records are not published automatically; open their reasons below.</p>}
    {preview.eligible===0&&<p role="status">No eligible questions are available in this export. Review the source records below.</p>}
    {published>0&&<a className="btn btn-secondary" href={`/pyq?exam=${encodeURIComponent(exam)}&year=${preview.year}`}>View published {preview.year} questions</a>}
    {held>0&&<button type="button" className="btn btn-secondary" onClick={onReview}>Review held questions</button>}
    {pending>0&&<button className="btn btn-primary" type="button" disabled={busy||progress?.finished} onClick={onPublish}>{busy?'Publishing…':progress?.finished?'Import checked — refresh this year':progress?.offset>0?`Resume ${preview.year} import`:`Publish eligible ${preview.year} questions`}</button>}
  </div>
}

export default function PipelineQuestions({token,onPublished}) {
  const [exam,setExam]=useState('jee_main')
  const examName=exam==='mht_cet'?'MHT-CET':'JEE Main'
  const [years,setYears]=useState([]),[error,setError]=useState(''),[busy,setBusy]=useState(false)
  const [preview,setPreview]=useState(null),[progress,setProgress]=useState(null),[retry,setRetry]=useState('')
  const alive=useRef(true),running=useRef(false),heldRecords=useRef(null)
  useEffect(()=>{
    alive.current=true
    let current=true
    setYears([]);setPreview(null);setProgress(null);setError('')
    request(`/api/admin/pipeline-questions?exam=${exam}`,{token,cache:false,timeoutMs:60_000}).then(data=>{if(current)setYears(data.years)}).catch(e=>{if(current)setError(e.message)})
    return()=>{current=false;alive.current=false;running.current=false}
  },[token,exam])
  async function review(year) {
    setBusy(true);setError('');setProgress(null);setPreview(null)
    try {const data=await request(`/api/admin/pipeline-questions/${year}?exam=${exam}`,{token,cache:false,timeoutMs:60_000});if(alive.current){setPreview(data);setProgress(data.progress)}}
    catch(e){if(alive.current)setError(e.message)}
    finally{if(alive.current)setBusy(false)}
  }
  async function publish() {
    if(!preview||busy||preview.database.counts.add+preview.database.counts.update===0)return
    running.current=true
    setBusy(true);setError('')
    try {
      await runPipelineImport({request,token,preview,isActive:()=>alive.current&&running.current,
        onProgress:state=>{if(alive.current)setProgress(state)},onRetry:message=>{if(alive.current)setRetry(message)}})
      if(alive.current){
        onPublished?.()
        const current=await request(`/api/admin/pipeline-questions/${preview.year}?exam=${exam}`,{token,cache:false,timeoutMs:60_000})
        if(alive.current){
          setPreview(current);setProgress(current.progress)
          setYears(rows=>rows.map(row=>row.year===current.year?{...row,progress:current.progress}:row))
        }
      }
    } catch(e){if(alive.current)setError(`${e.message} Completed batches are saved. Review this year to continue from the server checkpoint.`)}
    finally{running.current=false;if(alive.current){setBusy(false);setRetry('')}}
  }
  return <section className="adm-panel" aria-labelledby="pipeline-import-title">
    <div className="adm-head"><div><p className="adm-kicker">Pinned question exports</p><h2 id="pipeline-import-title">Publish {examName} questions</h2></div></div>
    <p className="adm-description">Bring the pinned exports into the question bank. Preview checks the live database first. Publication runs in small batches and preserves existing solutions, figures and question IDs. Pending and malformed questions stay out.</p>
    <label className="adm-select">Exam<select value={exam} disabled={busy} onChange={event=>setExam(event.target.value)}><option value="jee_main">JEE Main · 2019–2025</option><option value="mht_cet">MHT-CET · 2020–2026</option></select></label>
    {exam==='mht_cet'&&<p className="adm-description">Reconstructed papers with source answer keys, not official keys. Worked solutions are not verified. Preview and publish each year explicitly.</p>}
    {error&&<Notice error={error}/>}
    <div className="adm-subnav" role="group" aria-label="Review a question dataset">{years.map(year=><button key={year.year} disabled={busy} onClick={()=>review(year.year)}>Review {year.year} · {number(year.eligible)} eligible{year.progress?.offset>0?` · ${number(year.progress.offset)} saved`:''}</button>)}</div>
    {preview&&<div>
      <p><strong>{examName} {preview.year}</strong> · {number(preview.eligible)} eligible · {number(preview.verified_solutions)} with checked solutions · {number(preview.figures)} figures</p>
      <p className="adm-description">{number(preview.database.counts.add)} new · {number(preview.database.counts.update)} safe updates · {number(preview.database.counts.unchanged)} already current · {number(preview.database.counts.conflict+preview.database.counts.skip)} held in the database</p>
      <p className="adm-description">{number(preview.blocked.length)} malformed source records and {number(preview.source_pending)} pending source questions will not be published. The archive may contain partial shifts. Checked keys do not mean every worked solution has been independently verified.</p>
      {(preview.blocked.length>0||preview.database.issues.length>0)&&<details ref={heldRecords}><summary>View records held for review</summary><ul>{[...preview.blocked,...preview.database.issues].map((issue,i)=><li key={`${issue.ref}-${i}`}><strong>{issue.ref}</strong>: {issue.reason}</li>)}</ul></details>}
      <PublicationActions preview={preview} progress={progress} busy={busy} onPublish={publish} onReview={()=>{if(heldRecords.current){heldRecords.current.open=true;heldRecords.current.scrollIntoView({block:'nearest',behavior:'smooth'});heldRecords.current.querySelector('summary')?.focus()}}}/>
      {busy&&running.current&&<button type="button" className="btn btn-secondary" onClick={()=>{running.current=false;setRetry('Pausing after the current batch is confirmed…')}}>Pause import</button>}
    </div>}
    {retry&&<p role="status">{retry}</p>}
    {progress&&<div role="status" aria-live="polite"><progress max={progress.total} value={progress.offset} aria-label="Question import progress" style={{width:'100%',marginTop:16}}/><p>{progress.finished?'Import check completed':busy?'Publishing':'Saved progress'} · {number(progress.offset)} / {number(progress.total)} processed</p><p>{number(progress.added)} added · {number(progress.updated)} updated · {number(progress.unchanged)} already current · {number(progress.conflicts+progress.skipped)} held</p></div>}
  </section>
}
