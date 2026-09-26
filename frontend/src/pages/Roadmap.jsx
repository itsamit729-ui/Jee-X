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
    <p>{scenario.basis === 'college_cutoff' ? 'Reference for your comparable college choices, based on historical closing ranks.' : scenario.basis === 'entered_crl' ? 'A rank scenario.' : scenario.reference_year ? `Historical marks model: ${scenario.reference_year} · Rank reference: ${scenario.rank_reference_year}.` : 'Complete a baseline or choose a goal with available reference data. Estimates appear only within the available reference range.'}</p>
    {scenario.percentile_low != null && <p>Estimated percentile {scenario.percentile_low.toFixed(2)}–{scenario.percentile_high.toFixed(2)}</p>}
    {scenario.colleges.length ? <ul className="roadmap-colleges">{scenario.colleges.map((college, i) => <li key={`${college.institute}-${college.program}-${i}`}><strong>{college.institute}</strong><span>{college.program}</span><small>{college.reference_year} · Round {college.reference_round} · {college.quota} · {college.seat_type} · {college.gender_pool}</small><small>Closing rank {number(college.closing_rank)} · {college.meets_conservative_estimate ? 'Within the full estimated range' : 'Only overlaps the optimistic estimate'}</small></li>)}</ul> : <div className="roadmap-empty">{scenario.rank_low == null ? 'No college comparison yet.' : 'No matching cutoffs in our current All India dataset. This does not mean you have no admission options.'}</div>}
  </article>
}

