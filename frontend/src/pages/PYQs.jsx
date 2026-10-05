import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { ArrowUpRight, BookOpen } from 'lucide-react'
import AppHeader from '../components/AppHeader.jsx'
import { request } from '../lib/api.js'
import { requestFullscreen } from '../lib/fullscreen.js'
import './pyqs.css'

export default function PYQs() {
  const navigate = useNavigate()
  const [catalog, setCatalog] = useState(null)
  const [year, setYear] = useState(2026)
  const [subject, setSubject] = useState('PHY')
  const [count, setCount] = useState(10)
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)
  const [retry, setRetry] = useState(0)
  useEffect(() => {
    let active = true
    setError(''); setCatalog(null)
    request('/api/pyqs/bitsat').then(data => { if (active) setCatalog(data) })
      .catch(e => { if (active) setError(e.message) })
    return () => { active = false }
  }, [retry])
  const subjects = catalog?.years.find(item => item.year === year)?.subjects || []
  const selected = subjects.find(item => item.code === subject)
  async function start() {
    requestFullscreen()
    setBusy(true); setError('')
    try {
      const test = await request('/api/pyqs/bitsat/practice', {
        method: 'POST', body: { year, subject_code: subject, count },
      })
      navigate('/subject-test?pyq=bitsat', { state: { missionTest: test } })
    } catch (e) { setError(e.message) }
    finally { setBusy(false) }
  }
  return <div className="crackjee-root"><AppHeader/><main className="pyq-shell">
    <header className="pyq-heading"><div><span className="pyq-eyebrow">THE QUESTION ARCHIVE</span><h1>Learn from the years before.</h1><p>Pick a year. Choose your subject. Work through one focused set.</p></div><BookOpen size={36} aria-hidden="true"/></header>
    <section className="pyq-panel" aria-labelledby="pyq-title">
      <div className="pyq-panel-heading"><h2 id="pyq-title">BITSAT</h2><span className="tag">Memory-based</span></div>
      <p className="muted">Recalled questions, reviewed before publication. These practice sets are not official papers or full exam simulations.</p>
      {error && <div role="alert" className="alert">{error} {!catalog && <button className="btn btn-secondary" onClick={() => setRetry(v => v+1)}>Retry</button>}</div>}
      {!catalog && !error && <p role="status">Loading the archive…</p>}
      {catalog && <>
        <div className="pyq-years" aria-label="Exam year">{catalog.years.map(item => <button type="button" key={item.year} aria-pressed={year===item.year} disabled={busy} onClick={() => setYear(item.year)}>{item.year}</button>)}</div>
        <div className="pyq-subjects" aria-label="Subject">{subjects.map(item => <button type="button" key={item.code} aria-pressed={subject===item.code} disabled={busy} onClick={() => setSubject(item.code)}><strong>{item.name}</strong><span>{item.available ? 'Ready to practise' : 'Awaiting verified questions'}</span></button>)}</div>
        <div className="pyq-start"><label>Set length<select className="input" value={count} disabled={busy} onChange={e => setCount(Number(e.target.value))}>{[5,10,20,30].map(n => <option key={n} value={n}>{n} questions</option>)}</select></label><div><strong>+3 correct · −1 incorrect · 0 skipped</strong><p>{selected?.available ? `${Math.min(count, selected.available)} questions in this set. Solutions appear after submission.` : 'This selection is not published yet. It will open when verified questions are imported.'}</p></div><button className="btn btn-primary" disabled={busy || !selected?.available} onClick={start}>{busy ? 'Preparing…' : 'Start practice'}<ArrowUpRight size={17}/></button></div>
      </>}
    </section>
  </main></div>
}
