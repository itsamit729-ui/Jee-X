import { useCallback, useEffect, useRef, useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { ArrowLeft, ArrowRight, Check, Clock3, Cloud, LockKeyhole } from 'lucide-react'
import { assignmentDeadline } from '../lib/assignmentClock.js'
import { createPracticeTimer } from '../lib/practiceTimer.js'
import MathText from '../components/MathText.jsx'
import QuestionContent from '../components/classroom/QuestionContent.jsx'
import { classApi, ErrorMessage, Shell, when } from '../components/classroom/shared.jsx'

const mapAnswers = values => Object.fromEntries((values || []).map(a => [a.question_id, a]))
const isAnswered = answer => Boolean(answer?.option_ids?.length || (answer?.numeric_answer !== null && answer?.numeric_answer !== undefined))

export default function Assignment() {
  const { id } = useParams()
  // A route change remounts the attempt, so queued writes cannot reach another paper.
  return <Attempt key={id} id={id}/>
}
function Attempt({ id }) {
  const navigate = useNavigate()
  const [paper, setPaper] = useState(null), [answers, setAnswers] = useState({}), [index, setIndex] = useState(0), [error, setError] = useState(''), [busy, setBusy] = useState(false), [saveState, setSaveState] = useState(''), [seconds, setSeconds] = useState(0), [confirm, setConfirm] = useState(false), [dirty, setDirty] = useState(0), [conflict, setConflict] = useState(false)
  const [paletteOpen, setPaletteOpen] = useState(false)
  const paperRef = useRef(null), answersRef = useRef({}), version = useRef(0), queue = useRef(Promise.resolve()), deadline = useRef(0), active = useRef(true), dirtyRef = useRef(false), submitting = useRef(false), autoSubmitted = useRef(false)
  const timer = useRef(createPracticeTimer()), initialTimes = useRef({})
  const accept = useCallback((next, restore = false) => {
    paperRef.current = next; version.current = next.draft_version
    if (active.current) setPaper(next)
    if (next.deadline) deadline.current = assignmentDeadline(next.deadline, next.server_now)
    if (restore || next.result) {
      answersRef.current = mapAnswers(next.answers); dirtyRef.current = false
      timer.current.reset(); initialTimes.current = Object.fromEntries((next.answers || []).map(a => [a.question_id, a.time_taken_sec]))
      if (active.current) setAnswers(answersRef.current)
    }
  }, [])
  const load = useCallback(async () => {
    setBusy(true); setError('')
    try { const next = await classApi(`/assignments/${id}`); accept(next, true); setConflict(false); setSaveState(next.saved_at ? 'Saved to your account' : '') } catch (e) { setError(e.message) } finally { if (active.current) setBusy(false) }
  }, [id, accept])
  useEffect(() => { active.current = true; load(); return () => { active.current = false } }, [load])
  async function start() {
    setBusy(true); setError('')
    try { accept(await classApi(`/assignments/${id}/start`, { method: 'POST' }), true) } catch (e) { setError(e.message) } finally { setBusy(false) }
  }
  const persist = useCallback((submit = false) => {
    if (submit && submitting.current) return queue.current
    if (submit) { submitting.current = true; setBusy(true); setConfirm(false) }
    const operation = queue.current.catch(() => {}).then(async () => {
      if (!active.current || paperRef.current?.result) return
      const source = answersRef.current
      const snapshot = (paperRef.current.questions || []).map(q => ({
        question_id: q.question_id, option_ids: [], numeric_answer: null, ...source[q.question_id],
        time_taken_sec: Math.min(paperRef.current.duration_sec, (initialTimes.current[q.question_id] || 0) + timer.current.seconds(q.question_id)),
      }))
      setSaveState(submit ? 'Submitting…' : 'Saving…')
      try {
        const next = await classApi(`/assignments/${id}/${submit ? 'submit' : 'draft'}`, { method: submit ? 'POST' : 'PUT', body: { version: version.current, answers: snapshot } })
        accept({ ...paperRef.current, ...next })
        if (source === answersRef.current || next.result) dirtyRef.current = false
        if (active.current) { setSaveState('Saved to your account'); setError('') }
        if (next.result) window.dispatchEvent(new Event('jee-inbox-changed'))
      } catch (e) {
        if (active.current) { setError(e.message); setSaveState('Not saved — retry below'); if (e.status === 409) setConflict(true) }
      }
    }).finally(() => { if (submit) { submitting.current = false; if (active.current) setBusy(false) } })
    queue.current = operation
    return operation
  }, [id, accept])
  useEffect(() => {
    let leaving = false
    const saveBeforeNavigation = event => {
      if (!paperRef.current?.attempt_id || paperRef.current?.result || (!dirtyRef.current && !submitting.current)) return
      const anchor = event.target.closest?.('a[href]')
      if (!anchor || anchor.target === '_blank' || event.ctrlKey || event.metaKey || event.shiftKey || event.altKey || event.button !== 0) return
      const url = new URL(anchor.href)
      if (url.origin !== window.location.origin) return
      event.preventDefault(); event.stopPropagation()
      if (leaving) return
      leaving = true
      persist(false).then(() => {
        if (active.current && !dirtyRef.current && !submitting.current) navigate(url.pathname + url.search + url.hash)
      }).finally(() => { leaving = false })
    }
    document.addEventListener('click', saveBeforeNavigation, true)
    return () => document.removeEventListener('click', saveBeforeNavigation, true)
  }, [navigate, persist])
  useEffect(() => {
    if (!dirty || !dirtyRef.current || paper?.result || conflict) return
    const timer = setTimeout(() => persist(false), 650)
    return () => clearTimeout(timer)
  }, [dirty, paper?.result, conflict, persist])
  useEffect(() => {
    if (!paper?.attempt_id || paper.result) return
    const tick = () => {
      const left = Math.max(0, Math.ceil((deadline.current - Date.now()) / 1000)); setSeconds(left)
      if (left === 0 && !autoSubmitted.current) { autoSubmitted.current = true; persist(true) }
    }
    tick(); const timer = setInterval(tick, 1000)
    const preventLoss = e => { if (dirtyRef.current || submitting.current) { e.preventDefault(); e.returnValue = '' } }
    const retryOnline = () => { if (dirtyRef.current && !conflict) persist(false) }
    window.addEventListener('beforeunload', preventLoss); window.addEventListener('online', retryOnline)
    return () => { clearInterval(timer); window.removeEventListener('beforeunload', preventLoss); window.removeEventListener('online', retryOnline) }
  }, [paper?.attempt_id, paper?.result, conflict, persist])
  useEffect(() => {
    if (!paper?.result || paper.solutions_released) return
    const refresh = () => { if (!document.hidden) classApi(`/assignments/${id}`).then(next => accept(next, true)).catch(() => {}) }
    const interval = setInterval(refresh, 30000)
    window.addEventListener('focus', refresh)
    return () => { clearInterval(interval); window.removeEventListener('focus', refresh) }
  }, [paper?.result, paper?.solutions_released, id, accept])
  useEffect(() => {
    if (!paper?.attempt_id || paper.result || busy) return
    const qid = paper.questions[index]?.question_id
    const update = () => timer.current.activate(qid, document.visibilityState === 'visible' && document.hasFocus())
    update()
    document.addEventListener('visibilitychange', update); window.addEventListener('focus', update); window.addEventListener('blur', update)
    return () => { timer.current.pause(); document.removeEventListener('visibilitychange', update); window.removeEventListener('focus', update); window.removeEventListener('blur', update) }
  }, [paper?.attempt_id, paper?.result, index, busy])
  function go(next) { setIndex(next) }
  function choose(value) {
    const q = paper.questions[index]
    const next = { ...answersRef.current, [q.question_id]: { question_id: q.question_id, option_ids: [], numeric_answer: null, time_taken_sec: 0, ...answersRef.current[q.question_id], ...value } }
    answersRef.current = next; dirtyRef.current = true; setAnswers(next); setDirty(n => n + 1); setSaveState('Unsaved changes')
  }
  const running = paper?.attempt_id && !paper.result
  const q = paper?.questions?.[index], answer = q && answers[q.question_id]
  const answered = Object.values(answers).filter(isAnswered).length
  const review = paper?.result?.questions?.find(r => r.question_id === q?.question_id)
  const back = <Link className="btn btn-secondary" to="/classes" onClick={e => { if (running && dirtyRef.current) { e.preventDefault(); setError('Save your latest answers before leaving. Your timer will keep running.'); persist(false) } }}>← Your classroom</Link>
  return <Shell eyebrow={paper?.result ? 'YOUR CLASS CHECKPOINT' : 'ASSIGNED BY YOUR TEACHER'} title={paper?.title || 'Your class test'} intro={running ? 'One question at a time. Your saved answers stay with you if you return.' : paper?.instructions || 'A focused checkpoint for your next step.'} action={back}><ErrorMessage error={error}/>{error && <div className="cl-row cl-retry">{running && !conflict ? <button className="btn btn-primary" onClick={() => seconds === 0 ? persist(true) : persist(false)} disabled={busy}>Retry {seconds === 0 ? 'submission' : 'save'}</button> : <button className="btn btn-secondary" onClick={load} disabled={busy}>Reload saved attempt</button>}</div>}{!paper && !error && <p role="status">Loading your assignment…</p>}{paper && !paper.attempt_id && <section className="cl-card cl-launch"><span className="cl-icon"><Clock3 size={25}/></span><h2>{paper.status === 'upcoming' ? 'Your next checkpoint is lined up.' : paper.status === 'expired' ? 'This test has closed.' : 'Ready when you are.'}</h2><div className="cl-metrics"><div><strong>{paper.question_count}</strong><small>questions</small></div><div><strong>{paper.duration_sec / 60}</strong><small>minutes</small></div><div><strong>+{paper.marks_correct} / −{paper.marks_wrong}</strong><small>marking</small></div></div><p>Opens {when(paper.opens_at)} · Due {when(paper.due_at)}</p><p>The timer starts when you begin and keeps running if you leave. The deadline can shorten your available time. Only answers saved before time runs out are graded.</p><small>Scores appear after submission. Solutions unlock {when(paper.solutions_at)}.</small>{paper.status === 'not_started' && <button className="btn btn-primary" disabled={busy} onClick={start}>{busy ? 'Starting…' : 'Begin test'} <ArrowRight size={17}/></button>}{paper.status === 'upcoming' && <button className="btn btn-secondary" disabled={busy} onClick={load}>Check opening time</button>}</section>}{paper?.result && <section className="cl-card cl-result"><div><span className="cl-eyebrow">CHECKPOINT COMPLETE</span><h2>A result to build on.</h2><p>Your submitted answers now inform your personal practice and roadmap.</p></div><div className="cl-metrics"><div><strong>{paper.result.score}<em>/{paper.result.max_score}</em></strong><small>marks</small></div><div><strong>{paper.result.correct}/{paper.question_count}</strong><small>correct</small></div><div><strong>{paper.result.accuracy}%</strong><small>attempted accuracy</small></div></div><div className="cl-row"><Link className="btn btn-primary" to="/recommendations">Practise my next step <ArrowRight size={16}/></Link><Link className="btn btn-secondary" to="/roadmap">See my roadmap</Link></div>{!paper.solutions_released && <p className="cl-release"><LockKeyhole size={17}/>Answers and explanations unlock {when(paper.solutions_at)}.</p>}</section>}{q && <div className="cl-test-layout"><section className="cl-card cl-test-question"><div className="cl-section-head"><span className="cl-eyebrow">QUESTION {index + 1} / {paper.question_count}</span><span className="cl-pill">{q.type === 'numerical' ? 'Numerical' : q.type === 'multi_correct' ? 'Choose all correct' : 'Choose one'}</span></div><QuestionContent question={q}/>{q.type === 'numerical' ? <label className="cl-numeric">Your answer<input type="number" step="any" value={answer?.numeric_answer ?? ''} disabled={!running || busy || conflict || seconds === 0} onChange={e => choose({ numeric_answer: e.target.value === '' ? null : Number(e.target.value) })} placeholder="Enter a number"/></label> : <div className="cl-answer-options">{q.options.map(o => { const chosen = answer?.option_ids?.includes(o.id); return <button key={o.id} className={chosen ? 'chosen' : ''} aria-pressed={Boolean(chosen)} disabled={!running || busy || conflict || seconds === 0} onClick={() => choose({ option_ids: q.type === 'multi_correct' ? chosen ? answer.option_ids.filter(v => v !== o.id) : [...(answer?.option_ids || []), o.id] : [o.id] })}><span>{o.label}</span><MathText text={o.content}/>{chosen && <Check size={18}/>}</button> })}</div>}{running && <button className="btn btn-quiet btn-sm" disabled={busy || conflict || seconds === 0 || !isAnswered(answer)} onClick={() => choose({ option_ids: [], numeric_answer: null })}>Clear answer</button>}{review && <div className="cl-solution"><strong>{review.outcome === 'correct' ? 'Correct' : review.outcome === 'skipped' ? 'Unanswered' : 'Needs another look'} · {review.marks_awarded} marks</strong><p>Correct answer: {q.type === 'numerical' ? `${review.answer_min} to ${review.answer_max}` : q.options.filter(o => review.correct_option_ids.includes(o.id)).map(o => o.label).join(', ')}</p><MathText text={review.solution || 'No written explanation is available for this question.'}/></div>}<div className="cl-test-actions"><button className="btn btn-secondary" disabled={index === 0} onClick={() => go(index - 1)}><ArrowLeft size={16}/>Previous</button><button className="btn btn-primary" disabled={index === paper.question_count - 1} onClick={() => go(index + 1)}>Next <ArrowRight size={16}/></button></div></section><aside className="cl-card cl-test-nav">{running && <><div className={`cl-timer ${seconds < 60 ? 'urgent' : ''}`}><Clock3 size={19}/><strong>{Math.floor(seconds / 60)}:{String(seconds % 60).padStart(2, '0')}</strong><span>remaining</span></div><div className="cl-save" role="status"><Cloud size={15}/>{saveState || 'Answers save automatically'}</div></>}<h3>{answered} / {paper.question_count} answered</h3><progress max={paper.question_count} value={answered}/><button className="cl-palette-toggle btn btn-quiet btn-sm" aria-expanded={paletteOpen} onClick={() => setPaletteOpen(v => !v)}>{paletteOpen ? 'Hide' : 'Show'} question navigator</button><nav className={`cl-palette ${paletteOpen ? '' : 'mobile-collapsed'}`} aria-label="Test questions">{paper.questions.map((question, i) => <button key={question.question_id} aria-label={`Question ${i + 1}, ${isAnswered(answers[question.question_id]) ? 'answered' : 'unanswered'}`} aria-current={index === i ? 'step' : undefined} className={isAnswered(answers[question.question_id]) ? 'answered' : ''} onClick={() => go(i)}>{i + 1}</button>)}</nav>{running && <><p>You can revisit any question before submitting.</p>{confirm ? <div className="cl-confirm" role="group" aria-label="Confirm submission"><strong>Submit {answered} answered questions?</strong><small>{paper.question_count - answered} unanswered. You cannot change answers after submission.</small><button className="btn btn-primary" disabled={busy || conflict} onClick={() => persist(true)}>Confirm submission</button><button className="btn btn-quiet" onClick={() => setConfirm(false)}>Keep working</button></div> : <button className="btn btn-primary" disabled={busy || conflict} onClick={() => setConfirm(true)}>{busy ? 'Submitting…' : 'Review & submit'}</button>}</>}</aside></div>}</Shell>
}
