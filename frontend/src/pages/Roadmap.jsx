import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { ArrowUpRight, ArrowRight, Check, Clock3, Flag, SlidersHorizontal, RefreshCw, Target } from 'lucide-react'
import AppHeader from '../components/AppHeader.jsx'
import { request } from '../lib/api.js'
import './roadmap.css'

const SUBJECTS = { PHY: 'Physics', CHEM: 'Chemistry', MATH: 'Mathematics' }
const number = value => value == null ? '—' : Number(value).toLocaleString('en-IN')
const date = value => new Date(value.endsWith('Z') ? value : `${value}Z`).toLocaleDateString('en-IN', { day: 'numeric', month: 'short' })
const practiceLink = task => `/subject-test?subject=${task.subject}${task.chapter_id ? `&chapter=${task.chapter_id}` : ''}`

function Outlook({ scenario, label, target }) {
  return <article className="roadmap-outlook"><span className="roadmap-kicker">{label}</span>
    <h3>{scenario.rank_low == null ? 'More evidence needed' : `CRL ${number(scenario.rank_low)}${scenario.rank_high !== scenario.rank_low ? `–${number(scenario.rank_high)}` : ''}`}</h3>
    <p>{scenario.basis === 'entered_crl' ? (target ? 'Your chosen rank scenario.' : 'The CRL you entered; not independently verified.') : scenario.reference_year ? `Historical marks model: ${scenario.reference_year} · Rank reference: ${scenario.rank_reference_year}.` : 'Add a CRL or complete a baseline. Estimates appear only within the available reference range.'}</p>
    {scenario.percentile_low != null && <p>Estimated percentile {scenario.percentile_low.toFixed(2)}–{scenario.percentile_high.toFixed(2)}</p>}
    {scenario.colleges.length ? <ul className="roadmap-colleges">{scenario.colleges.map((college, i) => <li key={`${college.institute}-${college.program}-${i}`}><strong>{college.institute}</strong><span>{college.program}</span><small>{college.reference_year} · Round {college.reference_round} · {college.quota} · {college.seat_type} · {college.gender_pool}</small><small>Closing rank {number(college.closing_rank)} · {college.meets_conservative_estimate ? 'Within the full estimated range' : 'Only overlaps the optimistic estimate'}</small></li>)}</ul> : <div className="roadmap-empty">{scenario.rank_low == null ? 'No college comparison yet.' : 'No matching cutoffs in our current All India dataset. This does not mean you have no admission options.'}</div>}
  </article>
}

