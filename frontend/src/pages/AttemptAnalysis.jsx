import { useEffect, useState } from 'react'
import { Link, useLocation, useNavigate, useParams } from 'react-router-dom'
import { ArrowLeft } from 'lucide-react'
import AppHeader from '../components/AppHeader.jsx'
import AttemptReport from '../components/AttemptReport.jsx'
import GoalJourney from '../components/GoalJourney.jsx'
import RankPredictor from '../components/RankPredictor.jsx'
import MhtCollegePredictor from '../components/MhtCollegePredictor.jsx'
import { attemptAnalysisService } from '../lib/subjectTests.js'
import { attemptKind, buddyResult, nextTestPath } from '../lib/attemptAnalysis.js'
import './practice.css'

const formatDate = (value) => new Date(value).toLocaleString('en-IN', { day: 'numeric', month: 'short', year: 'numeric', hour: 'numeric', minute: '2-digit' })

// Older full mocks were scored in the browser and only their totals were kept.
export function SummaryOnly({ data }) {
  const { summary, subject_breakdown: breakdown } = data
  const diagnostic=data.meta?.kind==='free_diagnostic'
  return <section className="panel attempt-summary-note">
    <div className="score-big">{summary.score ?? '—'}<small>{diagnostic ? `/ ${summary.total_questions} correct` : ' marks'}</small></div>
    <p className="result-line" style={{ marginTop: 12 }}><strong>{Math.round(summary.accuracy || 0)}%</strong> accuracy</p>
    {Object.keys(breakdown).length > 0 && <div className="rows" style={{ marginTop: 12 }}>
      {Object.entries(breakdown).map(([subject, d]) => <div key={subject} className="row"><span className="row-main">{subject}</span><span className="row-value">{d.correct}/{d.total}</span></div>)}
    </div>}
    <p className="muted" style={{ marginTop: 16 }}>This test was taken before question-by-question results were saved, so only its totals are available.</p>
  </section>
}

export default function AttemptAnalysis() {
  const { attemptId } = useParams()
  const navigate = useNavigate()
  const location = useLocation()
  const [data, setData] = useState(null)
  const [error, setError] = useState(null)
  const [retry, setRetry] = useState(0)
  // Coins and streak only arrive with the submit response, never on a reopen.
  const [submitted] = useState(() => location.state?.submitted || null)

  useEffect(() => {
    if (location.state?.submitted) navigate(location.pathname, { replace: true, state: null })
  }, [])

  useEffect(() => {
    let active = true
    setError(null); setData(null)
    attemptAnalysisService.get(attemptId)
      .then((value) => { if (active) setData(value) })
      .catch((e) => { if (active) setError(e) })
    return () => { active = false }
  }, [attemptId, retry])

  const shell = (children) => <div className="crackjee-root"><AppHeader /><main className="wrap page">{children}</main></div>

  if (error) return shell(<div className="empty" role="alert">
    <h3>{error.status === 404 ? 'Result not found' : error.status === 403 ? 'Open this from your class' : 'We couldn’t load this result'}</h3>
    <p>{error.status === 404 ? 'It may belong to another account.' : error.message}</p>
    <div className="hero-actions">
      {![403, 404, 409].includes(error.status) && <button type="button" className="btn btn-primary" onClick={() => setRetry((v) => v + 1)}>Try again</button>}
      <Link className="btn btn-secondary" to={error.status === 403 ? '/classes' : '/dashboard'}>{error.status === 403 ? 'My classes' : 'Back to dashboard'}</Link>
    </div>
  </div>)
  if (!data) return shell(<p className="muted" role="status">Loading your result…</p>)

  const { meta } = data
  const pyq = ['bitsat', 'mht_cet'].includes(meta.pattern)
  return shell(<>
    <button type="button" className="btn btn-quiet btn-sm back" onClick={() => navigate('/dashboard')}><ArrowLeft size={16} aria-hidden="true" />Dashboard</button>
    <div className="page-head">
      <div>
        <span className="eyebrow">{attemptKind(meta).toUpperCase()}</span>
        <h1 className="page-title">{meta.title}</h1>
        <p className="page-sub">Submitted {formatDate(meta.submitted_at)}</p>
      </div>
      <div className="page-actions">
        {data.detail_available && <Link className="btn btn-secondary" to="/buddy" state={{ result: buddyResult(data) }}>Ask Buddy about this result</Link>}
        <Link className="btn btn-primary" to={nextTestPath(meta)}>Start another</Link>
      </div>
    </div>
    {submitted?.coins_earned > 0 && <p className="alert" role="status">You earned {submitted.coins_earned} Edge Coins{submitted.current_streak ? ` · ${submitted.current_streak}-day streak` : ''}.</p>}

    {data.detail_available ? <AttemptReport data={data} /> : <SummaryOnly data={data} />}

    {data.detail_available && <div className="stack" style={{ marginTop: 24 }}>
      {meta.pattern === 'mht_cet' && meta.is_mock && <MhtCollegePredictor attemptId={meta.attempt_id} />}
      {meta.pattern === 'jee_main' && meta.is_mock && <RankPredictor attemptId={meta.attempt_id} />}
      {!pyq && meta.kind !== 'daily' && <GoalJourney afterTest attemptId={meta.attempt_id} />}
      {!pyq && !meta.is_mock && meta.kind !== 'daily' && <details className="journey-method"><summary>Explore rank and college reference data</summary><RankPredictor attemptId={meta.attempt_id} /></details>}
    </div>}
  </>)
}
