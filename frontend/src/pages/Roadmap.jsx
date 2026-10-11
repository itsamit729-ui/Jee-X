import { useEffect, useRef, useState } from 'react'
import { useLocation } from 'react-router-dom'
import { ArrowRight, Check, ChevronDown, Clock3, Flag, SlidersHorizontal, Target } from 'lucide-react'
import AppHeader from '../components/AppHeader.jsx'
import CollegeInfo from '../components/CollegeInfo.jsx'
import PlanWorkspace from '../components/PlanWorkspace.jsx'
import PlanGoalEditor from '../components/PlanGoalEditor.jsx'
import { request } from '../lib/api.js'
import { goalPayload, planGoal } from '../lib/planPresentation.js'
import './roadmap.css'
import './my-plan.css'

const number = value => value == null ? '—' : Number(value).toLocaleString('en-IN')
const date = value => new Date(value.endsWith('Z') ? value : `${value}Z`).toLocaleDateString('en-IN', { day: 'numeric', month: 'short' })

function CollegeReferences({ data, onEdit }) {
  return <>{data.settings.goal_type === 'colleges' && <details className="mp-disclosure"><summary>Your chosen colleges & branch benchmarks<ChevronDown size={17}/></summary><div className="mp-cutoff-grid">{data.settings.choices.map(choice => <article key={choice.id}><h4>{choice.institute}<CollegeInfo institute={choice.institute} program={choice.program}/></h4><p>{choice.program}</p>{choice.rank ? <><strong>{choice.rank_list} closing rank {number(choice.rank)}</strong><small>{choice.year} · Round {choice.round} · {choice.quota} · {choice.seat_type} · {choice.gender_pool}</small></> : <p>No applicable cutoff resolved. Add your state of eligibility, or check whether this program requires a different exam route.</p>}</article>)}</div></details>}
    <details className="mp-disclosure" id="college-reference-details"><summary>Explore historical NIT cutoffs<ChevronDown size={17}/></summary>
    <div className="mp-reference-heading"><h3>{data.settings.admission.category}{data.settings.admission.pwd ? ' / PwD' : ''} seat comparisons</h3><button type="button" className="mp-text-action" onClick={onEdit}>Change category or state<ArrowRight size={15}/></button></div>
    <p>{data.settings.admission.state ? `Quota filtered for ${data.settings.admission.state}.` : 'Add your Class XII state of eligibility to resolve NIT quotas. These examples are not yet eligibility matches.'} Compare reserved-category cutoffs to the corresponding category rank, never to CRL. Historical cutoffs do not guarantee admission.</p>
    <div className="mp-cutoff-grid">{data.cutoff_preview.map((college, index) => <article key={index}><span className="mp-eyebrow">{college.quota} · {college.seat_type}</span><h4>{college.institute}<CollegeInfo institute={college.institute} program={college.program}/></h4><p>{college.program}</p><strong>{college.rank_list} closing rank {number(college.closing_rank)}</strong><small>{college.reference_year} · Round {college.reference_round} · {college.gender_pool}{!college.quota_resolved ? ' · State eligibility unresolved' : ''}</small></article>)}</div>
    {!data.cutoff_preview.length && <p>No cutoff references are available for this selection yet. Try a different category or check back later.</p>}
    <p>{data.college_note}</p>
  </details></>
}