export default function Roadmap() {
  const [data, setData] = useState(null)
  const [draft, setDraft] = useState(null)
  const [editing, setEditing] = useState(false)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const [notice, setNotice] = useState('')
  const [version, setVersion] = useState(0)
  useEffect(() => {
    let active = true
    setError('')
    request('/api/roadmap', version ? { cache: false } : {}).then(value => {
      if (active) { setData(value); setDraft(value.settings) }
    }).catch(e => { if (active) setError(e.message) })
    return () => { active = false }
  }, [version])
  async function save(event) {
    event?.preventDefault()
    setBusy(true); setError(''); setNotice('')
    try {
      const value = await request('/api/roadmap', { method: 'PUT', body: {
        ...draft, exam_date: draft.exam_date || null,
        weekly_hours: Number(draft.weekly_hours), target_marks: Number(draft.target_marks),
        current_crl: draft.current_crl ? Number(draft.current_crl) : null,
        target_crl: draft.target_crl ? Number(draft.target_crl) : null,
      } })
      setData(value); setDraft(value.settings); setEditing(false); setNotice('Your next seven days are ready. Previous checkpoints are saved below.')
    } catch (e) { setError(e.message) }
    finally { setBusy(false) }
  }
  const field = (name, value) => setDraft(current => ({ ...current, [name]: value }))
  const tasks = data?.plan.tasks || []
  const next = tasks.find(task => !task.progress.met) || tasks[0]
  const completed = tasks.filter(task => task.progress.met).length
  const gap = data?.baseline.score == null ? null : Math.max(0, data.settings.target_marks - data.baseline.score)
  const days = data?.settings.exam_date ? Math.max(0, Math.ceil((new Date(`${data.settings.exam_date}T23:59:59+05:30`) - Date.now()) / 86400000)) : null

  return <div className="crackjee-root"><AppHeader/><main className="wrap roadmap-page">
    <header className="roadmap-heading"><div><span className="roadmap-kicker">YOUR ROADMAP</span><h1>A little clearer.<br/><em>A step closer.</em></h1><p>Your recent work, turned into a plan for what comes next.</p></div>{data && <button className="btn btn-secondary" onClick={() => { setDraft(data.settings); setEditing(!editing) }} aria-expanded={editing}><SlidersHorizontal size={16}/> {editing ? 'Close goals' : 'Adjust my goals'}</button>}</header>
    {error && <div className="alert" role="alert">{error} <button className="btn btn-secondary btn-sm" onClick={() => setVersion(v => v + 1)}>Retry loading</button></div>}
    {notice && <p className="roadmap-notice" role="status"><Check size={16}/>{notice}</p>}
    {!data && !error && <div className="roadmap-loading" role="status"><span className="spin"/> Reading your recent practice and building your next steps…</div>}
    {data && <>
      {(editing || !data.saved) && <form className="roadmap-goals" onSubmit={save}><div className="roadmap-section-heading"><div><span className="roadmap-kicker">MAKE IT YOURS</span><h2>{data.saved ? 'A plan that fits your week' : 'Start with a goal you care about'}</h2></div><Flag size={22}/></div>
        <div className="roadmap-fields">
          <label>Study hours per week<input required type="number" min="2" max="60" value={draft.weekly_hours} onChange={e => field('weekly_hours', e.target.value)}/></label>
          <label>Target marks / 300<input required type="number" min="1" max="300" value={draft.target_marks} onChange={e => field('target_marks', e.target.value)}/></label>
          <label>Exam date <small>optional</small><input type="date" value={draft.exam_date || ''} onChange={e => field('exam_date', e.target.value)}/></label>
          <label>College or branch goal <small>optional</small><input maxLength="120" placeholder="e.g. Mechanical at NIT Trichy" value={draft.target_college} onChange={e => field('target_college', e.target.value)}/></label>
        </div>
        <details className="roadmap-rank-inputs"><summary>Have a JEE Main CRL, or a target rank?</summary><p>Enter Common Rank List ranks only. These override the marks-based college scenarios; category ranks are not supported here.</p><div className="roadmap-fields"><label>Current CRL <small>optional, self-reported</small><input type="number" min="1" max="3000000" value={draft.current_crl || ''} onChange={e => field('current_crl', e.target.value)}/></label><label>Target CRL <small>optional, what-if scenario</small><input type="number" min="1" max="3000000" value={draft.target_crl || ''} onChange={e => field('target_crl', e.target.value)}/></label></div></details>
        <div className="roadmap-form-footer"><p>Saving starts a new seven-day plan and archives current checkpoints.</p><button className="btn btn-primary" disabled={busy}>{busy ? 'Building your plan…' : data.saved ? 'Save goals & rebuild plan' : 'Create my roadmap'}<ArrowRight size={16}/></button></div>
      </form>}
      <section className="roadmap-position" aria-label="Current position and goal"><article><span className="roadmap-kicker">WHERE YOU STAND</span><div className="roadmap-number">{data.baseline.score == null ? 'Let’s find out' : number(data.baseline.score)}{data.baseline.score != null && <small>/ 300</small>}</div><p>{data.baseline.count ? `${data.baseline.count} recent assessment${data.baseline.count === 1 ? '' : 's'} · median score` : 'Topic practice shapes your plan. A balanced assessment establishes your exam baseline.'}</p><Link to="/recommendations?assessment=1">{data.baseline.count ? 'Take another checkpoint' : 'Take a baseline assessment'} <ArrowUpRight size={16}/></Link></article><article><span className="roadmap-kicker">WHERE YOU WANT TO GO</span><div className="roadmap-number">{data.settings.target_marks}<small>/ 300</small></div><p>{gap == null ? 'A chosen target. Your baseline will show the gap.' : gap > 0 ? `${number(gap)} marks from your current baseline. Progress must be demonstrated in fresh assessments.` : 'You have reached this marks target in your recent baseline. Work on consistency or set a new goal.'}</p><span className="roadmap-tag">{days == null ? `${data.settings.weekly_hours} hours available each week` : `${days} days to your chosen exam date`}</span></article></section>
      {data.settings.target_college && <p className="roadmap-goal-line"><Flag size={16}/> Working towards <strong>{data.settings.target_college}</strong><span>Your personal goal, not an admission prediction.</span></p>}
      <div className="roadmap-workspace"><section>
        <div className="roadmap-section-heading"><div><span className="roadmap-kicker">{data.saved ? `${date(data.plan.created_at)} — ${date(data.plan.review_at)}` : 'PREVIEW YOUR FIRST WEEK'}</span><h2>Your next seven days</h2></div><span className="roadmap-tag">{completed}/{tasks.length} checkpoints</span></div>
        {data.saved && next && <div className="roadmap-next"><div><span className="roadmap-kicker">{completed === tasks.length ? 'KEEP THE MOMENTUM' : 'START HERE'}</span><h3>{next.title}</h3><p>{completed === tasks.length ? 'Your chapter checkpoints are met. Take a balanced assessment to check exam readiness.' : next.goal}</p></div><Link className="btn btn-primary" to={completed === tasks.length ? '/recommendations?assessment=1' : practiceLink(next)}>{completed === tasks.length ? 'Assess progress' : 'Start a 15-min session'}<ArrowUpRight size={16}/></Link></div>}
        <ol className="roadmap-timeline">{tasks.map((task, i) => <li key={`${task.subject}-${task.chapter_id}`}><span className={`roadmap-step ${task.progress.met ? 'done' : ''}`}>{task.progress.met ? <Check size={17}/> : `0${i + 1}`}</span><article><div className="roadmap-task-top"><span className="roadmap-kicker">{SUBJECTS[task.subject]}</span><span><Clock3 size={13}/> {task.minutes} min this week</span></div><h3>{task.title}</h3><p>{task.reason}</p><div className="roadmap-task-sequence"><span>Review concepts · {task.review_minutes} min</span><ArrowRight size={12}/><span>Practice · 15 min</span><ArrowRight size={12}/><span>Fresh check · 15 min</span></div><p className="roadmap-checkpoint">{task.checkpoint}</p><div className="roadmap-task-footer"><span>{task.progress.met ? 'Checkpoint met' : `${task.progress.answered}/5 fresh answers · ${task.progress.correct} correct`}</span><Link to={practiceLink(task)}>Practise <ArrowUpRight size={15}/></Link></div></article></li>)}</ol>
        <p className="roadmap-help">Fresh answers count from the start of your saved plan. Repeating a familiar question does not complete a checkpoint. Use any remaining study time for revision and a full assessment when you have three uninterrupted hours.</p>
        {data.saved && <button className="btn btn-secondary" disabled={busy} onClick={save}><RefreshCw size={15}/>{busy ? 'Updating…' : 'Review progress & plan next week'}</button>}
      </section><aside className="roadmap-sidebar"><section className="roadmap-panel"><Target size={21}/><h2>Make progress visible</h2><p>Learn the concept. Try it without help. Come back to a fresh question.</p>{data.subjects.length ? data.subjects.map(s => <div className="roadmap-subject" key={s.code}><div><strong>{SUBJECTS[s.code]}</strong><span>{s.accuracy}%</span></div><progress value={s.accuracy} max="100" aria-label={`${SUBJECTS[s.code]} practice accuracy`}/><small>{s.answered} distinct answered questions in recent history</small></div>) : <p className="roadmap-empty">Your subject picture will appear after your first submitted practice session.</p>}<small>Practice accuracy is not a JEE percentile. Recent distinct answers guide these priorities.</small></section>
        <section className="roadmap-panel"><span className="roadmap-kicker">ASSESSMENT HISTORY</span><h2>Your own benchmark</h2>{data.baseline.recent.length ? <ul className="roadmap-history">{data.baseline.recent.map(item => <li key={item.attempt_id}><span>{date(item.date)}</span><strong>{item.score} / 300</strong></li>)}</ul> : <p>No balanced assessments yet. Your first one is a starting point, not a judgement.</p>}<p className="roadmap-help">{data.baseline.note}</p></section>
      </aside></div>
      <section className="roadmap-college-section"><div className="roadmap-section-heading"><div><span className="roadmap-kicker">THE BIGGER PICTURE</span><h2>What could open up?</h2></div></div><p className="roadmap-intro-copy">Compare your current evidence with a chosen target. Following a plan does not guarantee marks, rank or admission.</p><div className="roadmap-outlook-grid"><Outlook scenario={data.current} label="CURRENT EVIDENCE"/><Outlook scenario={data.target} label="IF YOU REACH YOUR TARGET" target/></div><p className="roadmap-help">{data.college_note}</p></section>
      {data.checkpoints.length > 0 && <details className="roadmap-archive"><summary>Previous plan reviews ({data.checkpoints.length})</summary>{[...data.checkpoints].reverse().map((checkpoint, i) => <div key={i}><strong>{date(checkpoint.date)}</strong><p>{checkpoint.tasks.map(t => `${t.title}: ${t.met ? 'checkpoint met' : `${t.answered}/5 fresh answers, ${t.correct} correct`}`).join(' · ')}</p></div>)}</details>}
    </>}
  </main></div>
}
