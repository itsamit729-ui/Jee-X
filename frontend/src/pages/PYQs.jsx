import { clearPaperReturn } from '../lib/paperReturn.js'
import { useEffect, useState } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { ArrowUpRight, BookOpen, Clock3, Layers3, ChevronDown } from 'lucide-react'
import AppHeader from '../components/AppHeader.jsx'
import { request } from '../lib/api.js'
import { requestFullscreen } from '../lib/fullscreen.js'
import './pyqs.css'
import { PYQ_EXAMS, pyqExam, pyqLabel, paperMarks, practiceOffset } from '../lib/pyqArchive.js'

export default function PYQs() {
  const navigate = useNavigate()
  useEffect(() => { clearPaperReturn() }, [])
  const [params, setParams] = useSearchParams()
  const exam = pyqExam(params.get('exam'))
  const [view, setView] = useState('papers')
  const [catalog, setCatalog] = useState(null)
  const [year, setYear] = useState(2026)
  const [subject, setSubject] = useState('PHY')
  const [count, setCount] = useState([5,10,20,30].includes(Number(params.get('count'))) ? Number(params.get('count')) : 10)
  const [offset, setOffset] = useState(practiceOffset(params.get('offset')))
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)
  const [retry, setRetry] = useState(0)
  useEffect(() => {
    let active = true
    setView(params.get('view') === 'practice' || exam === 'bitsat' ? 'practice' : 'papers')
    setSubject(['PHY','CHEM','MATH','ENG','LR'].includes(params.get('subject')) ? params.get('subject') : 'PHY')
    setError(''); setCatalog(null)
    request(`/api/pyqs/${exam}`).then(data => { if (active) { setCatalog(data); setYear(data.years.find(y => y.year === Number(params.get('year')))?.year || data.years.find(y => y.papers?.length || y.subjects.some(s => s.available))?.year || data.years[0]?.year || 2026) } })
      .catch(e => { if (active) setError(e.message) })
    return () => { active = false }
  }, [retry, exam])
  const subjects = catalog?.years.find(item => item.year === year)?.subjects || []
  const selected = subjects.find(item => item.code === subject)
  const papers = catalog?.years.find(item => item.year === year)?.papers || []
  const requestedShift = params.get('shift')
  const selectedPaper = requestedShift && year === Number(params.get('year')) ? papers.find(p => p.shift === requestedShift) : null
  async function start(paper = null) {
    requestFullscreen()
    setBusy(true); setError('')
    try {
      const test = await request(`/api/pyqs/${exam}/${paper ? 'papers' : 'practice'}`, {
        method: 'POST', body: paper ? { year, shift: paper.shift, acquisition_source: ['direct','google','youtube','instagram','whatsapp','telegram','teacher','other'].includes(params.get('source')) ? params.get('source') : undefined } : { year, subject_code: subject, count, offset },
      })
      const selection = new URLSearchParams({ pyq: exam, year: String(year), subject, offset: String(offset), count: String(count), view: paper ? 'papers' : 'practice' })
      if (paper) selection.set('shift', paper.shift)
      navigate(`/subject-test?${selection}`, { state: { missionTest: test } })
    } catch (e) { setError(e.message) }
    finally { setBusy(false) }
  }
  return <div className="crackjee-root"><AppHeader/><main className="pyq-shell">
    <header className="pyq-heading"><div><span className="pyq-eyebrow">THE QUESTION ARCHIVE</span><h1>The years before.<br/><span>Your next step forward.</span></h1><p>Pick your paper, find your rhythm, and learn from every attempt.</p></div><span className="pyq-heading-icon"><BookOpen size={33} strokeWidth={1.2} aria-hidden="true"/></span></header>
    <div className="pyq-exams" role="group" aria-label="Exam">{PYQ_EXAMS.map(([code, label, detail]) => <button key={code} disabled={busy} aria-pressed={exam === code} onClick={() => { setParams({ exam: code }); setSubject("PHY"); setYear(2026); setOffset(0) }}><Layers3 size={19}/><span><strong>{label}</strong><small>{detail}</small></span><ArrowUpRight size={16}/></button>)}</div>
    <section className="pyq-panel" aria-labelledby="pyq-title">
      <div className="pyq-panel-heading"><h2 id="pyq-title">{pyqLabel(exam)}</h2><span className="tag">{exam === 'jee_main' ? 'MCQ + Numerical' : 'Memory-based'}</span></div>
      <details className="pyq-source-note"><summary>About these questions & paper coverage<ChevronDown size={14}/></summary>
      {exam === "bitsat" && <><p className="muted">Recalled questions, reviewed before publication. These practice sets are not official papers or full exam simulations.</p>
      <p className="muted" style={{fontSize:12}}>Initial collection: selected 2022–2023 questions, with new worked solutions. Source: <a href="https://huggingface.co/datasets/datavorous/entrance-exam-dataset" target="_blank" rel="noreferrer">datavorous and contributors</a> · <a href="https://creativecommons.org/licenses/by/4.0/" target="_blank" rel="noreferrer">CC BY 4.0</a>. Year labels follow the source; coverage is incomplete.</p></>}
      {exam === "jee_main" && <p className="muted">All published, answer-key-ready JEE Main PYQs in the question bank, including numerical questions. Browse by year and subject, or attempt every available question for a dated shift. Coverage and original order may be incomplete. Scoring uses +4 correct, −1 incorrect and 0 skipped; historical paper patterns may differ. Worked solutions appear where available; answer keys are shown after submission.</p>}
      {exam === "mht_cet" && <p className="muted">Chapter-wise questions reconstructed by ExamSIDE, with source answer keys. These are not official papers. Worked solutions are being added; some questions currently show only the answer key.</p>}
      </details>
      {error && <div role="alert" className="alert">{error} {!catalog && <button className="btn btn-secondary" onClick={() => setRetry(v => v+1)}>Retry</button>}</div>}
      {!catalog && !error && <p role="status">Loading the archive…</p>}
      {catalog && <>
        <div className="pyq-filter-heading"><span>01</span>Choose a year</div><div className="pyq-years" role="group" aria-label="Exam year">{catalog.years.map(item => <button type="button" key={item.year} aria-pressed={year===item.year} disabled={busy} onClick={() => { setYear(item.year); setOffset(0) }}>{item.year}</button>)}</div>
        <div className="pyq-filter-heading"><span>02</span>Choose your format</div><div className="pyq-years pyq-format" role="group" aria-label="Practice format">{[['papers', 'Year & shift mocks'], ['practice', 'Subject practice']].map(([code, label]) => <button key={code} disabled={busy} aria-pressed={view === code} onClick={() => setView(code)}>{label}</button>)}</div>
        {view === 'papers' ? <>
          {selectedPaper && <div className="pyq-timing-note"><div><strong>Your selected paper: {selectedPaper.shift}</strong><p>{selectedPaper.available} available questions · Ready when you are.</p><button className="btn btn-primary" disabled={busy} onClick={() => start(selectedPaper)}>{busy ? 'Preparing…' : 'Start selected mock'}</button></div></div>}
          {requestedShift && year === Number(params.get('year')) && !selectedPaper && <p role="status">That paper is no longer available. Choose another shift below.</p>}
          <p className="muted">{papers.length ? `${papers.length} shift mocks · All available subjects · 180 minutes · Auto-submit` : 'No dated shift papers are available for this year yet. Subject practice remains available when questions have no shift metadata.'}</p>
          {papers.length > 0 && <p className="pyq-timing-note"><Clock3 size={15}/><span>{exam === 'mht_cet' ? 'Reconstructed papers may be incomplete. MHT-CET: 90 min Physics/Chemistry → 90 min Mathematics.' : exam === 'jee_main' ? '180-minute mocks include all available MCQs and numerical questions for the shift. Papers may be incomplete; original question order and historical formats may differ.' : 'Reconstructed papers may be incomplete. Original question order may differ.'}</span></p>}
          <div className="pyq-papers">{papers.map(paper => <article className="pyq-paper" key={paper.shift}>
            <div><h3>{paper.shift}</h3><span className="tag">{paper.available} questions</span></div>
            <p><strong>{paperMarks(exam, paper.subjects)} marks</strong> · {exam === 'mht_cet' ? (['PHY', 'CHEM', 'MATH'].every(code => paper.subjects.find(s => s.code === code)?.available === 50) ? '150-question reconstruction' : 'Partial paper — some questions are missing') : exam === 'jee_main' ? 'Available shift questions · Coverage may be incomplete' : 'Reconstructed paper'}</p>
            <p>{paper.subjects.map(s => `${s.name}: ${s.available}`).join(' · ')}</p>
            <button className="btn btn-primary" disabled={busy} onClick={() => start(paper)}>{busy ? 'Preparing…' : 'Start mock'}<ArrowUpRight size={17}/></button>
          </article>)}</div>
        </> : <>
        <div className="pyq-subjects" aria-label="Subject">{subjects.map(item => <button type="button" key={item.code} aria-pressed={subject===item.code} disabled={busy} onClick={() => { setSubject(item.code); setOffset(0) }}><strong>{item.name}</strong><span>{item.available ? `${item.available} questions` : 'Awaiting verified questions'}</span></button>)}</div>
        <div className="pyq-start"><label>Set length<select className="input" value={count} disabled={busy} onChange={e => { setCount(Number(e.target.value)); setOffset(0) }}>{[5,10,20,30].map(n => <option key={n} value={n}>{n} questions</option>)}</select></label><div><strong>{exam === "jee_main" ? "+4 correct · −1 incorrect · 0 skipped" : exam === "bitsat" ? "+3 correct · −1 incorrect · 0 skipped" : `+${subject === "MATH" ? 2 : 1} correct · No negative marking`}</strong><p>{selected?.available ? `${Math.max(0, Math.min(count, selected.available - offset))} questions in this set. Answers and available solutions appear after submission.` : 'This selection is not published yet. It will open when verified questions are imported.'}</p></div><button className="btn btn-primary" disabled={busy || !selected?.available || offset >= selected.available} onClick={() => start()}>{busy ? 'Preparing…' : 'Start practice'}<ArrowUpRight size={17}/></button></div>
        {Boolean(selected?.available) && <div className="pyq-set-pages"><button className="btn btn-secondary" disabled={busy || offset === 0} onClick={() => setOffset(n => Math.max(0, n - count))}>Previous set</button><p aria-live="polite">{offset < selected.available ? `Questions ${offset + 1}–${Math.min(offset + count, selected.available)} of ${selected.available}` : 'This set is no longer available. Choose the previous set or another subject.'}</p><button className="btn btn-secondary" disabled={busy || offset + count >= selected.available} onClick={() => setOffset(n => n + count)}>Next set</button></div>}
        </>}
      </>}
    </section>
  </main></div>
}
