import { useCallback, useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { ArrowUpRight, Bell, BookOpen, RefreshCw } from 'lucide-react'
import { request } from '../../lib/api.js'
import AppHeader from '../AppHeader.jsx'
import './classroom.css'

export const classApi = (path, options = {}) => request(`/api${path}`, { cache: false, ...options })
export const when = value => new Date(value).toLocaleString('en-IN', { day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit' })
export const statusLabel = value => ({ not_started: 'Ready to start', upcoming: 'Opens soon', in_progress: 'In progress', submitted: 'Submitted', expired: 'Closed' }[value] || value)
export function ErrorMessage({ error }) { return error ? <p className="cl-error" role="alert">{error}</p> : null }
export function Empty({ title, children }) { return <div className="cl-empty"><BookOpen size={28}/><h3>{title}</h3><p>{children}</p></div> }
export function Shell({ eyebrow, title, intro, action, children }) {
  return <div className="crackjee-root cl-root"><AppHeader/><main className="cl-wrap"><header className="cl-hero"><div><span className="cl-eyebrow">{eyebrow}</span><h1>{title}</h1><p>{intro}</p></div>{action}</header>{children}</main></div>
}
export function useLoad(path) {
  const [data, setData] = useState(null), [error, setError] = useState(''), [loading, setLoading] = useState(true)
  const reload = useCallback(async () => { setLoading(true); setError(''); try { const next = await classApi(path); setData(next); return next } catch (e) { setError(e.message) } finally { setLoading(false) } }, [path])
  useEffect(() => { let active = true; setLoading(true); setError(''); classApi(path).then(d => { if (active) setData(d) }).catch(e => { if (active) setError(e.message) }).finally(() => { if (active) setLoading(false) }); return () => { active = false } }, [path])
  return { data, setData, error, loading, reload }
}
export function LoadState({ loading, error, reload }) { return <>{loading && <p className="cl-muted" role="status"><RefreshCw size={14} className="spin"/> Loading…</p>}<ErrorMessage error={error}/>{error && <button className="btn btn-secondary" onClick={reload}>Try again</button>}</> }
export function AssignmentCard({ assignment: a, teacher = false }) {
  return <article className="cl-card cl-assignment"><div className="cl-row"><span className={`cl-pill ${a.status === 'in_progress' ? 'accent' : ''}`}>{teacher ? `${a.submitted}/${a.recipients} submitted` : statusLabel(a.status)}</span><span className="cl-muted">{a.duration_sec / 60} min</span></div><h3>{a.title}</h3><p>{a.question_count} questions · +{a.marks_correct} / −{a.marks_wrong}</p><div className="cl-card-bottom"><span>Due {when(a.due_at)}{a.score != null && <strong>{a.score} / {a.max_score} marks</strong>}</span><Link className="cl-icon-link" aria-label={`${teacher ? 'Report for' : 'Open'} ${a.title}`} to={teacher ? `/teacher?report=${a.id}` : `/assignments/${a.id}`}><ArrowUpRight size={22}/></Link></div></article>
}
export function AssignedTestsPreview() {
  const { data } = useLoad('/classrooms')
  const pending = data?.assignments.filter(a => ['not_started', 'in_progress'].includes(a.status)) || []
  if (!pending.length) return null
  return <div className="wrap cl-preview"><Link to="/classes"><span className="cl-icon"><Bell size={20}/></span><span><strong>{pending.length === 1 ? 'A test from your teacher is ready' : `${pending.length} class tests are waiting`}</strong><small>{pending[0].title} · Due {when(pending[0].due_at)}</small></span><ArrowUpRight size={20}/></Link></div>
}
