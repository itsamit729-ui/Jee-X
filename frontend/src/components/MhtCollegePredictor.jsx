import { useEffect, useState } from 'react'
import { request } from '../lib/api.js'

export default function MhtCollegePredictor({ attemptId }) {
  const [percentile, setPercentile] = useState('')
  const [category, setCategory] = useState('OPEN')
  const [quota, setQuota] = useState('S')
  const [pool, setPool] = useState('G')
  const [search, setSearch] = useState('')
  const [data, setData] = useState(null)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const [submitted, setSubmitted] = useState(null)
  useEffect(() => {
    let active = true
    request(`/api/pyqs/mht_cet/attempts/${attemptId}/colleges`).then(value => { if (active) setData(value) }).catch(e => { if (active) setError(e.message) })
    return () => { active = false }
  }, [attemptId])
  async function predict(event, offset = 0) {
    event?.preventDefault()
    const filters = offset ? submitted : { percentile, category, quota, pool, search }
    if (!filters || filters.percentile === '') return
    setBusy(true); setError('')
    try {
      const result = await request(`/api/pyqs/mht_cet/attempts/${attemptId}/colleges?${new URLSearchParams({ ...filters, offset })}`)
      setData(result); setSubmitted(filters)
    } catch (e) { setError(e.message) }
    finally { setBusy(false) }
  }
  return <section className="panel" aria-labelledby="cet-colleges-title">
    <h2 className="panel-title" id="cet-colleges-title">MHT CET college predictor</h2>
    {data && <p>Your mock: <strong>{data.score} / {data.maximum}</strong> · {data.question_count} questions</p>}
    <p className="muted">Explore colleges using an actual or assumed MHT CET percentile. Your mock marks are not converted into an official percentile. This comparison uses 2025 CAP Round I cutoffs.</p>
    <form onSubmit={predict} style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit,minmax(170px,1fr))', gap: 14 }}>
      <label>Actual / assumed percentile<input className="input" type="number" min="0" max="100" step="any" required value={percentile} onChange={e => setPercentile(e.target.value)} placeholder="e.g. 97.5"/></label>
      <label>Seat category<select className="input" value={category} onChange={e => setCategory(e.target.value)}>{['OPEN','SC','ST','VJ','NT1','NT2','NT3','OBC','SEBC'].map(c => <option key={c}>{c}</option>)}</select></label>
      <label>University quota<select className="input" value={quota} onChange={e => setQuota(e.target.value)}><option value="S">State level</option><option value="H">Home university</option><option value="O">Other than home university</option></select></label>
      <label>Seat pool<select className="input" value={pool} onChange={e => setPool(e.target.value)}><option value="G">General (all genders)</option><option value="L">Ladies</option></select></label>
      <label>College or branch<input className="input" value={search} onChange={e => setSearch(e.target.value)} placeholder="Computer, Pune…" maxLength={100}/></label>
      <button className="btn btn-primary" disabled={busy}>{busy ? 'Checking…' : 'Find college matches'}</button>
    </form>
    {error && <p className="alert" role="alert">{error}</p>}
    {data?.percentile != null && <div aria-live="polite"><p><strong>{data.total_matches} historical matches</strong> at {data.percentile} percentile · Seat code {data.seat_code}</p>
      {data.colleges.map(c => <article key={c.choice_code} style={{ padding: '16px 0', borderTop: '1px solid var(--line)' }}><strong>{c.institute}</strong><p>{c.program} · {c.choice_code}</p><small>Closing percentile: {c.closing_percentile.toFixed(5)} · {c.seat_code} · 2025 Round I · Source page {c.source_page}</small></article>)}
      {!data.total_matches && <p>No matching rows for these filters. Try another eligible seat pool or a different search.</p>}
      <div style={{ display: 'flex', gap: 12 }}>{data.next_offset != null && <button className="btn btn-secondary" disabled={busy} onClick={() => predict(null, data.next_offset)}>Next matches</button>}<button className="btn btn-quiet" disabled={busy} onClick={() => predict(null)}>First page</button></div>
    </div>}
    <p className="muted" style={{ fontSize: 12, marginTop: 18 }}>{data?.disclaimer || 'Historical cutoff comparison, not an admission guarantee.'} <a href={data?.source || 'https://fe2025.mahacet.org/'} target="_blank" rel="noreferrer">Official cutoff source</a></p>
  </section>
}
