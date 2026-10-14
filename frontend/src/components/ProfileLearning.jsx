import { Link } from 'react-router-dom'
import { useEffect, useState } from 'react'
import { request } from '../lib/api.js'
import { examLabel } from './StudentProfileStory.jsx'

export function LearningSnapshot({ data }) {
  return <section className="pp-card">
    <div className="pp-section-heading"><div><p className="pp-eyebrow">ONLY YOU CAN SEE THIS</p><h2>Your preparation, in focus.</h2></div><span className="pp-chip">Last {data.days} days · {examLabel(data.exam)}</span></div>
    <div className="pp-learning-stats"><div><strong>{data.completed_tests}</strong><span>Submitted tests</span></div><div><strong>{data.answered}</strong><span>Questions answered</span></div><div><strong>{data.accuracy == null ? '—' : `${data.accuracy}%`}</strong><span>Fully correct answers</span></div></div>
    {data.subjects.length ? <><h3 className="pp-subheading">Subject snapshot</h3><div className="pp-subjects">{data.subjects.map(s => <div key={s.name}><div><strong>{s.name}</strong><span>{s.accuracy}% fully correct</span></div><div className="pp-subject-track" role="meter" aria-label={`${s.name} fully correct answers`} aria-valuemin={0} aria-valuemax={100} aria-valuenow={s.accuracy}><i style={{ width: `${s.accuracy}%` }} /></div><small>{s.correct} of {s.answered} answered{s.answered < 10 ? ' · Early sample' : ''}</small></div>)}</div><p className="pp-muted">Correct ÷ answered questions. Partial answers count as answered; skipped and timed-out responses are excluded. Reattempts count separately. Results awaiting release are excluded.</p></> : <div className="pp-progress-empty"><p>No answered questions in this exam yet. Your subject snapshot will grow with your practice.</p><Link to="/practice" className="btn btn-primary">Start practising</Link></div>}
  </section>
}

export default function ProfileLearning() {
  const [data, setData] = useState(null)
  const [error, setError] = useState('')
  const [retry, setRetry] = useState(0)
  useEffect(() => {
    let active = true
    setError('')
    request('/api/profile/learning-summary').then(result => { if (active) setData(result) }).catch(e => { if (active) setError(e.message) })
    return () => { active = false }
  }, [retry])
  if (error) return <section className="pp-card" role="alert"><p>{error}</p><button className="btn btn-secondary" onClick={() => setRetry(n => n + 1)}>Retry progress</button></section>
  if (!data) return <section className="pp-card" role="status">Loading your preparation…</section>
  return <LearningSnapshot data={data} />
}
