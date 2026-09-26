import RatingSummary from '../components/RatingSummary.jsx'
import { useEffect, useMemo, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '../auth/AuthContext.jsx'
import { api } from '../lib/api.js'
import { syncPendingFreeTest } from '../lib/pendingFreeTest.js'
import { DashboardOverview, useCrackJeeStyles } from '../crackjee/screens.jsx'
import { PHYSICS, CHEM, MATHS, AMBER, SLATE } from '../crackjee/ui.js'
import AppHeader from '../components/AppHeader.jsx'
import { Loader } from '../components/Brand.jsx'

function accuracyPct(sub) {
  return sub && sub.total > 0 ? Math.round((sub.correct / sub.total) * 100) : 0
}

// Turns the raw list of attempts into the props DashboardOverview renders:
// stat cards, a score-trend series, and per-subject accuracy trends.
function buildDashboardData(attempts) {
  if (!attempts.length) return { statCards: null, history: null, subjectTrends: null }

  const ordered = [...attempts].sort(
    (a, b) => new Date(a.created_at) - new Date(b.created_at),
  )

  const history = ordered.map((a, i) => ({
    t: `M${i + 1}`,
    s: a.score,
    d: new Date(a.created_at).toLocaleDateString('en-IN', { day: 'numeric', month: 'short' }),
  }))

  const subjectTrends = ordered.map((a, i) => {
    const b = a.subject_breakdown || {}
    return {
      t: `M${i + 1}`,
      P: accuracyPct(b.Physics),
      C: accuracyPct(b.Chemistry),
      M: accuracyPct(b.Mathematics),
    }
  })

  const bestScore = Math.max(...ordered.map((a) => a.score))
  const avgScore = Math.round(ordered.reduce((s, a) => s + a.score, 0) / ordered.length)
  const bestAcc = Math.round(Math.max(...ordered.map((a) => a.accuracy)))
  const qsSolved = ordered.reduce((s, a) => s + a.total_questions, 0)

  const statCards = [
    { v: String(ordered.length), l: 'Tests', k: 'tests', c: PHYSICS },
    { v: String(bestScore), l: 'Best score', k: 'best', c: AMBER },
    { v: String(avgScore), l: 'Avg score', k: 'avg', c: CHEM },
    { v: `${bestAcc}%`, l: 'Best accuracy', k: 'acc', c: MATHS },
    { v: String(qsSolved), l: 'Questions solved', k: 'solved', c: SLATE },
  ]

  return { statCards, history, subjectTrends }
}

export default function Dashboard() {
  useCrackJeeStyles()
  const { logout } = useAuth()
  const navigate = useNavigate()
  const [profile, setProfile] = useState(null)
  const [attempts, setAttempts] = useState([])
  const [rating, setRating] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [loadVersion, setLoadVersion] = useState(0)

  useEffect(() => {
    let active = true
    setLoading(true)
    setError('')
    ;(async () => {
      try {
        await syncPendingFreeTest()
        const desk = await api.dashboard()
        if (!active) return
        if (!desk.onboarded) { navigate('/onboarding', { replace: true }); return }
        setProfile(desk.profile)
        setAttempts(desk.attempts)
        setRating(desk.rating)
      } catch (e) {
        if (active) setError(e.message || 'Your study desk couldn’t load. Please try again.')
      } finally {
        if (active) setLoading(false)
      }
    })()
    return () => { active = false }
  }, [navigate, loadVersion])

  const { statCards, history, subjectTrends } = useMemo(
    () => buildDashboardData(attempts),
    [attempts],
  )

  if (loading) return <Loader fullScreen label="Loading your dashboard" />

  return (
    <div className="crackjee-root">
      <AppHeader />
      {error && <div className="wrap" role="alert" style={{ paddingTop: 24 }}><div className="panel"><p>{error}</p><button className="btn btn-secondary btn-sm" style={{ marginTop: 12 }} onClick={() => setLoadVersion(v => v + 1)}>Try again</button></div></div>}
      {!error && <div className="wrap"><RatingSummary initialRating={rating} /></div>}
      {!error && <DashboardOverview
        profile={profile}
        statCards={statCards}
        history={history}
        subjectTrends={subjectTrends}
        onStart={() => navigate('/test')}
        onBuddy={() => navigate('/buddy')}
        onFreeTest={() => navigate('/free-test')}
        onSubjectTest={() => navigate('/subject-test')}
        onProfile={() => navigate('/profile')}
        onLogout={() => logout()}
        onHome={() => navigate('/')}
      />}
      {!error && <div className="wrap" style={{ paddingBottom: 40 }}><div className="panel" style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 18, flexWrap: 'wrap' }}>
        <div><span className="section-label">EXAM SITUATIONS</span><h2 style={{ margin: '7px 0' }}>Practice the moment that matters.</h2><p className="muted" style={{ margin: 0 }}>A three-hour exam in view. Play only the crucial 15–45 minutes.</p></div>
        <button type="button" className="btn btn-primary" onClick={() => navigate('/scenarios')}>Explore situations →</button>
      </div></div>}
    </div>
  )
}
