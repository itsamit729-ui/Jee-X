import { AssignedTestsPreview } from '../components/classroom/shared.jsx'
import { request } from '../lib/api.js'
import { ArrowUpRight, Target, Clock3, ArrowRight, BookOpen, CalendarCheck, GraduationCap, Users, Shapes, ChevronDown } from 'lucide-react'
import { Link } from 'react-router-dom'
import { preloadRoute } from '../lib/preloadRoute.js'
import './dashboard.css'
import RatingSummary from '../components/RatingSummary.jsx'
import { lazy, Suspense, useEffect, useMemo, useState } from 'react'
import { useNavigate } from 'react-router-dom'
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
  const [category, setCategory] = useState('All tools')
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
  const tools = [
    { title: 'Subject practice', description: 'Pick a chapter. Give it your full attention.', category: 'Practice', tag: 'YOUR PACE', Icon: Target, to: '/subject-test' },
    { title: 'PYQs & shift papers', description: 'MHT-CET shifts and BITSAT question collections.', category: 'Practice', tag: 'THE QUESTION ARCHIVE', Icon: BookOpen, to: '/pyq' },
    { title: 'Full mock test', description: 'Get comfortable with the paper and the clock.', category: 'Practice', tag: 'EXAM REHEARSAL', Icon: Clock3, to: profile?.target_exam === 'mht_cet' ? '/pyq?exam=mht_cet' : '/test' },
    { title: 'College outlook', description: 'Explore historical cutoffs and your college goals.', category: 'Discover', tag: 'YOUR NEXT CHAPTER', Icon: GraduationCap, to: profile?.target_exam === 'mht_cet' ? '/pyq?exam=mht_cet' : '/plan' },
    { title: 'Exam situations', description: 'Work through the tricky moments before exam day.', category: 'Practice', tag: '15–45 MINUTES', Icon: Shapes, to: '/scenarios' },
    { title: 'My classroom', description: 'Your classes, assignments and next submission.', category: 'Together', tag: 'LEARN TOGETHER', Icon: Users, to: '/classes' },
  ]
  const shownTools = category === 'All tools' ? tools : tools.filter(tool => tool.category === category)
  const examName = { jee_main: 'JEE Main', jee: 'JEE Main', mht_cet: 'MHT-CET', bitsat: 'BITSAT', jee_advanced: 'JEE Advanced' }[profile?.target_exam] || 'Your preparation'
  return <div className="crackjee-root edge-dashboard"><AppHeader/>
    <main className="edge-desk" onPointerOver={preloadRoute} onFocus={preloadRoute}>
      <header className="edge-desk-heading"><div><div className="edge-desk-context"><span>YOUR STUDY SPACE</span><i/><span>{examName}</span></div><h1>{profile?.name ? `Ready when you are, ${profile.name.split(' ')[0]}.` : 'Ready when you are.'}</h1><p>A little focus today. A little more confidence tomorrow.</p></div><div className="edge-desk-date"><CalendarCheck size={15}/>{new Date().toLocaleDateString('en-IN', { weekday:'short', day:'numeric', month:'short' })}</div></header>
      {error ? <div className="panel" role="alert"><p>{error}</p><button className="btn btn-secondary" onClick={() => setLoadVersion(v => v + 1)}>Try again</button></div> : <>
      <section className="edge-desk-stats" aria-label="Your progress summary">{(statCards || [{v:'0',l:'Tests',k:'tests'},{v:'—',l:'Best score',k:'best'},{v:'—',l:'Best accuracy',k:'acc'},{v:'0',l:'Questions solved',k:'solved'}]).filter(stat => stat.k !== 'avg').map((item,i) => <div key={item.k}><span>{item.l}</span><strong>{item.v}</strong><span className="edge-stat-index" aria-hidden="true">0{i+1}</span></div>)}</section>
      <div className="edge-desk-focus-row"><section className="edge-desk-focus"><div className="edge-focus-copy"><span className="edge-desk-label"><Target size={14}/> YOUR PERSONAL STUDY PLAN</span><h2>Your next step.<br/><span>A little clearer.</span></h2><p>Find your focus, understand why it matters, and turn today’s practice into a plan.</p><Link className="btn btn-primary" to="/plan">Open my study plan<ArrowUpRight size={17}/></Link></div><div className="edge-focus-path" aria-label="Study cycle"><div><span>01</span><p>Find your focus<small>Know what needs attention</small></p></div><div><span>02</span><p>Put it into practice<small>Build understanding, question by question</small></p></div><div><span>03</span><p>See what changed<small>Review, learn and go again</small></p></div></div></section>
      <aside className="edge-desk-side"><div className="edge-side-heading"><span>YOUR MOMENTUM</span><ArrowUpRight size={16}/></div><RatingSummary initialRating={rating}/><Link className="edge-daily-link" to="/daily"><span className="edge-daily-icon"><CalendarCheck size={21}/></span><div><strong>A small win for today</strong><p>Open your daily question</p></div><ArrowRight size={16}/></Link><div className="edge-last-session"><span>{latest ? 'LAST SESSION' : 'A FRESH START'}</span><p>{latest ? <><strong>{latest.score ?? '—'} marks</strong> · {Math.round(latest.accuracy || 0)}% accuracy</> : 'Your first session starts your progress story.'}</p>{latest && <small>{new Date(latest.created_at).toLocaleDateString('en-IN', {day:'numeric',month:'short'})}</small>}</div></aside></div>
      <AssignedTestsPreview/>
      <section className="edge-desk-tools" aria-labelledby="tools-title"><div className="edge-tools-heading"><div><span className="edge-desk-label">MAKE IT YOUR KIND OF SESSION</span><h2 id="tools-title">What would you like to work on?</h2></div><div role="group" aria-label="Filter study tools">{['All tools','Practice','Discover','Together'].map(value => <button key={value} aria-pressed={value === category} onClick={() => setCategory(value)}>{value}</button>)}</div></div><div className="edge-tool-grid" key={category}>{shownTools.map(({title,description,tag,Icon,to},i) => <Link className="edge-tool-card" key={to+title} to={to} style={{ '--card-index': i }}><span className="edge-tool-icon"><Icon size={21} strokeWidth={1.5}/></span><div><small>{tag}</small><h3>{title}</h3><p>{description}</p></div><ArrowUpRight size={17}/></Link>)}</div><p className="edge-tools-note">MHT-CET college comparisons appear after a mock, using a percentile you enter. <Link to="/advanced">Explore IIT & Advanced<ArrowUpRight size={12}/></Link></p></section>
      <details className="edge-desk-history" onToggle={e => setShowTrends(e.currentTarget.open)}><summary><span>Look back. Move forward.<small>{attempts.length} recorded {attempts.length === 1 ? 'session' : 'sessions'}</small></span><span>Results & trends<ChevronDown size={17}/></span></summary>{attempts.length ? <div className="edge-history-table"><div className="edge-history-labels"><span>SESSION DATE</span><span>SCORE</span><span>ACCURACY</span></div>{[...attempts].sort((a,b) => new Date(b.created_at)-new Date(a.created_at)).slice(0,10).map((attempt,i) => <div key={attempt.id || i}><span>{new Date(attempt.created_at).toLocaleDateString('en-IN',{day:'numeric',month:'short',year:'numeric'})}</span><strong>{attempt.score ?? '—'} marks</strong><span>{Math.round(attempt.accuracy || 0)}%</span></div>)}</div> : <p className="edge-history-empty">Your completed sessions will appear here. Start with a subject you want to work on.</p>}{showTrends && history?.length > 0 && <Suspense fallback={<p className="edge-history-empty">Loading trends…</p>}><ProgressTrends history={history} subjectTrends={subjectTrends}/></Suspense>}</details>
      <footer className="edge-desk-footer"><span>Good progress starts with showing up.</span><Link to="/syllabus">Browse the syllabus<ArrowUpRight size={13}/></Link></footer>
      </>}
    </main></div>
}
