import { useEffect, useState } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { ArrowLeft } from 'lucide-react'
import { catalogService, subjectTestBuilderService, subjectTestGraderService } from '../lib/subjectTests.js'
import MathText from '../components/MathText.jsx'
import QuestionAssets from '../components/QuestionAssets.jsx'
import AppHeader from '../components/AppHeader.jsx'
import Palette from '../components/Palette.jsx'
import RankPredictor from '../components/RankPredictor.jsx'
import FullscreenGuard from '../components/FullscreenGuard.jsx'
import { requestFullscreen, useFullscreenLock } from '../lib/fullscreen.js'
import { GOOD, BAD, PEN, SUBJECT_COLOR } from '../crackjee/ui.js'

const OUTCOME = { correct: 'correct', wrong: 'wrong' }

export default function SubjectTest() {
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()
  const requestedSubject = searchParams.get('subject')


  const [subjects, setSubjects] = useState(null) // null = loading
  const [chapters, setChapters] = useState([])
  const [chaptersLoading, setChaptersLoading] = useState(false)
  const [subjectCode, setSubjectCode] = useState('')
  const [chapterId, setChapterId] = useState('')
  const [count, setCount] = useState(10)
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

  const selectedSubject = subjects?.find((s) => s.code === subjectCode)
  const availableCount = chapterId
    ? chapters.find((c) => String(c.id) === String(chapterId))?.published_question_count ?? 0
    : selectedSubject?.published_question_count ?? 0

  const startTest = async () => {
    requestFullscreen() // must be called synchronously from this click, before any await
    setError('')
    setStarting(true)
    try {
      const created = await subjectTestBuilderService.start({
        subjectCode,
        chapterId: chapterId ? Number(chapterId) : null,
        count: Number(count),
      })
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
    setSubmitting(true)
    try {
      const payload = test.questions.map((q) => ({
        question_id: q.question_id,
        option_ids: answers[q.question_id]?.option_ids || [],
        numeric_answer: answers[q.question_id]?.numeric_answer ?? null,
        time_taken_sec: 0,
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
    const states = test.questions.map((qq, i) => (i === index ? 'current' : isAnswered(qq) ? 'answered' : 'idle'))
    return (
      <div className="crackjee-root">
        <AppHeader />
        <FullscreenGuard exited={fsExited} onResume={fsResume} />
        <main className="test-shell">
          <button type="button" className="btn btn-quiet btn-sm back" onClick={exitTest}>
            <ArrowLeft size={16} aria-hidden="true" />Exit test
          </button>

          <div className="test-top">
            <Palette states={states} label="Progress" />
            <span className="faint num">{answeredCount} of {test.questions.length} answered</span>
          </div>

          {error && <p className="alert" role="alert">{error}</p>}

          <div key={q.question_id} className="qcard q-enter">
            <div className="qmeta">
              <span className="tag"><span className="dot" style={{ background: SUBJECT_COLOR[test.subject_code] || PEN }} />Question {index + 1} of {test.questions.length}</span>
              <span className="tag">{q.ref}</span>
            </div>
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

  // ---------------------------------------------------------------- SETUP
  return (
    <div className="crackjee-root">
      <AppHeader />
      <main className="wrap-narrow page">
        <div className="page-head">
          <div>
            <h1 className="page-title">Subject test</h1>
            <p className="page-sub">Pick a subject, and a chapter if you like, then practise from the question bank.</p>
          </div>
        </div>

        {error && <div className="alert" role="alert">{error} <button className="btn btn-secondary btn-sm" onClick={() => setLoadVersion(v => v + 1)}>Retry loading</button></div>}

        <div className="panel">
          <div className="field">
            <span className="field-label" id="subject-label">Subject</span>
            {subjects === null ? (
              <p className="muted" style={{ display: 'flex', alignItems: 'center', gap: 8 }}><span className="spin" aria-hidden="true" />Loading subjects</p>
            ) : subjects.length === 0 ? (
              <p className="muted">No subjects found.</p>
            ) : (
              <div className="choice-grid" role="group" aria-labelledby="subject-label">
                {subjects.map((s) => {
                  const n = s.published_question_count
                  return (
                    <button key={s.code} type="button" className="choice" aria-pressed={subjectCode === s.code} onClick={() => setSubjectCode(s.code)}>
                      <span className="choice-name"><span className="dot" style={{ background: SUBJECT_COLOR[s.code] || PEN }} />{s.name}</span>
                      <span className={`choice-meta ${n === 0 ? 'is-empty' : ''}`}>{n === 0 ? 'No questions yet' : `${n} question${n === 1 ? '' : 's'}`}</span>
                    </button>
                  )
                })}
              </div>
            )}
          </div>

          <div className="field">
            <label className="field-label" htmlFor="chapter">Chapter</label>
            <select id="chapter" className="input" value={chapterId} onChange={(e) => setChapterId(e.target.value)} disabled={!subjectCode || chaptersLoading}>
              <option value="">All chapters</option>
              {chapters.map((c) => (
                <option key={c.id} value={c.id}>{c.name} ({c.published_question_count})</option>
              ))}
            </select>
            {chaptersLoading && <p className="hint" style={{ display: 'flex', alignItems: 'center', gap: 6 }}><span className="spin" aria-hidden="true" />Loading chapters</p>}
          </div>

          <div className="field">
            <label className="field-label" htmlFor="count">Number of questions</label>
            <input id="count" type="number" min="1" max="30" className="input num" style={{ maxWidth: 140 }} value={count} onChange={(e) => setCount(e.target.value)} />
          </div>

          {subjectCode && availableCount === 0 && (
            <p className="alert">No published questions for this choice yet. Try another subject or chapter.</p>
          )}

          <button type="button" className="btn btn-primary btn-lg" disabled={!subjectCode || chaptersLoading || availableCount === 0 || starting} onClick={startTest}>
            {starting ? <><span className="spin" aria-hidden="true" />Starting</> : 'Start test'}
          </button>
        </div>
      </main>
    </div>
  )
}

