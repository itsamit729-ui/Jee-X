import { useEffect, useState } from 'react'
import { request } from '../lib/api.js'

export default function AdminPlanInterests({ token }) {
  const [data, setData] = useState(null)
  const [error, setError] = useState('')
  const [offset, setOffset] = useState(0)
  const [retry, setRetry] = useState(0)
  const [loading, setLoading] = useState(true)
  useEffect(() => {
    let active = true
    setLoading(true); setError('')
    request(`/api/admin/plan-interests?offset=${offset}`, { token })
      .then(value => { if (active) setData(value) })
      .catch(e => { if (active) setError(e.message) })
      .finally(() => { if (active) setLoading(false) })
    return () => { active = false }
  }, [token, offset, retry])
  return <section className="adm-panel" style={{ marginBottom: 20 }}><div className="adm-head"><div><p className="adm-kicker">Launch demand · Not revenue</p><h2>Plan interest {data ? `(${data.total})` : ''}</h2></div><button className="btn btn-secondary btn-sm" disabled={loading} onClick={() => setRetry(n => n + 1)}>Refresh</button></div>
    {error && <p role="alert">{error}</p>}{loading ? <p role="status">Loading requests…</p> : data && <><div className="adm-table"><table><thead><tr><th>Email</th><th>Preference</th><th>Proposed price</th><th>Updated</th></tr></thead><tbody>{data.items.map(item => <tr key={item.email}><td>{item.email}</td><td>{item.plan.replaceAll('_', ' ')}</td><td>₹{item.price_inr} / {item.period_months} month(s)</td><td>{new Date(item.updated_at).toLocaleDateString('en-IN')}</td></tr>)}</tbody></table></div>{!data.items.length && <p>No requests yet.</p>}<div style={{ display: 'flex', gap: 12, marginTop: 14 }}><button className="btn btn-secondary btn-sm" disabled={offset === 0} onClick={() => setOffset(n => Math.max(0, n - 50))}>Previous</button><button className="btn btn-secondary btn-sm" disabled={offset + 50 >= data.total} onClick={() => setOffset(n => n + 50)}>Next</button></div></>}
  </section>
}
