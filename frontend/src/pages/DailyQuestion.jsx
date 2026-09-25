import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Flame, Coins } from 'lucide-react'
import { dailyQuestionService } from '../lib/dailyQuestion.js'
import { subjectTestGraderService } from '../lib/subjectTests.js'
import MathText from '../components/MathText.jsx'
import QuestionAssets from '../components/QuestionAssets.jsx'
import AppHeader from '../components/AppHeader.jsx'
import { Loader } from '../components/Brand.jsx'
import { GOOD, BAD } from '../crackjee/ui.js'

const OUTCOME = { correct: 'correct', wrong: 'wrong' }

export default function DailyQuestion() {
  const navigate = useNavigate()


  const [state, setState] = useState('loading') // loading | question | already-answered | error
  const [today, setToday] = useState(null)
  const [selectedOption, setSelectedOption] = useState(null)
  const [numericAnswer, setNumericAnswer] = useState('')
  const [error, setError] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const [result, setResult] = useState(null)

  useEffect(() => {
    (async () => {
      try {
        const data = await dailyQuestionService.getToday()
        setToday(data)
        setState(data.already_answered ? 'already-answered' : 'question')
      } catch (e) {
        setError(e.message)
        setState('error')
      }
    })()
  }, [])

  const submit = async () => {
    setError('')
    setSubmitting(true)
    try {
      const q = today.question
      const payload = [{
        question_id: q.question_id,
        option_ids: selectedOption ? [selectedOption] : [],
        numeric_answer: numericAnswer === '' ? null : Number(numericAnswer),
        time_taken_sec: 0,
      }]
      const res = await subjectTestGraderService.submit(today.attempt_id, payload)
      setResult(res)
    } catch (e) {
      setError(e.message)
    } finally {
      setSubmitting(false)
    }
  }

  if (state === 'loading') return <Loader fullScreen label="Fetching today's question" />

  if (state === 'error') {
    return (
      <div className="crackjee-root">
        <AppHeader />
        <main className="wrap-narrow page">
          <p className="alert" role="alert">{error || "Couldn't load today's question."}</p>
        </main>
      </div>
    )
  }

  if (state === 'already-answered' && !result) {
    return (
      <div className="crackjee-root">
        <AppHeader />
        <main className="wrap-narrow page">
          <div className="page-head"><h1 className="page-title">Daily question</h1></div>
          <div className="panel">
            <p className="muted" style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
              <Flame size={18} color={GOOD} aria-hidden="true" />
              You've already solved today's question. Current streak: <strong>{today.current_streak} day{today.current_streak === 1 ? '' : 's'}</strong>.
            </p>
            <p className="hint" style={{ marginTop: 10 }}>Come back tomorrow for the next one.</p>
            <button type="button" className="btn btn-primary" style={{ marginTop: 16 }} onClick={() => navigate('/dashboard')}>Back to dashboard</button>
          </div>
        </main>
      </div>
    )
  }

  if (result) {
    const r = result.questions[0]
    return (
      <div className="crackjee-root">
        <AppHeader />
        <main className="wrap-narrow page">
          <div className="page-head"><h1 className="page-title">Daily question</h1></div>
          <div className="panel">
            <div className="solution-head">
              <span className="sq" data-s={OUTCOME[r.outcome] || 'skipped'} />
              <span style={{ fontWeight: 700, color: r.outcome === 'correct' ? GOOD : BAD }}>
                {r.outcome === 'correct' ? 'Correct!' : 'Not quite'}
              </span>
            </div>
            <p style={{ marginTop: 10 }}><MathText text={r.solution} /></p>

            {result.coins_earned > 0 && (
              <p className="note" style={{ marginTop: 14, display: 'flex', alignItems: 'center', gap: 8 }}>
                <Coins size={16} aria-hidden="true" />+{result.coins_earned} Edge Coin{result.coins_earned === 1 ? '' : 's'} earned
              </p>
            )}
            {result.current_streak != null && (
              <p className="hint" style={{ marginTop: 8, display: 'flex', alignItems: 'center', gap: 6 }}>
                <Flame size={15} aria-hidden="true" />Current streak: {result.current_streak} day{result.current_streak === 1 ? '' : 's'}
              </p>
            )}

            <button type="button" className="btn btn-primary" style={{ marginTop: 16 }} onClick={() => navigate('/dashboard')}>Back to dashboard</button>
          </div>
        </main>
      </div>
    )
  }

  const q = today.question
  return (
    <div className="crackjee-root">
      <AppHeader />
      <main className="wrap-narrow page">
        <div className="page-head">
          <div>
            <h1 className="page-title">Daily question</h1>
            <p className="page-sub">Picked for you from your weakest topic. One per day.</p>
          </div>
        </div>

        {error && <p className="alert" role="alert">{error}</p>}

        <div className="qcard">
          <div className="qmeta">
            <span className="tag">{q.ref}</span>
            <span className="tag"><Flame size={13} aria-hidden="true" />{today.current_streak} day streak</span>
          </div>
          {q.passage && <div className="passage"><MathText text={q.passage} /></div>}
          <div className="qtext"><MathText text={q.stem} /></div>
            <QuestionAssets assets={q.assets} />

          {q.type === 'numerical' ? (
            <div className="field" style={{ maxWidth: 280, marginBottom: 0 }}>
              <label className="field-label" htmlFor="daily-numeric">Your answer</label>
              <input id="daily-numeric" type="number" className="input num" placeholder="Type a number"
                value={numericAnswer} onChange={(e) => setNumericAnswer(e.target.value)} />
            </div>
          ) : (
            <div className="options" role="radiogroup" aria-label="Options">
              {q.options.map((o) => (
                <button key={o.id} type="button" role="radio" aria-checked={selectedOption === o.id}
                  className={`option ${selectedOption === o.id ? 'is-selected' : ''}`} onClick={() => setSelectedOption(o.id)}>
                  <span className="option-key">{o.label}</span>
                  <span className="option-body"><MathText text={o.content} /></span>
                </button>
              ))}
            </div>
          )}
        </div>

        <div className="hero-actions" style={{ marginTop: 20 }}>
          <button
            type="button"
            className="btn btn-primary btn-lg"
            disabled={submitting || (q.type === 'numerical' ? numericAnswer === '' : selectedOption === null)}
            onClick={submit}
          >
            {submitting ? <><span className="spin" aria-hidden="true" />Submitting</> : 'Submit answer'}
          </button>
        </div>
      </main>
    </div>
  )
}

