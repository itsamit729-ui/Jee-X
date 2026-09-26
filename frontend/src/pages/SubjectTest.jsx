import { useEffect, useRef, useState } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { ArrowLeft, ArrowUpRight, Target, Compass, RotateCcw, Clock3 } from 'lucide-react'
import { catalogService, subjectTestBuilderService, subjectTestGraderService } from '../lib/subjectTests.js'
import MathText from '../components/MathText.jsx'
import QuestionAssets from '../components/QuestionAssets.jsx'
import AppHeader from '../components/AppHeader.jsx'
import Palette from '../components/Palette.jsx'
import RankPredictor from '../components/RankPredictor.jsx'
import FullscreenGuard from '../components/FullscreenGuard.jsx'
import { requestFullscreen, useFullscreenLock } from '../lib/fullscreen.js'
import { GOOD, BAD, PEN, SUBJECT_COLOR } from '../crackjee/ui.js'

import { createPracticeTimer } from '../lib/practiceTimer.js'
import './practice.css'

const OUTCOME = { correct: 'correct', wrong: 'wrong' }

export default function SubjectTest({ initialMode = 'recommended' }) {
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()
  const requestedSubject = searchParams.get('subject')


  const [subjects, setSubjects] = useState(null) // null = loading
  const [chapters, setChapters] = useState([])
  const [chaptersLoading, setChaptersLoading] = useState(false)
  const [subjectCode, setSubjectCode] = useState('')
  const [chapterId, setChapterId] = useState('')
  const [durationMinutes, setDurationMinutes] = useState(15)
  const [mode, setMode] = useState(requestedSubject ? 'topic' : initialMode)
  const timer = useRef(createPracticeTimer())
  const [error, setError] = useState('')
  const [starting, setStarting] = useState(false)
  const [loadVersion, setLoadVersion] = useState(0)

  const [test, setTest] = useState(null) // { attempt_id, questions, ... }
  const [index, setIndex] = useState(0)
  const [answers, setAnswers] = useState({}) // question_id -> { option_ids, numeric_answer }
  const [submitting, setSubmitting] = useState(false)
  const [result, setResult] = useState(null)
  const { exited: fsExited, resume: fsResume } = useFullscreenLock(Boolean(test) && !result)

  useEffect(() => {
    let active = true
    setError('')
    catalogService.listSubjects()
      .then(data => { if (active) setSubjects(data) })
      .catch(e => { if (active) { setError(e.message); setSubjects([]) } })
    return () => { active = false }
  }, [loadVersion])

  useEffect(() => {
    if (!subjects || !requestedSubject) return
    const match = subjects.find(s => s.name?.toLowerCase() === requestedSubject.toLowerCase())
    if (match) setSubjectCode(match.code)
  }, [subjects, requestedSubject])

  useEffect(() => {
    let active = true
    setChapters([])
    setChapterId('')
    setError('')
    setChaptersLoading(Boolean(subjectCode))
    if (!subjectCode) return
    catalogService.listChapters(subjectCode)
      .then(data => { if (active) setChapters(data) })
      .catch(e => { if (active) setError(e.message) })
      .finally(() => { if (active) setChaptersLoading(false) })
    return () => { active = false }
  }, [subjectCode, loadVersion])

  useEffect(() => {
    if (!test || result || submitting) return
    const id = test.questions[index]?.question_id
    const update = () => timer.current.activate(id, document.visibilityState === 'visible' && document.hasFocus())
    update()
    document.addEventListener('visibilitychange', update)
    window.addEventListener('focus', update)
    window.addEventListener('blur', update)
    return () => {
      timer.current.pause()
      document.removeEventListener('visibilitychange', update)
      window.removeEventListener('focus', update)
      window.removeEventListener('blur', update)
    }
  }, [test, index, result, submitting])

  const startTest = async () => {
    requestFullscreen() // must be called synchronously from this click, before any await
    setError('')
    setStarting(true)
    try {
      const created = await subjectTestBuilderService.start({
        subjectCode,
        chapterId: chapterId ? Number(chapterId) : null,
        durationMinutes,
        mode,
      })
      timer.current.reset()
      setTest(created)
      setIndex(0)
      setAnswers({})
      setResult(null)
    } catch (e) {
      setError(e.message)
    } finally {
      setStarting(false)
    }
  }

  const exitTest = () => {
    if (!window.confirm('Leave this test? Your answers will be lost.')) return
    setTest(null)
    setAnswers({})
    setIndex(0)
  }

  const selectOption = (questionId, optionId) => {
    setAnswers((a) => ({ ...a, [questionId]: { option_ids: [optionId] } }))
  }

  const setNumeric = (questionId, value) => {
    setAnswers((a) => ({ ...a, [questionId]: { numeric_answer: value === '' ? null : Number(value) } }))
  }

  const submitTest = async () => {
    setError('')
    timer.current.pause()
    setSubmitting(true)
    try {
      const payload = test.questions.map((q) => ({
        question_id: q.question_id,
        option_ids: answers[q.question_id]?.option_ids || [],
        numeric_answer: answers[q.question_id]?.numeric_answer ?? null,
        time_taken_sec: timer.current.seconds(q.question_id),
      }))
      const res = await subjectTestGraderService.submit(test.attempt_id, payload)
      setResult(res)
    } catch (e) {
      setError(e.message)
    } finally {
      setSubmitting(false)
    }
  }

  const restart = () => { setTest(null); setResult(null); setAnswers({}); setIndex(0) }
  const isAnswered = (q) => {
    const a = answers[q.question_id]
    return Boolean(a && (a.option_ids?.length || (a.numeric_answer !== null && a.numeric_answer !== undefined)))
  }
  const answeredCount = test ? test.questions.filter(isAnswered).length : 0

  // ---------------------------------------------------------------- RESULTS
  if (result) {
    return (
      <div className="crackjee-root">
        <AppHeader />
        <main className="test-shell">
          <div className="result-head">
            <div className="score-big">{result.score}<small>marks</small></div>
            <Palette size="lg" states={result.questions.map((r) => OUTCOME[r.outcome] || 'skipped')} label="Your answers" />
            <p className="result-line"><strong>{result.accuracy}%</strong> accuracy across {result.total_questions} questions</p>
          </div>

          <div style={{ marginBottom: 20 }}>
            <RankPredictor attemptId={result.attempt_id} />
          </div>

          <div className="panel">
            <h2 className="panel-title">Solutions</h2>
            {result.questions.map((r, i) => (
              <div key={r.question_id} className="solution">
                <div className="solution-head">
                  <span className="sq" data-s={OUTCOME[r.outcome] || 'skipped'} />
                  Question {i + 1}
                  <span className="faint" style={{ fontWeight: 500 }}>{r.ref}</span>
                  <span className="marks" style={{ color: r.marks_awarded > 0 ? GOOD : r.marks_awarded < 0 ? BAD : undefined }}>
                    {r.marks_awarded > 0 ? '+' : ''}{r.marks_awarded}
                  </span>
                </div>
                {test.questions.find(q => q.question_id === r.question_id)?.recommendation && <p className="muted" style={{fontSize:13}}>{test.questions.find(q => q.question_id === r.question_id).recommendation.reason}</p>}
                <p><MathText text={r.solution} /></p>
              </div>
            ))}
          </div>

          <div className="hero-actions">
            <button type="button" className="btn btn-primary" onClick={restart}>Start another test</button>
            <button type="button" className="btn btn-secondary" onClick={() => navigate('/dashboard')}>Back to dashboard</button>
          </div>
        </main>
      </div>
    )
  }

  // ---------------------------------------------------------------- QUESTION PHASE
  if (test) {
    const q = test.questions[index]
    const isLast = index === test.questions.length - 1
    return (
      <div className="crackjee-root">
        <AppHeader />
        <FullscreenGuard exited={fsExited} onResume={fsResume} />
        <main className="test-shell">
          <button type="button" className="btn btn-quiet btn-sm back" onClick={exitTest}>
            <ArrowLeft size={16} aria-hidden="true" />Exit test
          </button>

          <div className="practice-session-bar"><div><span className="practice-eyebrow">{test.title}</span><strong>Question {index + 1} <span>of {test.questions.length}</span></strong></div><span className="faint num">{answeredCount} answered</span><progress max={test.questions.length} value={answeredCount} aria-label="Questions answered"/></div>
          <nav className="practice-question-nav" aria-label="Jump to question">{test.questions.map((item,i) => <button key={item.question_id} type="button" aria-label={`Question ${i+1}${isAnswered(item) ? ', answered' : ', unanswered'}`} aria-current={index===i ? 'step' : undefined} className={isAnswered(item) ? 'answered' : ''} onClick={() => setIndex(i)}>{String(i+1).padStart(2,'0')}</button>)}</nav>

          {error && <p className="alert" role="alert">{error}</p>}

          <div key={q.question_id} className="qcard q-enter">
            <div className="qmeta">
              <span className="tag"><span className="dot" style={{ background: SUBJECT_COLOR[test.subject_code] || PEN }} />Question {index + 1} of {test.questions.length}</span>
              <span className="tag">{q.ref}</span>
            </div>
            {q.recommendation && <aside className="practice-why" aria-label="Why this question">
              <span className="practice-eyebrow"><Target size={14} aria-hidden="true"/> WHY THIS QUESTION</span>
              <p>{q.recommendation.reason}</p>
              <details><summary>Your learning goal</summary><p>{q.recommendation.learning_goal}</p></details>
            </aside>}
            {q.passage && <div className="passage"><MathText text={q.passage} /></div>}
            <div className="qtext"><MathText text={q.stem} /></div>
            <QuestionAssets assets={q.assets} />

            {q.type === 'numerical' ? (
              <div className="field" style={{ maxWidth: 280, marginBottom: 0 }}>
                <label className="field-label" htmlFor="numeric">Your answer</label>
                <input id="numeric" type="number" className="input num" placeholder="Type a number"
                  value={answers[q.question_id]?.numeric_answer ?? ''}
                  onChange={(e) => setNumeric(q.question_id, e.target.value)} />
              </div>
            ) : (
              <div className="options" role="radiogroup" aria-label="Options">
                {q.options.map((o) => {
                  const selected = answers[q.question_id]?.option_ids?.[0] === o.id
                  return (
                    <button key={o.id} type="button" role="radio" aria-checked={selected}
                      className={`option ${selected ? 'is-selected' : ''}`} onClick={() => selectOption(q.question_id, o.id)}>
                      <span className="option-key">{o.label}</span>
                      <span className="option-body"><MathText text={o.content} /></span>
                    </button>
                  )
                })}
              </div>
            )}
          </div>

          <div className="hero-actions" style={{ justifyContent: 'space-between', marginTop: 20 }}>
            <button type="button" className="btn btn-secondary" disabled={index === 0} onClick={() => setIndex((i) => i - 1)}>Previous</button>
            {isLast ? (
              <button type="button" className="btn btn-primary" disabled={submitting} onClick={submitTest}>
                {submitting ? <><span className="spin" aria-hidden="true" />Submitting</> : 'Submit test'}
              </button>
            ) : (
              <button type="button" className="btn btn-primary" onClick={() => setIndex((i) => i + 1)}>Next question</button>
            )}
          </div>
        </main>
      </div>
    )
  }

  const focusLabel = chapters.find(c => String(c.id) === chapterId)?.name || subjects?.find(s => s.code === subjectCode)?.name || 'Across subjects'
  const modeLabel = { recommended: 'Recommended for you', topic: 'Topic practice', revision: 'Quick revision' }[mode]
  // ---------------------------------------------------------------- SETUP
  return <div className="crackjee-root"><AppHeader />
    <main className="wrap practice-page">
      <header className="practice-intro"><div><span className="practice-eyebrow">YOUR NEXT STEP</span>
        <h1>Less guessing.<br /><em>Better practice.</em></h1>
        <p>Pick your focus. Make time for it. Leave knowing what to work on next.</p>
        <div className="practice-intro-tags"><span><Target size={14}/> A reason for every question</span><span><Clock3 size={14}/> Built around your time</span></div></div>
        <div className="practice-note"><span className="practice-eyebrow">HOW IT WORKS</span><ol><li><b>01</b><span>Find your starting point<small>Your recent answers guide the choice.</small></span></li><li><b>02</b><span>Work through the why<small>See the purpose of every question.</small></span></li><li><b>03</b><span>Take the next step<small>Review, learn, and come back stronger.</small></span></li></ol></div>
      </header>
      <section className="practice-paths" aria-label="Practice approach">
        {[['recommended', Target, '01', 'Recommended for you', 'A session shaped by your recent answers. New here? Start by finding your strengths.'],
          ['topic', Compass, '02', 'Choose a topic', 'Have something in mind? Focus on a subject or chapter, with questions chosen for your level.'],
          ['revision', RotateCcw, '03', 'Quick revision', 'Revisit concepts you have practised before. Build a starting point where evidence is limited.']].map(([key, Icon, number, title, copy]) =>
          <button key={key} type="button" className={`practice-path ${mode === key ? 'selected' : ''}`} aria-pressed={mode === key} onClick={() => setMode(key)}>
            <span className="practice-path-top"><span>{number}</span><Icon size={21}/></span><h2>{title}</h2><p>{copy}</p><span className="practice-path-action">{mode === key ? 'Selected' : 'Choose this path'} <ArrowUpRight size={17}/></span>
          </button>)}
      </section>
      <section className="practice-builder" aria-label="Set up practice">
        <div className="practice-controls"><div className="practice-step-heading"><span>01</span><div><span className="practice-eyebrow">CHOOSE YOUR FOCUS</span><h2>What are we working on?</h2></div></div>
          <div className="practice-subjects" role="group" aria-label="Subject">
            {mode !== 'topic' && <button type="button" aria-pressed={!subjectCode} onClick={() => setSubjectCode('')}>All subjects</button>}
            {subjects === null ? <span role="status">Loading subjects…</span> : subjects.map(s => <button key={s.code} type="button" aria-pressed={subjectCode === s.code} onClick={() => setSubjectCode(s.code)}>{s.name}</button>)}
          </div>
          {subjectCode && <div className="field"><label className="field-label" htmlFor="chapter">Chapter</label>
            <select id="chapter" className="input" value={chapterId} disabled={chaptersLoading} onChange={e => setChapterId(e.target.value)}><option value="">Across this subject</option>{chapters.map(c => <option key={c.id} value={c.id}>{c.name}</option>)}</select>
            {chaptersLoading && <p className="hint" role="status">Loading chapters…</p>}
          </div>}
          <h3 className="practice-time-label"><span className="practice-step-number">02</span> Set your pace</h3>
          <div className="practice-durations" role="group" aria-label="Session length">{[[5,'Quick'],[15,'Focused'],[30,'Deep practice']].map(([minutes,label]) => <button key={minutes} type="button" aria-pressed={durationMinutes === minutes} onClick={() => setDurationMinutes(minutes)}><strong>{minutes} min</strong><span>{label}</span></button>)}</div>
        </div>
        <aside className="practice-start"><span className="practice-eyebrow">READY WHEN YOU ARE</span><div className="practice-session-time"><strong>{durationMinutes}</strong><span>minutes<br />well spent</span><Clock3 size={28}/></div>
          <dl className="practice-plan" aria-live="polite"><div><dt>Approach</dt><dd>{modeLabel}</dd></div><div><dt>Focus</dt><dd>{focusLabel}</dd></div><div><dt>Finish with</dt><dd>Answers & explanations</dd></div></dl>
          <button type="button" className="btn btn-primary btn-lg" disabled={starting || chaptersLoading || (mode === 'topic' && !subjectCode)} onClick={startTest}>{starting ? 'Choosing your questions…' : 'Let’s practise'}{!starting && <ArrowUpRight size={18}/>}</button>
          <small>{mode === 'topic' && !subjectCode ? 'Choose a subject to continue.' : 'No countdown. Take the time you need to understand.'}</small>
          {starting && <p role="status" className="practice-preparing">Matching available questions to your recent answers…</p>}
        </aside>
      </section>
      {error && <div className="alert" role="alert">{error} <button type="button" className="btn btn-secondary btn-sm" onClick={() => setLoadVersion(v => v + 1)}>Retry loading</button></div>}
    </main>
  </div>
}
