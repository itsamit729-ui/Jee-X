import {useEffect,useRef,useState} from 'react'
import MathText from './MathText.jsx'
import QuestionAssets from './QuestionAssets.jsx'
import './test-session.css'
export const subjectNames={PHY:'Physics',CHEM:'Chemistry',MATH:'Mathematics',ENG:'English',LR:'Reasoning'}
export function clock(seconds){const n=Math.max(0,Math.floor(seconds||0));return `${n>=3600?`${Math.floor(n/3600)}:`:''}${String(Math.floor(n%3600/60)).padStart(2,'0')}:${String(n%60).padStart(2,'0')}`}
export default function TestSession({test,index,answers,onIndex,onOption,onNumeric,onClear,onSubmit,onExit,submitting,error,timed,remaining,elapsed,questionSeconds}) {
 const [palette,setPalette]=useState(false),body=useRef(null)
 const q=test.questions[index]
 const subjects=[...new Set(test.questions.map(q=>q.subject_code).filter(Boolean))]
 const answered=item=>answers[item.question_id]?.option_ids?.length||answers[item.question_id]?.numeric_answer!=null
 const count=test.questions.filter(answered).length
 const selected=answers[q.question_id]||{}
 const sameSubject=test.questions.map((q,i)=>({q,i})).filter(item=>item.q.subject_code===q.subject_code)
 useEffect(()=>{if(body.current)body.current.scrollTop=0},[q.question_id])
 function finish(){if(window.confirm(`Submit your saved answers? ${count} of ${test.questions.length} questions answered.`))onSubmit()}
 return <div className="test-session">
  <header className="test-session-header"><div><strong>{test.is_mock?'JEE Main mock':'Question practice'}</strong><small>{test.title}</small></div><div className="test-session-clock" role="timer" aria-label={timed?'Time remaining':'Practice time elapsed'}><small>{timed?'Time remaining':'Time elapsed'}</small><strong>{clock(timed?remaining:elapsed)}</strong></div><button type="button" onClick={onExit} disabled={submitting}>Exit test</button></header>
  <nav className="test-session-subjects" aria-label="Test subjects">{subjects.map(code=><button type="button" key={code} aria-pressed={q.subject_code===code} onClick={()=>onIndex(test.questions.findIndex(q=>q.subject_code===code))}>{subjectNames[code]||code}</button>)}<button type="button" className="test-palette-toggle" aria-expanded={palette} onClick={()=>setPalette(v=>!v)}>Questions · {count}/{test.questions.length}</button></nav>
  <div className="test-session-layout"><main className="test-session-main">
   <div className="test-session-qheading"><strong>Question {index+1} <small>of {test.questions.length}</small></strong><span>{q.type==='numerical'?'Section B · Numerical':q.type==='multi_correct'?'Multiple correct':'Section A · Single correct'} · +{q.marks_correct} / −{q.marks_wrong}</span><small>This question {clock(questionSeconds)}</small></div>
   <div className="test-session-content" ref={body} key={q.question_id}>
    {error&&<p className="alert" role="alert">{error}</p>}
    {q.passage&&<div className="passage"><MathText text={q.passage}/></div>}
    <div className="qtext"><MathText text={q.stem}/></div><QuestionAssets assets={q.assets}/>
    {q.type==='numerical'?<label className="test-numeric">Your answer<input className="input" type="number" step="any" disabled={submitting} value={selected.numeric_answer??''} onChange={event=>onNumeric(q.question_id,event.target.value)} placeholder="Enter a number"/></label>:<div className="options" role={q.type==='multi_correct'?'group':'radiogroup'} aria-label="Answer options">{q.options.map(o=><button type="button" key={o.id} disabled={submitting} role={q.type==='multi_correct'?'checkbox':'radio'} aria-checked={Boolean(selected.option_ids?.includes(o.id))} className={`option ${selected.option_ids?.includes(o.id)?'is-selected':''}`} onClick={()=>onOption(q.question_id,o.id)}><span className="option-key">{o.label}</span><span className="option-body"><MathText text={o.content}/></span></button>)}</div>}
    {q.recommendation&&<details className="test-question-reason"><summary>Why this question?</summary><p>{q.recommendation.reason}</p></details>}
   </div>
   <footer className="test-session-actions"><button type="button" disabled={submitting||index===0} onClick={()=>onIndex(index-1)}>Previous</button><button type="button" disabled={submitting||!answered(q)} onClick={()=>onClear(q.question_id)}>Clear answer</button>{index<test.questions.length-1&&<button type="button" className="primary" disabled={submitting} onClick={()=>onIndex(index+1)}>Next question</button>}<button type="button" className={index===test.questions.length-1?'primary':''} disabled={submitting} onClick={finish}>{submitting?'Submitting…':'Submit test'}</button></footer>
  </main><aside className={`test-session-palette ${palette?'is-open':''}`}><header><strong>Question navigator</strong><button type="button" onClick={()=>setPalette(false)} className="test-palette-close">Close</button></header><p>{count} answered · {test.questions.length-count} unanswered</p>{sameSubject.some(({q})=>q.type==='numerical')&&<div className="test-section-links">{[['single_correct','MCQs'],['numerical','Numericals']].map(([type,label])=><button type="button" key={type} onClick={()=>{const first=sameSubject.find(item=>item.q.type===type);if(first)onIndex(first.i)}}>{label}</button>)}</div>}<nav aria-label="Jump to question">{sameSubject.map(({q:item,i})=><button type="button" key={item.question_id} className={answered(item)?'answered':''} aria-current={index===i?'step':undefined} aria-label={`Question ${i+1}, ${answered(item)?'answered':'unanswered'}`} onClick={()=>{onIndex(i);setPalette(false)}}>{i+1}</button>)}</nav></aside></div>
 </div>
}
