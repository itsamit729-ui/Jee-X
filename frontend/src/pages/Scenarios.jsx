import { useEffect, useRef, useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import AppHeader from '../components/AppHeader.jsx'
import MathText from '../components/MathText.jsx'
import QuestionAssets from '../components/QuestionAssets.jsx'
import { scenarioService } from '../lib/scenarios.js'
import './scenarios.css'

const SUBJECT = { PHY: 'Physics', CHEM: 'Chemistry', MATH: 'Mathematics' }
const emptyAnswer = () => ({ option_ids: [], numeric_answer: null, marked_for_review: false, time_spent_sec: 0 })
const clock = (seconds) => `${Math.floor(seconds / 60).toString().padStart(2, '0')}:${(seconds % 60).toString().padStart(2, '0')}`

function Timeline({ preset, elapsed, examMinutes = 180 }) {
  const before = preset.start_minute
  const duration = preset.duration_minutes
  const after = examMinutes - before - duration
  const progress = Math.max(0, Math.min(duration, elapsed / 60))
  return <div className="scenario-timeline" aria-label={`${before} minutes of exam context, ${duration} minute practice segment, ${after} minutes after segment`}>
    <div className="scenario-timeline-captions"><span>Exam start</span><span>3-hour paper</span><span>Exam end</span></div>
    <div className="scenario-timeline-track">
      <span className="scenario-past" style={{ width: `${before / examMinutes * 100}%` }} />
      <span className="scenario-playing" style={{ width: `${duration / examMinutes * 100}%` }}><span style={{ width: `${progress / duration * 100}%` }} /></span>
      <span className="scenario-future" style={{ width: `${after / examMinutes * 100}%` }} />
    </div>
    <div className="scenario-timeline-labels"><span>{before} min already elapsed</span><strong>{duration} min you play</strong><span>{after} min after</span></div>
  </div>
}

function DecisionReview({ result, remaining }) {
  const longest = result.questions.reduce((a, b) => b.time_spent_sec > (a?.time_spent_sec ?? 0) ? b : a, null)
  const reviewed = result.questions.filter(q => q.marked_for_review)
  const unresolved = reviewed.filter(q => q.outcome === 'skipped')
  return <div className="scenario-decision-review">
    <div><strong>Time allocation</strong><p>{longest?.time_spent_sec > 0 ?
      `Your longest stop was ${longest.ref} (${clock(longest.time_spent_sec)}). ${longest.time_spent_sec >= 240 ? 'Try a shorter skip checkpoint on your next run.' : 'You kept your longest stop under four minutes.'}` :
      'No question time was recorded in this segment.'}</p></div>
    <div><strong>Question selection</strong><p>You answered {result.attempted} of {result.questions.length} questions and left {result.skipped} unanswered. {result.skipped ? 'On a replay, scan the unanswered ones before spending longer on a single problem.' : 'You answered every question in the segment.'}</p></div>
    <div><strong>Review decisions</strong><p>{reviewed.length ? `You flagged ${reviewed.length} for review; ${unresolved.length} remained unanswered.` : 'You did not mark any question for review.'} {remaining ? `${remaining} minutes of the full exam would still remain after this segment.` : 'This segment reached the end of the three-hour paper.'}</p></div>
  </div>
}

function PresetList() {

  const navigate = useNavigate()
  const [presets, setPresets] = useState(null)
  const [starting, setStarting] = useState('')
  const [error, setError] = useState('')

  useEffect(() => {
    scenarioService.list().then(setPresets).catch(e => setError(e.message))
  }, [])

  async function start(preset) {
    if (starting) return
    setStarting(preset.key)
    setError('')
    try {
      const run = await scenarioService.start(preset.key)
      navigate(`/scenarios/${run.id}`)
    } catch (e) {
      setError(e.message)
      setStarting('')
    }
  }

  return <div className="crackjee-root"><AppHeader /><main className="scenario-wrap">
    <Link to="/dashboard" className="scenario-back">← Back to dashboard</Link>
    <header className="scenario-intro"><span className="scenario-eyebrow">EXAM SITUATIONS</span><h1>Practise the moment that matters.</h1>
      <p>A three-hour JEE Main paper sets the scene. You play only the crucial 15–45 minutes. Your score comes from the questions you actually answer.</p>
    </header>
    {error && <p className="alert" role="alert">{error}</p>}
    {!presets && !error && <p role="status">Loading scenarios…</p>}
    <div className="scenario-list">{presets?.map((p, index) => <article className="scenario-card" key={p.key}>
      <span className="scenario-number">{String(index + 1).padStart(2, '0')}</span>
      <div className="scenario-card-body"><div className="scenario-card-top"><span>AT MINUTE {p.start_minute} OF 180</span><strong>{p.duration_minutes} MIN PLAY</strong></div>
        <h2>{p.title}</h2><p>{p.pressure}</p><p className="scenario-goal">Your goal: {p.objective}</p>
        <Timeline preset={p} elapsed={0} examMinutes={p.exam_minutes} />
        <button type="button" className="btn btn-primary" onClick={() => start(p)} disabled={Boolean(starting)}>
          {starting === p.key ? 'Opening situation…' : 'Enter situation →'}
        </button>
      </div>
    </article>)}</div>
    <p className="scenario-footnote">These are practice situations. The earlier part of the paper is a fictional setup; your rating, coins, and mock-test history are unaffected.</p>
  </main></div>
}

function Session({ runId }) {

  const [run, setRun] = useState(null)
  const [answers, setAnswers] = useState({})
  const [index, setIndex] = useState(0)
  const [seconds, setSeconds] = useState(0)
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)
  const [saving, setSaving] = useState(false)
  const pendingSaves = useRef(0)
  const answersRef = useRef({})
  const saveQueue = useRef(Promise.resolve())
  const timeEntered = useRef(Date.now())
  const offset = useRef(0)
  const expireRequested = useRef(false)
  const runRef = useRef(null)

  function loadSession(payload) {
    runRef.current = payload
    answersRef.current = payload.answers || {}
    setAnswers(payload.answers || {})
    offset.current = new Date(payload.server_now).getTime() - Date.now()
    setRun(payload)
    setSeconds(payload.status === 'finished' ? 0 : Math.max(0, Math.ceil((new Date(payload.deadline_at).getTime() - Date.now() - offset.current) / 1000)))
    timeEntered.current = Date.now()
  }

  useEffect(() => {
    let alive = true
    setRun(null)
    setError('')
    scenarioService.get(runId).then(payload => { if (alive) loadSession(payload) })
      .catch(e => { if (alive) setError(e.message) })
    return () => { alive = false }
  }, [runId])

  useEffect(() => {
    if (!run || run.status !== 'active') return undefined
    const timer = setInterval(() => setSeconds(Math.max(0, Math.ceil((new Date(run.deadline_at).getTime() - Date.now() - offset.current) / 1000))), 1000)
    return () => clearInterval(timer)
  }, [run?.id, run?.status, run?.deadline_at])

  function queueSave(question, answer) {
    const next = { ...answersRef.current, [question.id]: answer }
    answersRef.current = next
    setAnswers(next)
    pendingSaves.current += 1
    setSaving(true)
    saveQueue.current = saveQueue.current.catch(() => {}).then(async () => {
      await scenarioService.save(runId, question.id, answer)
    }).catch(e => {
      setError(`Your latest answer could not be saved: ${e.message}`)
      throw e
    }).finally(() => {
      pendingSaves.current -= 1
      setSaving(pendingSaves.current > 0)
    })
    return saveQueue.current
  }

  function recordCurrent(patch = {}) {
    if (!run || run.status !== 'active' || seconds <= 0) return
    const question = run.questions[index]
    const previous = answersRef.current[question.id] || emptyAnswer()
    const now = Date.now()
    const elapsed = Math.max(0, Math.floor((now - timeEntered.current) / 1000))
    timeEntered.current = now
    const next = { ...previous, ...patch, time_spent_sec: Math.min(run.scenario.duration_minutes * 60, previous.time_spent_sec + elapsed) }
    queueSave(question, next).catch(() => {})
  }

  function move(to) {
    if (to === index || !run || run.status !== 'active') return
    recordCurrent()
    setIndex(to)
    timeEntered.current = Date.now()
  }

  async function finish() {
    if (expireRequested.current || !runRef.current || runRef.current.status !== 'active') return
    expireRequested.current = true
    setBusy(true)
    try {
      try {
        await saveQueue.current
      } catch (saveError) {
        // A final save can arrive just after the server deadline. In that case
        // the server has already ended the run and we can still show its result.
        const current = await scenarioService.get(runId)
        if (current.status === 'finished') {
          loadSession(current)
          setError('')
          return
        }
        throw saveError
      }
      const payload = await scenarioService.finish(runId)
      loadSession(payload)
      setError('')
    } catch (e) {
      setError(`Could not finish this situation. ${e.message} Retry once your connection is back.`)
      expireRequested.current = false
    } finally { setBusy(false) }
  }

  useEffect(() => {
    if (run?.status === 'active' && seconds === 0) finish()
  }, [run?.status, seconds])

  async function retrySaves() {
    setError('')
    setBusy(true)
    try {
      await saveQueue.current.catch(() => {})
      for (const [id, answer] of Object.entries(answersRef.current)) await scenarioService.save(runId, id, answer)
    } catch (e) { setError(`Could not save answers: ${e.message}`) }
    finally { setBusy(false) }
  }

  if (!run) return <div className="crackjee-root"><AppHeader /><main className="scenario-wrap"><Link to="/scenarios" className="scenario-back">← Situations</Link><p role="status">{error || 'Loading your situation…'}</p></main></div>

  const p = run.scenario
  const finished = run.status === 'finished'
  const q = run.questions[index]
  const value = answers[q.id] || emptyAnswer()
  const answered = Object.values(answers).filter(a => a.option_ids?.length || a.numeric_answer !== null && a.numeric_answer !== undefined).length
  const elapsed = finished ? run.elapsed_sec : p.duration_minutes * 60 - seconds

  return <div className="crackjee-root"><AppHeader /><main className="scenario-wrap scenario-session">
    <Link to="/scenarios" className="scenario-back">← All situations</Link>
    <header className="scenario-session-head"><div><span className="scenario-eyebrow">EXAM SITUATION · JEE MAIN PRACTICE</span><h1>{p.title}</h1>
      <p>{p.pressure}</p></div><div className={`scenario-clock ${seconds <= 60 && !finished ? 'urgent' : ''}`} role="timer" aria-label="Time left in this segment"><span>SEGMENT TIME LEFT</span><strong>{finished ? 'Done' : clock(seconds)}</strong></div></header>
    <Timeline preset={p} elapsed={elapsed} examMinutes={run.exam_minutes} />
    <div className="scenario-context"><span>Before: {p.prior_answered} questions answered in the fictional setup</span><span>Now: {answered}/{run.questions.length} answered in this segment</span><span>After: {Math.max(0, 180 - p.start_minute - p.duration_minutes)} min of the paper outside this session</span></div>
    {error && <div className="alert" role="alert">{error} {!finished && <button type="button" className="btn btn-secondary btn-sm" onClick={seconds === 0 ? finish : retrySaves} disabled={busy}>{seconds === 0 ? 'View result' : 'Retry saving'}</button>}</div>}
    {finished ? <section className="scenario-result"><span className="scenario-eyebrow">SEGMENT COMPLETE</span><h2>{run.result.score} <small>/ {run.result.possible_marks} marks</small></h2>
      <p>These marks are from this segment only. The earlier and later parts of the three-hour paper have no assigned score.</p>
      <div className="scenario-result-stats"><div><strong>{run.result.correct}</strong> Correct</div><div><strong>{run.result.wrong}</strong> Incorrect</div><div><strong>{run.result.skipped}</strong> Skipped</div></div>
      <h3>Decision review</h3><DecisionReview result={run.result} remaining={Math.max(0, 180 - p.start_minute - p.duration_minutes)} />
      <div className="scenario-result-actions"><Link className="btn btn-secondary" to="/scenarios">Try another situation</Link><button type="button" className="btn btn-primary" disabled={busy} onClick={async () => {
        setBusy(true)
        try { const next = await scenarioService.start(p.key); window.location.assign(`/scenarios/${next.id}`) }
        catch (e) { setError(e.message); setBusy(false) }
      }}>Replay this situation</button></div>
      <h3>Question review</h3>{run.questions.map((question, i) => {
        const result = run.result.questions.find(item => item.id === question.id)
        return <div className="scenario-review" key={question.id}><div className="scenario-review-head"><strong>{i + 1}. {SUBJECT[question.subject]}</strong><span className={`scenario-outcome ${result.outcome}`}>{result.outcome} · {result.marks > 0 ? '+' : ''}{result.marks}</span></div>
          <p><MathText text={question.stem} /></p><QuestionAssets assets={question.assets} /><p><strong>Answer: </strong>{question.type === 'numerical' ? result.correct_numeric_answer : result.correct_option_ids.join(', ')} · <MathText text={result.solution} /></p>
          <small>{result.time_spent_sec}s recorded on this question{result.marked_for_review ? ' · marked for review' : ''}</small></div>
      })}
    </section> : <div className="scenario-paper"><aside className="scenario-palette"><strong>Question map</strong><p>Select any question to revisit it.</p>
      <div>{run.questions.map((item, i) => { const a = answers[item.id]; const state = a?.marked_for_review ? 'review' : a?.option_ids?.length || a?.numeric_answer != null ? 'answered' : 'empty'; return <button type="button" key={item.id} aria-label={`Question ${i + 1}, ${state}`} aria-current={i === index ? 'true' : undefined} className={`scenario-palette-item ${state} ${i === index ? 'current' : ''}`} onClick={() => move(i)}>{i + 1}</button> })}</div>
      <p className="scenario-save-status" role="status">{saving ? 'Saving…' : error ? 'Check save status' : 'Answers saved as you work'}</p>
    </aside><section className="qcard scenario-question" key={q.id}>
      <div className="qmeta"><span className="tag">{SUBJECT[q.subject]}</span><span className="tag">Question {index + 1} of {run.questions.length}</span><span className="tag">{q.type === 'numerical' ? 'Numerical · +4 / −1' : 'Single choice · +4 / −1'}</span></div>
      {q.passage && <div className="passage"><MathText text={q.passage} /></div>}
      <div className="qtext"><MathText text={q.stem} /></div><QuestionAssets assets={q.assets} />
      {q.type === 'numerical' ? <div className="field"><label className="field-label" htmlFor="scenario-numeric">Enter your answer</label><input id="scenario-numeric" className="input num" type="number" step="any" value={value.numeric_answer ?? ''} onChange={e => recordCurrent({ numeric_answer: e.target.value === '' ? null : Number(e.target.value), option_ids: [] })} /></div>
        : <div className="options" role="radiogroup" aria-label="Answer choices">{q.options.map(o => <button key={o.id} type="button" className={`option ${value.option_ids?.includes(o.id) ? 'is-selected' : ''}`} role="radio" aria-checked={Boolean(value.option_ids?.includes(o.id))} onClick={() => recordCurrent({ option_ids: [o.id], numeric_answer: null })}><span className="option-key">{o.label}</span><span className="option-body"><MathText text={o.content} /></span></button>)}</div>}
      <div className="scenario-question-actions"><button type="button" className="btn btn-quiet btn-sm" onClick={() => recordCurrent({ option_ids: [], numeric_answer: null })}>Clear answer</button><button type="button" className="btn btn-secondary btn-sm" aria-pressed={Boolean(value.marked_for_review)} onClick={() => recordCurrent({ marked_for_review: !value.marked_for_review })}>{value.marked_for_review ? 'Unmark review' : 'Mark for review'}</button></div>
      <div className="scenario-next"><button type="button" className="btn btn-secondary" disabled={index === 0} onClick={() => move(index - 1)}>Previous</button>{index < run.questions.length - 1 ? <button type="button" className="btn btn-primary" onClick={() => move(index + 1)}>Next question →</button> : <button type="button" className="btn btn-primary" onClick={() => { recordCurrent(); finish() }} disabled={busy}>Finish segment</button>}</div>
    </section></div>}
    {!finished && <p className="scenario-end"><button type="button" className="btn btn-quiet" disabled={busy} onClick={() => { recordCurrent(); finish() }}>Finish early and see results</button></p>}
  </main></div>
}

export default function Scenarios() {
  const { runId } = useParams()
  return runId ? <Session key={runId} runId={runId} /> : <PresetList />
}