export default function Roadmap() {
  const { search } = useLocation()
  const filters = new URLSearchParams(search)
  const [data, setData] = useState(null), [draft, setDraft] = useState(null)
  const [editing, setEditing] = useState(false), [busy, setBusy] = useState(false)
  const [error, setError] = useState(''), [saveError, setSaveError] = useState('')
  const [notice, setNotice] = useState(''), [version, setVersion] = useState(0)
  const editButton = useRef(null), saving = useRef(false)
  useEffect(() => {
    let active = true
    setError('')
    request('/api/roadmap', version ? { cache: false } : {}).then(value => {
      if (active) { setData(value); setDraft(value.settings) }
    }).catch(failure => { if (active) setError(failure.message) })
    return () => { active = false }
  }, [version])

  function editGoals() {
    if (saving.current) return
    setDraft(data.settings); setSaveError(''); setNotice(''); setEditing(true)
    requestAnimationFrame(() => {
      const heading = document.getElementById('my-plan-goals-heading')
      heading?.focus({ preventScroll: true }); heading?.scrollIntoView({ block: 'start' })
    })
  }
  function closeEditor() { setEditing(false); setSaveError(''); requestAnimationFrame(() => editButton.current?.focus()) }
  async function save(event) {
    event.preventDefault()
    if (saving.current) return
    saving.current = true; setBusy(true); setSaveError(''); setNotice('')
    try {
      const value = await request('/api/roadmap', { method: 'PUT', body: goalPayload(draft) })
      setData(value); setDraft(value.settings); closeEditor()
      setNotice('Your plan is ready. Start with the recommended topic below; your previous checkpoints are in Past reviews.')
    } catch (failure) { setSaveError(failure.message || 'Your goals could not be saved. Please try again.') }
    finally { saving.current = false; setBusy(false) }
  }
  const goal = data && planGoal(data.settings, data.saved)
  const count = data?.baseline.count || 0

  return <div className="crackjee-root"><AppHeader/><main className="wrap my-plan-page">
    <header className="mp-page-heading"><div><span className="mp-eyebrow">MY PLAN <span>/</span> JEE MAIN</span><h1>A clear next step.<br/><span>Every time you show up.</span></h1><p>Your goal, your study week and the next topic to work on. All in one place.</p></div>{data && <button ref={editButton} type="button" className="btn btn-secondary" onClick={editing ? closeEditor : editGoals} aria-expanded={editing} aria-controls="my-plan-goals" disabled={busy}><SlidersHorizontal size={16}/>{editing ? 'Close goal settings' : data.saved ? 'Edit my goals' : 'Set my goal'}</button>}</header>
    {error && <div className="mp-error" role="alert"><p>{error}</p><button type="button" className="btn btn-secondary btn-sm" onClick={() => setVersion(value => value + 1)}>Try loading again</button></div>}
    {notice && <div className="mp-success" role="status"><Check size={18}/><p>{notice}</p></div>}
    {!data && !error && <div className="mp-loading" role="status"><p>Reading your practice and putting your next steps together…</p><div aria-hidden="true"><span/><span/><span/></div><section aria-hidden="true"><span/><span/><span/></section></div>}
    {data && <>
      {editing ? <PlanGoalEditor draft={draft} setDraft={setDraft} data={data} busy={busy} error={saveError} onSave={save} onCancel={closeEditor}/> : <>
        <section className="mp-overview" aria-label="Your goal, baseline and study time">
          <article><span className="mp-overview-icon"><Flag size={19}/></span><div><span>{goal.label}</span><strong>{goal.value}</strong><small>{goal.detail}</small></div></article>
          <article><span className="mp-overview-icon"><Target size={19}/></span><div><span>{count ? 'Your current baseline' : 'Your starting score'}</span><strong>{data.baseline.score == null ? 'Let’s find out' : <>{number(data.baseline.score)} <em>/ 300</em></>}</strong><small>{count ? `Median of ${count} recent assessment${count === 1 ? '' : 's'}` : 'A balanced assessment gives you a baseline'}</small></div></article>
          <article><span className="mp-overview-icon"><Clock3 size={19}/></span><div><span>{data.settings.available_hours == null ? 'Suggested study time' : 'Your study time'}</span><strong>{data.settings.weekly_hours} <em>hours / week</em></strong><small>Topic practice + room for revision</small></div></article>
        </section>
        {!data.saved && <section className="mp-welcome"><div><span className="mp-eyebrow">FIRST TIME HERE?</span><h2>Your first step is already picked.</h2><p>Try the topic below, or set a goal to personalise your schedule. Your answers will guide what comes next.</p></div><button type="button" className="mp-text-action" onClick={editGoals}>Make this plan mine<ArrowRight size={15}/></button></section>}
      </>}
      <PlanWorkspace data={data.journey} outlook={data} onEditGoals={editGoals} preferredSubject={filters.get('subject')} preferredChapter={filters.get('chapter')} collegeDetails={<CollegeReferences data={data} onEdit={editGoals}/>}/>
      <details className="mp-disclosure mp-past-reviews"><summary>Past reviews <span>{data.checkpoints.length}</span><ChevronDown size={17}/></summary><p>When you save new goals, your previous seven-day checkpoints are kept here.</p>{!data.checkpoints.length ? <p>No previous reviews yet. Your first one will appear when you update your goals.</p> : <ol>{[...data.checkpoints].reverse().map((checkpoint, index) => <li key={`${checkpoint.date}-${index}`}><strong>{date(checkpoint.date)}</strong><ul>{checkpoint.tasks.map((task, i) => <li key={i}><span>{task.title}</span><small>{task.met ? 'Checkpoint met' : `${task.answered}/5 fresh answers · ${task.correct} correct`}</small></li>)}</ul></li>)}</ol>}</details>
    </>}
  </main></div>
}