function CollegePicker({ draft, setDraft }) {
  const [query, setQuery] = useState('')
  const [options, setOptions] = useState([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  useEffect(() => {
    let active = true
    setLoading(true); setError('')
    const timer = setTimeout(() => {
      request(`/api/roadmap/colleges?q=${encodeURIComponent(query)}`).then(rows => { if (active) setOptions(rows) })
        .catch(e => { if (active) setError(e.message) }).finally(() => { if (active) setLoading(false) })
    }, 250)
    return () => { active = false; clearTimeout(timer) }
  }, [query])
  const choices = draft.choices || []
  const choose = item => setDraft(current => current.college_choices.length >= 3 || current.college_choices.includes(item.id) ? current : ({ ...current, choices: [...(current.choices || []), item], college_choices: [...current.college_choices, item.id] }))
  const remove = id => setDraft(current => ({ ...current, choices: current.choices.filter(c => c.id !== id), college_choices: current.college_choices.filter(x => x !== id) }))
  return <div className="roadmap-college-picker"><p>Choose up to three college and branch combinations. We’ll work out the available historical benchmarks.</p>
    <ol className="roadmap-choices">{choices.map((c, i) => <li key={c.id}><span className="roadmap-step">{i + 1}</span><div><strong>{c.institute}</strong><small>{c.program}</small></div><button type="button" className="btn btn-quiet" onClick={() => remove(c.id)} aria-label={`Remove ${c.institute}, ${c.program}`}>Remove</button></li>)}</ol>
    {choices.length < 3 && <><label className="roadmap-search-label">Find a college or branch<input type="search" value={query} placeholder="Search institute name or branch" onChange={e => setQuery(e.target.value)}/></label>
    <div className="roadmap-search-results" aria-label="College and branch search results">{loading ? <p role="status">Finding choices…</p> : options.filter(o => !draft.college_choices.includes(o.id)).map(o => <button key={o.id} type="button" onClick={() => choose(o)}><span><strong>{o.institute}</strong><small>{o.program}</small></span><span aria-hidden="true">+</span></button>)}{!loading && options.length === 0 && <p>No matching programs in our catalog yet. Try another name, or use a marks goal.</p>}</div></>}
    {choices.length === 3 && <p role="status">All three choices added. Remove one to change it.</p>}{error && <p role="alert">{error}</p>}
  </div>
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
        goal_type: draft.goal_type,
        target_marks: draft.goal_type === 'marks' ? Number(draft.target_marks) : null,
        college_choices: draft.goal_type === 'colleges' ? draft.college_choices : [],
      } })
      setData(value); setDraft(value.settings); setEditing(false); setNotice('Your next seven days are ready. Previous checkpoints are saved below.')
    } catch (e) { setError(e.message) }
    finally { setBusy(false) }
  }
  const field = (name, value) => setDraft(current => ({ ...current, [name]: value }))
  const tasks = data?.plan.tasks || []
  const next = tasks.find(task => !task.progress.met) || tasks[0]
  const completed = tasks.filter(task => task.progress.met).length
  const gap = data?.baseline.score == null || data?.settings.target_marks == null ? null : Math.max(0, data.settings.target_marks - data.baseline.score)
  const days = data?.settings.exam_date ? Math.max(0, Math.ceil((new Date(`${data.settings.exam_date}T23:59:59+05:30`) - Date.now()) / 86400000)) : null

  return <div className="crackjee-root"><AppHeader/><main className="wrap roadmap-page">
    <header className="roadmap-heading"><div><span className="roadmap-kicker">YOUR ROADMAP</span><h1>A little clearer.<br/><em>A step closer.</em></h1><p>Your recent work, turned into a plan for what comes next.</p></div>{data && <button className="btn btn-secondary" onClick={() => { setDraft(data.settings); setEditing(!editing) }} aria-expanded={editing}><SlidersHorizontal size={16}/> {editing ? 'Close goals' : 'Adjust my goals'}</button>}</header>
    {error && <div className="alert" role="alert">{error} <button className="btn btn-secondary btn-sm" onClick={() => setVersion(v => v + 1)}>Retry loading</button></div>}
    {notice && <p className="roadmap-notice" role="status"><Check size={16}/>{notice}</p>}
    {!data && !error && <div className="roadmap-loading" role="status"><span className="spin"/> Reading your recent practice and building your next steps…</div>}
    {data && <>
      {(editing || !data.saved) && <form className="roadmap-goals" onSubmit={save}><div className="roadmap-section-heading"><div><span className="roadmap-kicker">MAKE IT YOURS</span><h2>{data.saved ? 'A plan that fits your week' : 'Start with a goal you care about'}</h2></div><Flag size={22}/></div>
        <div className="roadmap-goal-switch" role="group" aria-label="Choose your goal type">
          <button type="button" aria-pressed={draft.goal_type === 'marks'} onClick={() => setDraft(d => ({ ...d, goal_type: 'marks', target_marks: d.target_marks || 150 }))}><Target size={20}/><strong>I have a marks target</strong><span>Choose the score you want to work towards.</span></button>
          <button type="button" aria-pressed={draft.goal_type === 'colleges'} onClick={() => setDraft(d => ({ ...d, goal_type: 'colleges' }))}><Flag size={20}/><strong>I have colleges in mind</strong><span>Add up to three college and branch choices.</span></button>
        </div>
        {draft.goal_type === 'marks' ? <div className="roadmap-fields"><label>Target marks / 300<input required type="number" min="1" max="300" value={draft.target_marks ?? ''} onChange={e => field('target_marks', e.target.value)}/></label></div> : <CollegePicker draft={draft} setDraft={setDraft}/>}
        <p className="roadmap-help">We handle the schedule, suggested pace and assessment checkpoints using your profile and practice history.</p>
        <div className="roadmap-form-footer"><p>Saving starts a new seven-day plan and archives current checkpoints.</p><button className="btn btn-primary" disabled={busy || (draft.goal_type === 'colleges' && !draft.college_choices.length)}>{busy ? 'Building your plan…' : data.saved ? 'Save goals & rebuild plan' : 'Create my roadmap'}<ArrowRight size={16}/></button></div>
      </form>}
      <section className="roadmap-position" aria-label="Current position and goal"><article><span className="roadmap-kicker">WHERE YOU STAND</span><div className="roadmap-number">{data.baseline.score == null ? 'Let’s find out' : number(data.baseline.score)}{data.baseline.score != null && <small>/ 300</small>}</div><p>{data.baseline.count ? `${data.baseline.count} recent assessment${data.baseline.count === 1 ? '' : 's'} · median score` : 'Topic practice shapes your plan. A balanced assessment establishes your exam baseline.'}</p><Link to="/recommendations?assessment=1">{data.baseline.count ? 'Take another checkpoint' : 'Take a baseline assessment'} <ArrowUpRight size={16}/></Link></article><article><span className="roadmap-kicker">WHERE YOU WANT TO GO</span>{data.settings.goal_type === 'marks' ? <><div className="roadmap-number">{data.settings.target_marks}<small>/ 300</small></div><p>{gap == null ? 'Your chosen target. Your baseline will show the gap.' : gap > 0 ? `${number(gap)} marks from your current baseline. Progress must be demonstrated in fresh assessments.` : 'You have reached this marks target. Work on consistency or choose a new goal.'}</p></> : <><div className="roadmap-number">{data.settings.choices.length}<small>college & branch choices</small></div><p>{data.settings.target_crl ? `Historical reference: CRL ${number(data.settings.target_crl)} for the most demanding comparable choice. This is a past cutoff, not a guaranteed admission target.` : 'Your choices are saved. We need applicable cutoff data before calculating a rank benchmark.'}</p></>}<span className="roadmap-tag">{days == null ? `${data.settings.target_year} target year` : `${days} days to the configured exam date`}</span></article></section>
      <div className="roadmap-auto-plan"><span className="roadmap-kicker">PLANNED FOR YOU</span><strong>{data.settings.weekly_hours} suggested hours / week</strong><p>{data.settings.pace_basis} {data.settings.timeline_note}</p></div>
      {data.settings.goal_type === 'colleges' && <ol className="roadmap-choices roadmap-selected-goals">{data.settings.choices.map((c, i) => <li key={c.id}><span className="roadmap-step">{i + 1}</span><div><strong>{c.institute}</strong><span>{c.program}</span><small>{c.rank ? `${c.year} · Round ${c.round} · AI / OPEN / Gender-Neutral · Closing CRL ${number(c.rank)}` : 'No applicable All India OPEN cutoff available. State/category eligibility or a different exam route may be required.'}</small></div></li>)}</ol>}

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
