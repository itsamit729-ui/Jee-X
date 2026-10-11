import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { ArrowUpRight, BookOpen } from 'lucide-react'
import AppHeader from '../components/AppHeader.jsx'
import { request } from '../lib/api.js'
import { requestFullscreen } from '../lib/fullscreen.js'
import './pyqs.css'

export default function PYQs() {
  const navigate = useNavigate()
  const [exam, setExam] = useState('mht_cet')
  const [view, setView] = useState('papers')
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
    request(`/api/pyqs/${exam}`).then(data => { if (active) { setCatalog(data); setYear(data.years.find(y => y.papers?.length || y.subjects.some(s => s.available))?.year || data.years[0]?.year || 2026) } })
      .catch(e => { if (active) setError(e.message) })
    return () => { active = false }
  }, [retry, exam])
  const subjects = catalog?.years.find(item => item.year === year)?.subjects || []
  const selected = subjects.find(item => item.code === subject)
  const papers = catalog?.years.find(item => item.year === year)?.papers || []
  async function start(paper = null) {
    requestFullscreen()
    setBusy(true); setError('')
    try {
      const test = await request(`/api/pyqs/${exam}/${paper ? 'papers' : 'practice'}`, {
        method: 'POST', body: paper ? { year, shift: paper.shift } : { year, subject_code: subject, count },
      })
      navigate(`/subject-test?pyq=${exam}`, { state: { missionTest: test } })
    } catch (e) { setError(e.message) }
    finally { setBusy(false) }
  }
  return <div className="crackjee-root"><AppHeader/><main className="pyq-shell">
    <header className="pyq-heading"><div><span className="pyq-eyebrow">THE QUESTION ARCHIVE</span><h1>Learn from the years before.</h1><p>Choose a year, choose a shift, and take its timed mock.</p></div><BookOpen size={36} aria-hidden="true"/></header>
    <div className="pyq-years" aria-label="Exam">{[["mht_cet", "MHT CET"], ["bitsat", "BITSAT"]].map(([code, label]) => <button key={code} disabled={busy} aria-pressed={exam === code} onClick={() => { setExam(code); setSubject("PHY"); setYear(2026) }}>{label}</button>)}</div>
    <section className="pyq-panel" aria-labelledby="pyq-title">
      <div className="pyq-panel-heading"><h2 id="pyq-title">{exam === "bitsat" ? "BITSAT" : "MHT CET"}</h2><span className="tag">Memory-based</span></div>
      {exam === "bitsat" && <><p className="muted">Recalled questions, reviewed before publication. These practice sets are not official papers or full exam simulations.</p>
      <p className="muted" style={{fontSize:12}}>Initial collection: selected 2022–2023 questions, with new worked solutions. Source: <a href="https://huggingface.co/datasets/datavorous/entrance-exam-dataset" target="_blank" rel="noreferrer">datavorous and contributors</a> · <a href="https://creativecommons.org/licenses/by/4.0/" target="_blank" rel="noreferrer">CC BY 4.0</a>. Year labels follow the source; coverage is incomplete.</p></>}
      {exam === "mht_cet" && <p className="muted">Chapter-wise questions reconstructed by ExamSIDE, with source answer keys. These are not official papers. Worked solutions are being added; some questions currently show only the answer key.</p>}
      {error && <div role="alert" className="alert">{error} {!catalog && <button className="btn btn-secondary" onClick={() => setRetry(v => v+1)}>Retry</button>}</div>}
      {!catalog && !error && <p role="status">Loading the archive…</p>}
      {catalog && <>
        <div className="pyq-years" aria-label="Exam year">{catalog.years.map(item => <button type="button" key={item.year} aria-pressed={year===item.year} disabled={busy} onClick={() => setYear(item.year)}>{item.year}</button>)}</div>
        <div className="pyq-years" aria-label="Practice format">{[['papers', 'Year & shift mocks'], ['practice', 'Subject practice']].map(([code, label]) => <button key={code} disabled={busy} aria-pressed={view === code} onClick={() => setView(code)}>{label}</button>)}</div>
        {view === 'papers' ? <>
          <p className="muted">{papers.length ? `${papers.length} shift mocks · All available subjects · 180 minutes · Auto-submit` : 'No dated shift papers are available for this year yet. Subject practice remains available when questions have no shift metadata.'}</p>
          {papers.length > 0 && <p className="muted">Reconstructed from available questions; some papers have incomplete coverage. MHT CET mocks use 90 minutes for Physics/Chemistry, followed by 90 minutes for Mathematics. Original question order may differ.</p>}
          <div className="pyq-papers">{papers.map(paper => <article className="pyq-paper" key={paper.shift}>
            <div><h3>{paper.shift}</h3><span className="tag">{paper.available} questions</span></div>
            <p><strong>{paper.subjects.reduce((total, s) => total + s.available * (exam === 'bitsat' ? 3 : s.code === 'MATH' ? 2 : 1), 0)} marks</strong> · {exam === 'mht_cet' ? (['PHY', 'CHEM', 'MATH'].every(code => paper.subjects.find(s => s.code === code)?.available === 50) ? '150-question reconstruction' : 'Partial paper — some questions are missing') : 'Reconstructed paper'}</p>
            <p>{paper.subjects.map(s => `${s.name}: ${s.available}`).join(' · ')}</p>
            <button className="btn btn-primary" disabled={busy} onClick={() => start(paper)}>{busy ? 'Preparing…' : 'Start mock'}<ArrowUpRight size={17}/></button>
          </article>)}</div>
        </> : <>
        <div className="pyq-subjects" aria-label="Subject">{subjects.map(item => <button type="button" key={item.code} aria-pressed={subject===item.code} disabled={busy} onClick={() => setSubject(item.code)}><strong>{item.name}</strong><span>{item.available ? `${item.available} questions` : 'Awaiting verified questions'}</span></button>)}</div>
        <div className="pyq-start"><label>Set length<select className="input" value={count} disabled={busy} onChange={e => setCount(Number(e.target.value))}>{[5,10,20,30].map(n => <option key={n} value={n}>{n} questions</option>)}</select></label><div><strong>{exam === "bitsat" ? "+3 correct · −1 incorrect · 0 skipped" : `+${subject === "MATH" ? 2 : 1} correct · No negative marking`}</strong><p>{selected?.available ? `${Math.min(count, selected.available)} questions in this set. Answers and available solutions appear after submission.` : 'This selection is not published yet. It will open when verified questions are imported.'}</p></div><button className="btn btn-primary" disabled={busy || !selected?.available} onClick={() => start()}>{busy ? 'Preparing…' : 'Start practice'}<ArrowUpRight size={17}/></button></div>
        </>}
      </>}
    </section>
  </main></div>
}
