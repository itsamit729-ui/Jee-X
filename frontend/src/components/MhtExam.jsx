import { useEffect, useState } from 'react'
import MathText from './MathText.jsx'
import QuestionAssets from './QuestionAssets.jsx'
import { cetCanAnswer, cetPhase, cetStatus } from '../lib/mhtExam.js'
import './mht-exam.css'

const names = { PHY: 'Physics', CHEM: 'Chemistry', MATH: 'Mathematics' }
const labels = { answered: 'Answered', unanswered: 'Not answered', unvisited: 'Not visited', review: 'Marked for review', 'answered-review': 'Answered & marked' }
export default function MhtExam({ test, remaining, index, onIndex, answers, onAnswer, onClear, onSubmit, onExit, submitting, error }) {
  const phase = cetPhase(remaining)
  const allowed = test.questions.map((q, i) => ({ q, i })).filter(({ q }) => cetCanAnswer(q.subject_code, remaining))
  const current = allowed.find(item => item.i === index) || allowed[0]
  const q = current?.q
  const [visited, setVisited] = useState({})
  const [review, setReview] = useState({})
  const [draft, setDraft] = useState(null)
  const [instructions, setInstructions] = useState(false)
  useEffect(() => {
    if (!q) return
    onIndex(current.i)
    setVisited(v => ({ ...v, [q.question_id]: true }))
    setDraft(answers[q.question_id]?.option_ids?.[0] ?? null)
  }, [q?.question_id])
  const seconds = phase === 'PC' ? remaining - 5400 : Math.max(0, remaining)
  const subjectQuestions = allowed.filter(item => item.q.subject_code === q?.subject_code)
  const state = id => cetStatus(id, answers, visited, review)
  function save(mark) {
    if (!q || !cetCanAnswer(q.subject_code, remaining)) return
    if (draft != null) onAnswer(q.question_id, draft)
    else onClear(q.question_id)
    setReview(v => ({ ...v, [q.question_id]: mark }))
    const next = allowed.find(item => item.i > current.i)
    if (next) onIndex(next.i)
  }
  return <div className="cet-exam">
    <header className="cet-top"><div><strong>JEE EDGE <span>• MHT CET PCM</span></strong><small>{test.title}</small></div><button onClick={() => setInstructions(v => !v)}>Instructions</button><button onClick={onExit}>Exit mock</button></header>
    <div className="cet-strip"><strong>{phase === 'PC' ? 'Section 1: Physics & Chemistry' : phase === 'MATH' ? 'Section 2: Mathematics' : 'Time is up'}</strong><span role="timer" aria-label="Section time remaining">Time left <b>{String(Math.floor(seconds / 60)).padStart(2, '0')}:{String(seconds % 60).padStart(2, '0')}</b></span></div>
    {instructions && <div className="cet-instructions"><strong>Mock instructions</strong><p>Physics and Chemistry: first 90 minutes. Mathematics: next 90 minutes. The previous section locks automatically. Save & Next records your choice; a selected choice is not saved until you save it. Saved answers marked for review are included in scoring. No negative marking.</p><p>Reconstructed English-language paper. Missing questions and original question order may differ from the official exam. This is a practice interface, not an official CET portal. Keep this tab open; refreshing or exiting loses this session.</p></div>}
    {error && <p className="cet-error" role="alert">{error}</p>}
    <div className="cet-layout"><main className="cet-main">
      <nav className="cet-tabs" aria-label="Subject">{Object.entries(names).map(([code, name]) => <button key={code} disabled={!cetCanAnswer(code, remaining)} aria-pressed={q?.subject_code === code} onClick={() => { const target = allowed.find(item => item.q.subject_code === code); if (target) onIndex(target.i) }}>{name}{!cetCanAnswer(code, remaining) ? ' · Locked' : ''}</button>)}</nav>
      {q ? <><div className="cet-qheading"><strong>Question {current.i + 1}</strong><span>Single correct · +{q.marks_correct} mark{q.marks_correct > 1 ? 's' : ''} · No negative marking</span></div><div className="cet-question">
        {q.passage && <div className="passage"><MathText text={q.passage}/></div>}
        <MathText text={q.stem}/><QuestionAssets assets={q.assets}/>
        <div className="cet-options" role="radiogroup" aria-label="Answer options">{q.options.map(o => <label key={o.id}><input type="radio" name={`cet-${q.question_id}`} checked={draft === o.id} disabled={submitting} onChange={() => setDraft(o.id)}/><span>{o.label}.</span><MathText text={o.content}/></label>)}</div>
      </div><footer className="cet-actions"><button disabled={submitting} onClick={() => save(true)}>Mark for Review & Next</button><button disabled={submitting} onClick={() => { setDraft(null); onClear(q.question_id) }}>Clear Response</button><button className="cet-primary" disabled={submitting} onClick={() => save(false)}>Save & Next</button></footer></> : <div className="cet-question"><h2>{phase === 'DONE' ? 'Submitting your mock…' : 'No questions in this section'}</h2><p>{phase === 'DONE' ? 'Please keep this page open. If submission fails, use Retry submission.' : 'The next section opens when the section timer ends.'}</p></div>}
    </main><aside className="cet-sidebar"><h3>Question palette</h3><div className="cet-legend">{Object.entries(labels).map(([key, label]) => <span key={key}><i className={`cet-key ${key}`}>{test.questions.filter(item => state(item.question_id) === key).length}</i>{label}</span>)}</div>
      <p>{names[q?.subject_code] || 'Section complete'}</p><div className="cet-palette">{subjectQuestions.map(({ q: item, i }) => <button key={item.question_id} className={`cet-key ${state(item.question_id)}`} aria-current={current?.i === i ? 'step' : undefined} aria-label={`Question ${i+1}: ${labels[state(item.question_id)]}`} onClick={() => onIndex(i)}>{i+1}</button>)}</div>
      <small>Answered and marked questions are counted. Unsaved choices are not counted.</small>
      <button className="cet-submit" disabled={submitting || phase === 'PC'} onClick={() => { if (phase === 'DONE' || window.confirm('Submit the mock with your saved answers? This cannot be undone.')) onSubmit() }}>{submitting ? 'Submitting…' : phase === 'DONE' ? 'Retry submission' : 'Submit mock'}</button>
      {phase === 'PC' && <small>Submission unlocks in the Mathematics section.</small>}
    </aside></div>
  </div>
}
