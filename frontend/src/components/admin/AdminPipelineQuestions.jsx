import { useEffect, useRef, useState } from 'react'
import { request } from '../../lib/api.js'
import { runPipelineImport } from '../../lib/pipelineImport.js'
import { Notice, number } from './AdminShared.jsx'

export default function PipelineQuestions({token,onPublished}) {
  const [years,setYears]=useState([]),[error,setError]=useState(''),[busy,setBusy]=useState(false)
  const [preview,setPreview]=useState(null),[progress,setProgress]=useState(null),[retry,setRetry]=useState('')
  const alive=useRef(true),running=useRef(false)
  useEffect(()=>{
    alive.current=true
    request('/api/admin/pipeline-questions',{token,cache:false,timeoutMs:60_000}).then(data=>{if(alive.current)setYears(data.years)}).catch(e=>{if(alive.current)setError(e.message)})
    return()=>{alive.current=false;running.current=false}
  },[token])
  async function review(year) {
    setBusy(true);setError('');setProgress(null);setPreview(null)
    try {const data=await request(`/api/admin/pipeline-questions/${year}`,{token,cache:false,timeoutMs:60_000});if(alive.current){setPreview(data);setProgress(data.progress)}}
    catch(e){if(alive.current)setError(e.message)}
    finally{if(alive.current)setBusy(false)}
  }
  async function publish() {
    if(!preview||busy)return
    running.current=true
    setBusy(true);setError('')
    try {
      await runPipelineImport({request,token,preview,isActive:()=>alive.current&&running.current,
        onProgress:state=>{if(alive.current)setProgress(state)},onRetry:message=>{if(alive.current)setRetry(message)}})
      if(alive.current){
        onPublished?.()
        const current=await request(`/api/admin/pipeline-questions/${preview.year}`,{token,cache:false,timeoutMs:60_000})
        if(alive.current){
          setPreview(current);setProgress(current.progress)
          setYears(rows=>rows.map(row=>row.year===current.year?{...row,progress:current.progress}:row))
        }
      }
    } catch(e){if(alive.current)setError(`${e.message} Completed batches are saved. Review this year to continue from the server checkpoint.`)}
    finally{running.current=false;if(alive.current){setBusy(false);setRetry('')}}
  }
  return <section className="adm-panel" aria-labelledby="pipeline-import-title">
    <div className="adm-head"><div><p className="adm-kicker">Reviewed AI pipeline exports</p><h2 id="pipeline-import-title">Publish JEE Main questions</h2></div></div>
    <p className="adm-description">Bring the reviewed 2019–2025 exports into the question bank. Preview checks the live database first. Publication runs in small batches and preserves existing solutions, figures and question IDs. Pending and malformed questions stay out.</p>
    {error&&<Notice error={error}/>}
    <div className="adm-subnav" role="group" aria-label="Review a question dataset">{years.map(year=><button key={year.year} disabled={busy} onClick={()=>review(year.year)}>Review {year.year} · {number(year.eligible)} eligible{year.progress?.offset>0?` · ${number(year.progress.offset)} saved`:''}</button>)}</div>
    {preview&&<div>
      <p><strong>JEE Main {preview.year}</strong> · {number(preview.eligible)} eligible · {number(preview.verified_solutions)} with checked solutions · {number(preview.figures)} figures</p>
      <p className="adm-description">{number(preview.database.counts.add)} new · {number(preview.database.counts.update)} safe updates · {number(preview.database.counts.unchanged)} already current · {number(preview.database.counts.conflict+preview.database.counts.skip)} held in the database</p>
      <p className="adm-description">{number(preview.blocked.length)} malformed source records and {number(preview.source_pending)} pending source questions will not be published. The archive may contain partial shifts. Checked keys do not mean every worked solution has been independently verified.</p>
      {(preview.blocked.length>0||preview.database.issues.length>0)&&<details><summary>View records held for review</summary><ul>{[...preview.blocked,...preview.database.issues].map((issue,i)=><li key={`${issue.ref}-${i}`}><strong>{issue.ref}</strong>: {issue.reason}</li>)}</ul></details>}
      <button className="btn btn-primary" type="button" disabled={busy||progress?.finished||preview.database.counts.add+preview.database.counts.update===0} onClick={publish}>{busy?'Publishing…':progress?.finished?'Import complete':progress?.offset>0?`Resume ${preview.year} import`:`Publish eligible ${preview.year} questions`}</button>
      {busy&&running.current&&<button type="button" className="btn btn-secondary" onClick={()=>{running.current=false;setRetry('Pausing after the current batch is confirmed…')}}>Pause import</button>}
    </div>}
    {retry&&<p role="status">{retry}</p>}
    {progress&&<div role="status" aria-live="polite"><progress max={progress.total} value={progress.offset} aria-label="Question import progress" style={{width:'100%',marginTop:16}}/><p>{progress.finished?'Import completed':busy?'Publishing':'Saved progress'} · {number(progress.offset)} / {number(progress.total)} processed</p><p>{number(progress.added)} added · {number(progress.updated)} updated · {number(progress.unchanged)} already current · {number(progress.conflicts+progress.skipped)} held</p></div>}
  </section>
}
