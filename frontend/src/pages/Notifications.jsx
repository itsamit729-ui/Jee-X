import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { ArrowUpRight, Bell } from 'lucide-react'
import { classApi, Empty, ErrorMessage, LoadState, Shell, useLoad, when } from '../components/classroom/shared.jsx'

export default function Notifications() {
  const { data, loading, error, reload } = useLoad('/notifications')
  const [actionError, setActionError] = useState(''), [busy, setBusy] = useState(null)
  const navigate = useNavigate()
  async function open(item) {
    setBusy(item.id); setActionError('')
    try { if (!item.read) await classApi(`/notifications/${item.id}/read`, { method: 'POST' }); window.dispatchEvent(new Event('jee-inbox-changed')); navigate(item.href) } catch (e) { setActionError(e.message) } finally { setBusy(null) }
  }
  return <Shell eyebrow="YOUR INBOX" title="Stay in the loop." intro="Class tests, deadlines and solutions, all in one place." action={<button className="btn btn-secondary" onClick={reload} disabled={loading}>Refresh inbox</button>}><LoadState {...{ loading, error, reload }}/><ErrorMessage error={actionError}/>{data && <section className="cl-inbox"><div className="cl-section-head"><h2>{data.unread_count ? `${data.unread_count} unread` : 'You’re up to date'}</h2><span className="cl-muted">In-app notifications</span></div>{data.items.length ? data.items.map(item => <button className={`cl-notification ${item.read ? '' : 'unread'}`} key={item.id} onClick={() => open(item)} disabled={busy !== null}><span className="cl-icon"><Bell size={19}/></span><span className="cl-grow"><strong>{item.title}</strong><p>{item.body}</p><small>{when(item.created_at)}{!item.read && ' · Unread'}</small></span><ArrowUpRight size={19}/></button>) : <Empty title="A quiet moment">Your teacher’s next assignment will appear here. Notifications update while Jee Edge is open.</Empty>}</section>}</Shell>
}
