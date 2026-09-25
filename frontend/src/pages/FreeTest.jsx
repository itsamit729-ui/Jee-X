import { useEffect, useMemo, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '../auth/AuthContext.jsx'
import { Clock, Check, X as XIcon } from 'lucide-react'
import { freeTestQuestions, SECONDS_PER_QUESTION } from '../data/freeTestQuestions.js'
import { api } from '../lib/api.js'
import { savePendingFreeTest } from '../lib/pendingFreeTest.js'
import { Logo } from '../components/Brand.jsx'
import Palette from '../components/Palette.jsx'
import RankPredictor from '../components/RankPredictor.jsx'
import FullscreenGuard from '../components/FullscreenGuard.jsx'
import { requestFullscreen, useFullscreenLock } from '../lib/fullscreen.js'
import { GOOD, BAD, SUBJECT_COLOR } from '../crackjee/ui.js'

const LETTER = (i) => String.fromCharCode(65 + i)

export default function FreeTest() {
  const { openLogin, isAuthenticated } = useAuth()
  const navigate = useNavigate()
  const [phase, setPhase] = useState('story') // story | question | results
  const [index, setIndex] = useState(0)
  const [timeLeft, setTimeLeft] = useState(SECONDS_PER_QUESTION)
  const [selected, setSelected] = useState(null)
  const [revealed, setRevealed] = useState(false)
  const [answers, setAnswers] = useState([])
  const [saveState, setSaveState] = useState('idle')
  const [attemptId, setAttemptId] = useState(null)
  const { exited: fsExited, resume: fsResume } = useFullscreenLock(phase === 'question')
  const intervalRef = useRef(null)
  const submittedRef = useRef(false)
  const questionHeadingRef = useRef(null)

  useEffect(() => {
    if (phase === 'question') questionHeadingRef.current?.focus()
  }, [phase, index])

  const question = freeTestQuestions[index]
  const total = freeTestQuestions.length

  useEffect(() => {
    if (phase !== 'question' || revealed) return
    intervalRef.current = setInterval(() => {
      setTimeLeft((t) => {
        if (t <= 1) { clearInterval(intervalRef.current); return 0 }
        return t - 1
      })
    }, 1000)
    return () => clearInterval(intervalRef.current)
  }, [phase, index, revealed])

  useEffect(() => {
    if (phase === 'question' && timeLeft === 0 && !revealed) submitAnswer(null)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [timeLeft])

  const submitAnswer = (optionIndex) => {
    if (revealed) return
    clearInterval(intervalRef.current)
    const correct = optionIndex === question.correctAnswer
    setAnswers((prev) => [
      ...prev,
      { questionId: question.id, selected: optionIndex, correct, timeTaken: SECONDS_PER_QUESTION - timeLeft },
    ])
    setRevealed(true)
  }

  const goToNext = () => {
    if (index === total - 1) { setPhase('results'); return }
    setIndex((i) => i + 1)
    setSelected(null)
    setRevealed(false)
    setTimeLeft(SECONDS_PER_QUESTION)
  }

  const beginTest = () => {
    requestFullscreen() // must be called synchronously from this click
    setPhase('question')
  }

  const results = useMemo(() => {
    if (phase !== 'results') return null
    const score = answers.filter((a) => a.correct).length
    const accuracy = Math.round((score / total) * 100)
    const avgTime = Math.round(answers.reduce((s, a) => s + a.timeTaken, 0) / total)
    const bySubject = {}
    freeTestQuestions.forEach((q, i) => {
      bySubject[q.subject] = bySubject[q.subject] || { correct: 0, total: 0 }
      bySubject[q.subject].total += 1
      if (answers[i]?.correct) bySubject[q.subject].correct += 1
    })
    return { score, accuracy, avgTime, bySubject }
  }, [phase, answers, total])

  useEffect(() => {
    if (phase !== 'results' || !results || submittedRef.current) return
    submittedRef.current = true

    const payload = {
      test_type: 'free_diagnostic',
      score: results.score,
      total_questions: total,
      accuracy: results.accuracy,
      avg_time_seconds: results.avgTime,
      subject_breakdown: results.bySubject,
    }

    if (isAuthenticated) {
      setSaveState('saving')
      ;(async () => {
        try {
          const saved = await api.submitTestAttempt(payload)
          setAttemptId(saved.id)
          setSaveState('saved')
        } catch {
          savePendingFreeTest(payload)
          setSaveState('error')
        }
      })()
    } else {
      savePendingFreeTest(payload)
      setSaveState('pending-signup')
    }
  }, [phase, results, isAuthenticated, total])

  const goToSignup = () => openLogin({ signup: true })

  // What was actually recorded for this question (a timeout records no choice).
  const recorded = answers[index]
  const chosen = revealed ? recorded?.selected : selected
  const states = freeTestQuestions.map((_, i) =>
    i < answers.length ? (answers[i].correct ? 'correct' : 'wrong') : phase === 'question' && i === index ? 'current' : 'idle',
  )

  return (
    <div className="crackjee-root">
      <FullscreenGuard exited={fsExited} onResume={fsResume} />
      <header className="topbar">
        <div className="wrap topbar-row">
          <Logo />
          {phase === 'question' && <span className="faint num">Question {index + 1} of {total}</span>}
        </div>
      </header>
      {phase === 'question' && <div className="test-progress-track" role="progressbar" aria-label="Questions completed" aria-valuemin={0} aria-valuemax={total} aria-valuenow={answers.length}><span style={{ width: `${answers.length / total * 100}%` }}/></div>}

      {phase === 'story' && (
        <main className="story"><div className="story-layout"><div><span className="eyebrow">EVERY JOURNEY HAS A FIRST QUESTION</span>
          <div className="story-year" aria-label="1989">1989</div>
          <p>A student from Chennai was preparing for one of India's toughest engineering entrance exams.</p>
          <p>His name was <strong>Sundar Pichai</strong>. He went on to study at IIT Kharagpur and, decades later, to run Google and Alphabet.</p>
          <p>Before any of that, he was a student in front of a question paper.</p>

          </div><div className="turn">
            <span className="eyebrow">THE FIVE-MINUTE WARM-UP</span><h2 style={{ marginTop: 12 }}>Now, your turn.</h2>
            <p>Ten questions in the spirit of the IIT entrance papers of that era. Not the actual paper he sat.</p>
            <div className="chips">
              <span className="tag">10 questions</span>
              <span className="tag">30 seconds each</span>
              {['Physics', 'Chemistry', 'Mathematics'].map((s) => (
                <span key={s} className="tag"><span className="dot" style={{ background: SUBJECT_COLOR[s] }} />{s}</span>
              ))}
            </div>
            <ol className="story-steps"><li><b>01</b> Choose an answer before the timer ends.</li><li><b>02</b> Read the explanation after each question.</li><li><b>03</b> See your result. Choose what comes next.</li></ol>
            <button type="button" className="btn btn-primary btn-lg btn-block" onClick={beginTest}>Start question 1</button>
          </div></div>
        </main>
      )}

      {phase === 'question' && (
        <main className="test-shell">
          <div className="test-top">
            <Palette states={states} label="Progress" />
            <span className={`pill ${timeLeft <= 10 ? 'is-urgent' : ''}`} role="timer" aria-label={`${timeLeft} seconds left`}>
              <Clock size={15} aria-hidden="true" />0:{String(timeLeft).padStart(2, '0')}
            </span>
          </div>

          <div key={question.id} className="qcard q-enter">
            <div className="qmeta">
              <span className="tag"><span className="dot" style={{ background: SUBJECT_COLOR[question.subject] }} />{question.subject}</span>
              <span className="tag">{question.topic}</span>
            </div>
            <p ref={questionHeadingRef} tabIndex={-1} className="qtext qtext-lg">{question.question}</p>

            <div className="options">
              {question.options.map((opt, i) => {
                const state = revealed
                  ? i === question.correctAnswer ? 'is-correct' : i === chosen ? 'is-wrong' : ''
                  : i === selected ? 'is-selected' : ''
                return (
                  <button key={i} type="button" className={`option ${state}`} disabled={revealed} aria-pressed={!revealed && i === selected} onClick={() => setSelected(i)}>
                    <span className="option-key">{LETTER(i)}</span>
                    <span className="option-body">{opt}</span>
                    {revealed && i === question.correctAnswer && <Check size={18} color={GOOD} className="option-icon" aria-label="Correct answer" />}
                    {revealed && i === chosen && i !== question.correctAnswer && <XIcon size={18} color={BAD} className="option-icon" aria-label="Your answer" />}
                  </button>
                )
              })}
            </div>

            {!revealed ? (
              <button type="button" className="btn btn-primary btn-lg btn-block" style={{ marginTop: 20 }} disabled={selected === null} onClick={() => submitAnswer(selected)}>
                Submit answer
              </button>
            ) : (
              <div className="explain" role="status">
                <strong>
                  {recorded?.selected === null
                    ? `Time's up, so this one counts as unanswered. The answer is ${LETTER(question.correctAnswer)}.`
                    : recorded?.correct ? 'Correct.' : `Not quite. The answer is ${LETTER(question.correctAnswer)}.`}
                </strong>
                {question.explanation}
                <div>
                  <button type="button" className="btn btn-primary" onClick={goToNext}>
                    {index === total - 1 ? 'See your results' : 'Next question'}
                  </button>
                </div>
              </div>
            )}
          </div>
        </main>
      )}

      {phase === 'results' && results && (
        <main className="test-shell">
          <div className="result-head">
            <div className="score-big">{results.score}<small>/ {total}</small></div>
            <Palette size="lg" states={answers.map((a) => (a.correct ? 'correct' : 'wrong'))} label="Your answers" />
            <p className="result-line"><strong>{results.accuracy}%</strong> accuracy, <strong>{results.avgTime}s</strong> on average per question</p>
          </div>

          <div className="panel" style={{ paddingBlock: 8 }}>
            <div className="rows">
              {Object.entries(results.bySubject).map(([subject, s]) => (
                <div key={subject} className="row">
                  <span className="dot" style={{ background: SUBJECT_COLOR[subject] }} />
                  <span className="row-main">{subject}</span>
                  <span className="row-value">{s.correct} / {s.total}</span>
                </div>
              ))}
            </div>
          </div>

          <p className="story-close">In 1989, Sundar Pichai was a student just starting out. <strong>Today you took your first step.</strong></p>

          {isAuthenticated ? (
            <>
              {saveState === 'saving' && <p className="hint" style={{ marginBottom: 12 }}>Saving your result…</p>}
              {saveState === 'saved' && <p className="hint hint-ok" style={{ marginBottom: 12 }}>Saved to your dashboard.</p>}
              {saveState === 'error' && <p className="note" style={{ marginBottom: 14 }}>Couldn't save it yet. Finish setting up your profile and it will appear on your dashboard.</p>}
              {attemptId && (
                <div style={{ marginBottom: 20, textAlign: 'left' }}>
                  <RankPredictor attemptId={attemptId} />
                </div>
              )}
              <button type="button" className="btn btn-primary btn-lg" onClick={() => navigate('/dashboard')}>Go to your dashboard</button>
            </>
          ) : (
            <>
              <button type="button" className="btn btn-primary btn-lg" onClick={goToSignup}>Create a free account to save this result</button>
              <p className="hint" style={{ marginTop: 12 }}>An account also unlocks full mocks, subject tests and your score history.</p>
            </>
          )}
        </main>
      )}
    </div>
  )
}
