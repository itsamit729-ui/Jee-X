import { useEffect, useState } from 'react'
import { request } from '../lib/api.js'
export default function AdminPaperAcquisition({ token }) {
  const [data, setData] = useState(null)
  const [error, setError] = useState('')
  const [retry, setRetry] = useState(0)
  useEffect(() => {
    let active = true
    setError('')
    request('/api/admin/paper-acquisition', { token }).then(value => { if (active) setData(value) }).catch(e => { if (active) setError(e.message) })
    return () => { active = false }
  }, [token, retry])
  const sources = [...new Set(data?.rows.map(row => row.source) || [])]
  const count = (source, event) => data.rows.find(row => row.source === source && row.event === event)?.count || 0
  return <section className="adm-panel" style={{marginBottom:24}}><div className="adm-head"><h2>Practice discovery · Last 30 days</h2><button onClick={() => setRetry(n => n+1)}>Refresh</button></div><p>Event counts, not unique students. Instagram, YouTube start-page and paper visits and clicks are approximate; mock starts are recorded by the server. No visitor identifiers are stored.</p>{error && <p role="alert">{error}</p>}{!data && !error && <p role="status">Loading traffic…</p>}{data && <div className="adm-table"><table><thead><tr><th>Source</th><th>Page views</th><th>Continue clicks</th><th>Mocks started</th></tr></thead><tbody>{sources.map(source => <tr key={source}><td>{source}</td><td>{count(source,'view')}</td><td>{count(source,'start_click')}</td><td>{count(source,'mock_start')}</td></tr>)}</tbody></table>{!sources.length && <p>No paper traffic recorded yet.</p>}</div>}</section>
}
