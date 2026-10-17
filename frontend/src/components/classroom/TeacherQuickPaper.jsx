import { useMemo, useRef, useState } from 'react'
import { ArrowRight, Check, ChevronDown, FileText, LoaderCircle, Search, SlidersHorizontal, X } from 'lucide-react'
import { classApi, ErrorMessage, LoadState, useLoad } from './shared.jsx'
import { paperExams, paperSubjects, defaultMarking, quickPaperBody, quickPaperProblem } from '../../lib/teacherQuickPaper.js'
import TeacherPaperDownloads from './TeacherPaperDownloads.jsx'
import './teacher-quick-paper.css'

const initial={exam:'jee_main',scope:'all',count:30,duration:60,method:'topics',chapters:[],reference:'',fullPaper:false,
  level:'balanced',source:'all',type:'',sets:false,title:'',instructions:'',correct:'',wrong:''}

export default function TeacherQuickPaper({references,onCreated,onOpen,onAdvanced,onBusy}) {
  const [form,setForm]=useState(initial),[search,setSearch]=useState(''),[paperSearch,setPaperSearch]=useState('')
  const [result,setResult]=useState(null),[busy,setBusy]=useState(false),[error,setError]=useState('')
  const pending=useRef(null)
  const chapterInput=useRef(null),chapterResults=useRef(null)
  const catalog=useLoad(`/teacher/papers/catalog?exam=${form.exam}`)
  const set=(key,value)=>{setForm(previous=>({...previous,[key]:value}));setError('')}
  const allChapters=catalog.data?.chapters||[]
  const selectedChapters=allChapters.filter(chapter=>form.chapters.includes(chapter.id))
  const chapterMatches=useMemo(()=>allChapters.filter(c=>(form.scope==='all'||form.scope.split(',').includes(c.subject))&&c.name.toLowerCase().includes(search.trim().toLowerCase())&&!form.chapters.includes(c.id)).slice(0,12),[allChapters,search,form.scope,form.chapters])
  const papers=(references.data?.papers||[]).filter(p=>p.exam===form.exam)
  const reference=papers.find(p=>JSON.stringify([p.year,p.shift])===form.reference)
  const visiblePapers=papers.filter(p=>`${p.year} ${p.shift||'no shift label'}`.toLowerCase().includes(paperSearch.trim().toLowerCase())).sort((a,b)=>b.year-a.year||String(a.shift).localeCompare(String(b.shift)))
  const chosenSubjects=[...new Set(selectedChapters.map(chapter=>chapter.subject))]
  const marking=defaultMarking(form.exam,chosenSubjects.length===1?chosenSubjects[0]:form.scope)
  const exact=form.method==='reference'&&form.fullPaper
  const problem=quickPaperProblem(form,reference)
  const mixedCet=form.exam==='mht_cet'&&(exact||(chosenSubjects.length?chosenSubjects.includes('MATH')&&chosenSubjects.length>1:form.scope==='all'))
  function changeExam(exam) {
    setForm(previous=>({...previous,exam,scope:exam==='mht_cet'?'PHY':'all',chapters:[],reference:'',correct:'',wrong:''}));setSearch('');setPaperSearch('');setError('')
  }
  function changeMethod(method){setForm(previous=>({...previous,method,fullPaper:false,reference:'',chapters:[]}));setError('')}
  function addChapter(chapter){set('chapters',[...form.chapters,chapter.id]);setSearch('');chapterInput.current?.focus()}
  async function create(event) {
    event.preventDefault()
    if(busy)return
    if(search.trim()){setError('Choose a chapter from the results, or clear the chapter search.');return}
    if(problem){setError(problem);return}
    const body=quickPaperBody(form,reference,'')
    const signature=JSON.stringify(body)
    if(pending.current?.signature!==signature)pending.current={signature,key:crypto.randomUUID()}
    body.request_key=pending.current.key
    setBusy(true);onBusy(true);setError('')
    try {
      const ready=await classApi('/teacher/papers/quick-create',{method:'POST',body,timeoutMs:40_000})
      setResult(ready);onCreated(ready.paper)
    }catch(e){setError(e.message)}finally{setBusy(false);onBusy(false)}
  }
  if(result)return <div className="qp-studio"><TeacherPaperDownloads result={result} onOpen={onOpen}/></div>
  return <section className="qp-studio" aria-label="Quick paper creator">
    <header className="qp-intro"><div><span className="qp-eyebrow">CREATE A PAPER</span><h2>A few choices. Ready to print.</h2><p>Pick what to test. We’ll assemble the paper and matching OMR.</p></div><button type="button" className="btn btn-quiet" onClick={()=>onAdvanced({...form,correct:form.correct!==''?form.correct:String(marking.correct),wrong:form.wrong!==''?form.wrong:String(marking.wrong)})}><SlidersHorizontal size={16}/>Choose questions myself</button></header>
    <form className="qp-builder" onSubmit={create}>
      <fieldset disabled={busy} className="qp-fields">
        <div className="qp-exams" role="group" aria-label="Exam">{Object.entries(paperExams).map(([code,label])=><button type="button" key={code} aria-pressed={form.exam===code} onClick={()=>changeExam(code)}>{label}</button>)}</div>
        <div className="qp-presets" role="group" aria-label="Paper size presets"><span>Start with</span>{[[10,20,'Quick quiz'],[30,60,'Chapter test'],[60,120,'Long practice']].map(([count,duration,label])=><button type="button" key={count} aria-pressed={Number(form.count)===count&&Number(form.duration)===duration} onClick={()=>setForm(previous=>({...previous,count,duration}))}>{label}<small>{count} questions</small></button>)}</div>
        <div className="qp-methods" role="group" aria-label="Question selection"><button type="button" aria-pressed={form.method==='topics'} onClick={()=>changeMethod('topics')}>Subjects & chapters</button><button type="button" aria-pressed={form.method==='reference'} onClick={()=>changeMethod('reference')}>Past paper / shift</button></div>
        {form.method==='reference'&&<div className="qp-reference"><LoadState {...references}/><label>Find a paper<Search size={15}/><input type="search" value={paperSearch} onChange={e=>{setPaperSearch(e.target.value);set('reference','')}} placeholder="Search year, date or shift"/></label><label>Past paper<select value={form.reference} onChange={e=>set('reference',e.target.value)}><option value="">Choose a paper</option>{visiblePapers.map(p=><option key={JSON.stringify([p.year,p.shift])} value={JSON.stringify([p.year,p.shift])}>{p.year} · {p.shift||'No shift label'} · {p.count} questions</option>)}</select></label><label className="qp-check"><input type="checkbox" checked={form.fullPaper} onChange={e=>set('fullPaper',e.target.checked)}/>Use the full available paper{reference?` (${reference.count} questions)`:''}</label></div>}
        {!exact&&<>
          <div className="qp-scope"><label>Subject<select value={form.scope} onChange={e=>{setForm(previous=>({...previous,scope:e.target.value,chapters:[]}));setSearch('')}}><option value="all">All subjects</option>{Object.entries(paperSubjects).filter(([code])=>form.exam==='bitsat'||!['ENG','LR'].includes(code)).map(([code,label])=><option key={code} value={code}>{label}</option>)}{form.exam==='mht_cet'&&<option value="PHY,CHEM">Physics & Chemistry</option>}</select></label><label className="qp-topic-search">Chapters <span>optional</span><div><Search size={17}/><input ref={chapterInput} type="search" value={search} onChange={e=>setSearch(e.target.value)} onKeyDown={e=>{if(e.key==='Escape')setSearch('');if((e.key==='Enter'||e.key==='ArrowDown')&&search.trim()){e.preventDefault();if(e.key==='Enter'&&chapterMatches.length===1)addChapter(chapterMatches[0]);else chapterResults.current?.querySelector('button')?.focus()}}} placeholder="Type a chapter, e.g. Electrostatics" aria-controls="quick-chapter-results"/></div></label></div>
          {!!selectedChapters.length&&<div className="qp-selected" aria-label="Selected chapters">{selectedChapters.map(chapter=><button type="button" key={chapter.id} onClick={()=>set('chapters',form.chapters.filter(id=>id!==chapter.id))}>{chapter.name}<X size={13}/><span className="sr-only">Remove chapter</span></button>)}<button type="button" className="qp-clear" onClick={()=>set('chapters',[])}>Clear</button></div>}
          <LoadState {...catalog}/>
          {search.trim()&&!catalog.loading&&!catalog.error&&<div ref={chapterResults} id="quick-chapter-results" className="qp-topic-results" aria-label="Matching chapters">{chapterMatches.length?chapterMatches.map(chapter=><button type="button" key={chapter.id} onClick={()=>addChapter(chapter)}><span>{chapter.name}<small>{paperSubjects[chapter.subject]}</small></span><span>{chapter.count} in bank <Check size={15}/></span></button>):<p>No matching chapters. Try a different name or subject.</p>}</div>}
          <p className="qp-scope-hint">{selectedChapters.length?`${selectedChapters.length} chapter${selectedChapters.length===1?'':'s'} selected`:`All chapters in ${form.scope==='all'?'the selected exam':paperSubjects[form.scope]||'Physics & Chemistry'}`}</p>
        </>}
        <div className="qp-numbers">{!exact?<label>Questions<input type="number" min="1" max="200" required value={form.count} onChange={e=>set('count',e.target.value)}/></label>:<div className="qp-full-count"><span>Questions</span><strong>{reference?.count||'—'}</strong><small>Full available paper</small></div>}<label>Duration <span>minutes</span><input type="number" min="1" max="240" required value={form.duration} onChange={e=>set('duration',e.target.value)}/></label><label className="qp-set-choice">Paper versions<select value={form.sets?'two':'one'} onChange={e=>set('sets',e.target.value==='two')}><option value="one">One paper</option><option value="two">Two shuffled sets · A & B</option></select></label></div>
        <details className="qp-options"><summary>More options <span>Difficulty, marking, title & format</span><ChevronDown size={16}/></summary><div className="qp-options-grid"><label>Difficulty<select value={form.level} onChange={e=>set('level',e.target.value)} disabled={exact}><option value="easy">Easy</option><option value="balanced">Balanced</option><option value="hard">Hard</option></select></label><label>Format<select value={form.type} onChange={e=>set('type',e.target.value)} disabled={exact}><option value="">All supported formats</option><option value="single_correct">Single correct MCQs</option><option value="multi_correct">Multiple correct</option><option value="numerical">Numerical</option></select></label>{form.method==='topics'&&<label>Source<select value={form.source} onChange={e=>set('source',e.target.value)}><option value="all">All available questions</option><option value="pyq">Previous-year questions</option><option value="original">Original questions</option></select></label>}<label>Correct-answer marks<input type="number" min="1" max="10" value={form.correct} placeholder={`${marking.correct} (default)`} onChange={e=>set('correct',e.target.value)}/></label><label>Wrong-answer deduction<input type="number" min="0" max="10" value={form.wrong} placeholder={`${marking.wrong} (default)`} onChange={e=>set('wrong',e.target.value)}/></label><label className="qp-wide">Paper title <span>optional</span><input value={form.title} maxLength={150} placeholder="Created automatically if left blank" onChange={e=>set('title',e.target.value)}/></label><label className="qp-wide">Instructions <span>optional</span><textarea value={form.instructions} rows={2} maxLength={2000} onChange={e=>set('instructions',e.target.value)}/></label></div></details>
        {mixedCet&&<p className="qp-notice">Mixed MHT-CET subjects use one marking value for the whole paper. Set it under More options, or choose Mathematics separately.</p>}
        <ErrorMessage error={error}/>
        <footer className="qp-create"><span><FileText size={17}/>{exact?'Full paper':`${form.count||'—'} questions`} · {form.duration||'—'} minutes<small>Paper + matching OMR · {form.sets?'Sets A & B':'One paper'}{!mixedCet?` · +${form.correct||marking.correct} / −${form.wrong!==''?form.wrong:marking.wrong}`:''}</small></span><button className="btn btn-primary" type="submit" disabled={busy||catalog.loading||!!catalog.error||!!search.trim()||(form.method==='reference'&&(references.loading||!!references.error))}>{busy?<LoaderCircle size={17} className="spin"/>:<ArrowRight size={17}/>}<span>{busy?'Creating your paper…':'Create paper & OMR'}</span></button></footer>
        {search.trim()&&<p className="qp-scope-hint" role="status">Choose a chapter from the results, or clear your search to use all chapters.</p>}
      </fieldset>
    </form>
  </section>
}
