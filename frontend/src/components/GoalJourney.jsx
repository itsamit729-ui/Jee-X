import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { ArrowRight, Check, Flag, RefreshCw, ChevronDown } from 'lucide-react'
import { request } from '../lib/api.js'
import './goal-journey.css'

const subjectNames = { PHY: 'Physics', CHEM: 'Chemistry', MATH: 'Mathematics' }
const when = value => new Date(value.includes('T') ? `${value.replace(/Z$/, '')}Z` : `${value}T12:00:00`).toLocaleDateString('en-IN', { day: 'numeric', month: 'short' })
const statusLabel = { met: 'Evidence met', current: 'Your next milestone', upcoming: 'Ahead of you', recheck: 'Time to recheck' }

export function JourneyPanel({ data, compact = false, afterTest = false }) {
  const active = data.milestones.find(m => m.id === data.active_id)
  const completed = data.milestones.filter(m => m.met).length
  const [subject, setSubject] = useState('ALL')
  const focus = data.focus.filter(s => subject === 'ALL' || s.subject === subject)
  return <section className={`goal-journey ${compact ? 'journey-compact' : ''}`} aria-label={afterTest ? 'How this test updates your path' : 'Your path to your goal'}>
    <header className="journey-heading"><div><span className="journey-eyebrow">{afterTest ? 'AFTER THIS TEST' : 'YOUR GOAL, ONE STEP AT A TIME'}</span><h2>{afterTest ? 'Your work changes what comes next.' : compact ? 'Today has a place in your bigger plan.' : 'From here to exam day.'}</h2></div><span className="journey-goal"><Flag size={15}/>{data.saved ? data.goal_label : 'Choose your goal'}</span></header>
    {!data.saved && <p className="journey-setup">This is a starting plan. <Link to="/roadmap">Save your marks or college goal <ArrowRight size={14}/></Link></p>}
    <div className="journey-outlook"><div><span>Current baseline</span><strong>{data.standing.score == null ? 'Let’s establish it' : <>{data.standing.score}<small> / 300</small></>}</strong></div><div><span>{data.standing.gap == null ? 'Evidence so far' : 'Gap to your target'}</span><strong>{data.standing.gap == null ? `${data.evidence.fresh_answers} fresh answers` : `${data.standing.gap} marks`}</strong></div><div><span>{data.standing.range ? 'Recent assessment range' : 'Readiness picture'}</span><strong>{data.standing.range ? `${data.standing.range[0]}–${data.standing.range[1]} / 300` : 'Still taking shape'}</strong></div></div>
    <div className="journey-current"><div><span className="journey-eyebrow">STEP {active.number} OF {data.milestones.length} · {data.evidence.level}</span><h3>{active.title}</h3><p>{active.purpose}</p><span className="journey-progress-copy">{active.progress}</span></div><div className="journey-actions">{active.id === 'baseline' || ['mocks', 'goal'].includes(active.id) ? <Link className="btn btn-primary" to={active.id === 'goal' && data.standing.target == null ? '/roadmap#college-outlook' : '/recommendations?assessment=1'}>{active.id === 'goal' && data.standing.target == null ? 'Review college outlook' : 'Take a balanced assessment'}<ArrowRight size={16}/></Link> : compact && !afterTest ? <a className="btn btn-primary" href="#practice-builder">Continue my practice<ArrowRight size={16}/></a> : <Link className="btn btn-primary" to={afterTest ? '/roadmap#milestones' : '/recommendations'}>{afterTest ? 'See my updated roadmap' : 'Continue my practice'}<ArrowRight size={16}/></Link>}{compact && <Link className="journey-text-link" to="/roadmap#milestones">See the complete journey <ArrowRight size={14}/></Link>}</div></div>
    <div className="journey-changes"><span className="journey-eyebrow">{afterTest ? 'WHAT CHANGED' : 'LATEST PLAN UPDATE'}</span><ul>{data.changes.map((message, i) => <li key={i}>{message}</li>)}</ul></div>
    {!compact && <>
      <div className="journey-section-head" id="milestones"><div><span className="journey-eyebrow">THE COMPLETE PATH</span><h3>Every milestone. A clear next step.</h3></div><span>{completed} / {data.milestones.length} with current evidence</span></div>
      <p className="journey-note">{data.exam_date ? `Planning toward ${when(data.exam_date)} ${data.target_year}.` : `${data.target_year} target year · exam date will be added when configured.`} {data.timeline_note}</p>
      <ol className="journey-timeline">{data.milestones.map(m => <li key={m.id} className={`journey-milestone is-${m.status}`} aria-current={m.id === data.active_id ? 'step' : undefined}><span className="journey-node">{m.met ? <Check size={17}/> : String(m.number).padStart(2, '0')}</span><details open={m.id === data.active_id}><summary><div><span className="journey-eyebrow">{statusLabel[m.status]}</span><h4>{m.title}</h4><p>{m.progress}</p></div><ChevronDown size={18}/></summary><div className="journey-milestone-body"><p>{m.purpose}</p><div><strong>What completes this step</strong><p>{m.requirement}</p></div>{m.first_met_at && <small>First achieved {when(m.first_met_at)}. Current evidence is checked again as it ages.</small>}</div></details></li>)}</ol>
      <div className="journey-finish"><Flag size={21}/><div><strong>Exam day is the destination. Revision keeps you ready.</strong><p>Milestones can develop together across subjects. Once the evidence is met, keep checking retention and full-test consistency until your exam.</p></div></div>
      <div className="journey-section-head"><div><span className="journey-eyebrow">YOUR NEXT SEVEN DAYS</span><h3>Where your effort matters next.</h3></div><div className="journey-filters" role="group" aria-label="Filter priorities by subject">{['ALL', ...Object.keys(subjectNames)].map(code => <button key={code} aria-pressed={subject === code} onClick={() => setSubject(code)}>{subjectNames[code] || 'All'}</button>)}</div></div>
      <div className="journey-focus-grid">{focus.map(s => <article key={s.chapter_id}><span className="journey-eyebrow">{subjectNames[s.subject]}</span><h4>{s.title}</h4><p>{s.reason}</p><div className="journey-focus-stat"><strong>{s.accuracy}%</strong><span>first-exposure accuracy<br/>{s.answered} answers · {s.days} practice days</span></div><Link to={`/recommendations?subject=${s.subject}&chapter=${s.chapter_id}`}>Work on this chapter <ArrowRight size={14}/></Link></article>)}</div>
      {!focus.length && <p className="journey-note">{data.focus.length ? 'No priority chapter in this subject yet. Try a subject session to build evidence.' : 'Start with a balanced assessment or short practice session. Your chapter priorities will appear here.'}</p>}
      <details className="journey-method"><summary>How your plan adapts</summary><p>{data.evidence_note}</p><p>Evidence updates after each submitted test when you open your plan. Weekly work refreshes after three submitted sessions or seven days. A single result does not erase earlier achievements.</p><p>The score range describes past assessments, not predicted improvement. No future marks or admission outcome is promised.</p></details>
      {data.history.length > 0 && <details className="journey-method"><summary>Recent plan updates</summary><ol>{[...data.history].reverse().map((h, i) => <li key={i}><strong>{when(h.date)}</strong><p>{h.messages.join(' ')}</p></li>)}</ol></details>}
    </>}
  </section>
}

export default function GoalJourney({ afterTest = false, attemptId }) {
  const [data, setData] = useState(null)
  const [error, setError] = useState('')
  const [retry, setRetry] = useState(0)
  useEffect(() => {
    let active = true
    setError(''); setData(null)
    request('/api/roadmap/journey', { cache: false }).then(value => { if (active) setData(value) }).catch(e => { if (active) setError(e.message) })
    return () => { active = false }
  }, [attemptId, retry])
  if (error) return <div className="journey-loading" role="alert">Your practice is available. We couldn’t load your plan. <button className="btn btn-secondary" onClick={() => setRetry(v => v + 1)}><RefreshCw size={14}/>Retry plan</button></div>
  if (!data) return <div className="journey-loading" role="status">Connecting today’s practice to your goal…</div>
  return <JourneyPanel data={data} compact afterTest={afterTest}/>
}
