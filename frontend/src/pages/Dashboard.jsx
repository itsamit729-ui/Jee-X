import { AssignedTestsPreview } from '../components/classroom/shared.jsx'
import { request } from '../lib/api.js'
import { ArrowUpRight, Target, Clock3, ArrowRight } from 'lucide-react'
import RatingSummary from '../components/RatingSummary.jsx'
import { lazy, Suspense, useEffect, useMemo, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '../auth/AuthContext.jsx'
import { api } from '../lib/api.js'
import { syncPendingFreeTest } from '../lib/pendingFreeTest.js'
import '../studio-ui.css'
import { PHYSICS, CHEM, MATHS, AMBER, SLATE } from '../crackjee/ui.js'
import AppHeader from '../components/AppHeader.jsx'
import { Loader } from '../components/Brand.jsx'

const ProgressTrends = lazy(() => import('../components/ProgressTrends.jsx'))

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
      P: accuracyPct(b.Physics || b.PHY),
      C: accuracyPct(b.Chemistry || b.CHEM),
      M: accuracyPct(b.Mathematics || b.MATH),
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
  const navigate = useNavigate()
  const [showTrends, setShowTrends] = useState(false)
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
        if (!desk.onboarded) { const access = await request('/api/classrooms/access', { cache: false }); if (active) navigate(access.teacher ? '/teacher' : '/onboarding', { replace: true }); return }
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

  const latest = attempts.length ? [...attempts].sort((a,b) => new Date(b.created_at) - new Date(a.created_at))[0] : null
  return <div className="crackjee-root studio-dashboard"><AppHeader/>
    <main className="studio-workspace">
      <header className="studio-page-heading"><div><span className="studio-overline">YOUR DAILY STARTING POINT</span><h1>{profile?.name ? `Let’s make progress, ${profile.name.split(' ')[0]}.` : 'Let’s make progress.'}</h1><p>A clear next step. Everything else within reach.</p></div><span className="studio-date">{new Date().toLocaleDateString('en-IN', { weekday:'short', day:'numeric', month:'short' })}</span></header>
      {error ? <div className="panel" role="alert"><p>{error}</p><button className="btn btn-secondary" onClick={() => setLoadVersion(v => v + 1)}>Try again</button></div> : <>
      <div className="studio-desk-grid"><section className="studio-focus"><div className="studio-focus-head"><span><Target size={15}/>YOUR PERSONAL PLAN</span><span>01 / START HERE</span></div><div className="studio-focus-body"><h2>Less wondering.<br/><em>More working<br/>on what matters.</em></h2><p>Your recommended topic, the reason behind it, and the next milestone — in one place.</p><button className="btn" onClick={() => navigate('/plan')}>Open my study plan <ArrowUpRight size={18}/></button></div><div className="studio-focus-foot"><span>FIND YOUR FOCUS</span><ArrowRight size={16}/><span>PRACTISE</span><ArrowRight size={16}/><span>REVIEW</span></div></section>
      <aside className="studio-progress"><div className="studio-card-heading"><h2>Your progress</h2><button className="text-action" onClick={() => navigate('/profile')} aria-label="View your profile"><ArrowUpRight size={18}/></button></div><RatingSummary initialRating={rating}/><div className="studio-metrics">{(statCards || [{v:'0',l:'Tests',k:'tests'},{v:'—',l:'Best score',k:'best'},{v:'—',l:'Best accuracy',k:'acc'},{v:'0',l:'Questions solved',k:'solved'}]).filter(s => s.k !== 'avg').map(item => <div key={item.k}><strong>{item.v}</strong><span>{item.l}</span></div>)}</div><div className="studio-latest"><span className="studio-overline">{latest ? 'LATEST SESSION' : 'YOUR FIRST SESSION'}</span><strong>{latest ? `${latest.score ?? '—'} marks · ${Math.round(latest.accuracy || 0)}% accuracy` : 'Your starting point is waiting.'}</strong><p>{latest ? new Date(latest.created_at).toLocaleDateString('en-IN', {day:'numeric',month:'short'}) : 'Complete a session to start building your progress history.'}</p></div></aside></div>
      <section className="studio-session-list" aria-label="Choose a session"><div className="studio-card-heading"><h2>Choose your session</h2><span>Make the time you have count.</span></div><div className="studio-session-grid">{[
        ['01','Focused practice','One subject. One clear focus.','YOUR PACE','/subject-test',Target],
        ['02','Full mock','Rehearse the complete paper.','3 HOURS','/test',Clock3],
        ['03','Exam situations','Practise a difficult exam moment.','15–45 MIN','/scenarios',ArrowRight],
      ].map(([n,title,copy,time,path,Icon]) => <button key={path} className="studio-session" onClick={() => navigate(path)}><span className="studio-session-symbol"><Icon size={22}/></span><span className="studio-session-copy"><small>{time}</small><strong>{title}</strong><span>{copy}</span></span><ArrowUpRight size={20}/></button>)}</div></section>
      <details className="studio-history" onToggle={e => setShowTrends(e.currentTarget.open)}><summary>Recent results <span>{attempts.length} recorded sessions</span></summary>{attempts.length ? <div className="studio-history-list">{[...attempts].sort((a,b) => new Date(b.created_at)-new Date(a.created_at)).slice(0,10).map((attempt,i) => <div key={attempt.id || i}><span>{new Date(attempt.created_at).toLocaleDateString('en-IN')}</span><strong>{attempt.score ?? '—'} marks</strong><span>{Math.round(attempt.accuracy || 0)}% accuracy</span></div>)}</div> : <p>Your completed sessions will appear here.</p>}{showTrends && history?.length > 0 && <Suspense fallback={<p>Loading trends…</p>}><ProgressTrends history={history} subjectTrends={subjectTrends}/></Suspense>}</details>
      <AssignedTestsPreview/>
      </>}
    </main></div>
}
