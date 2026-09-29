import SectionTabs from '../components/SectionTabs.jsx'
import TopicStudyPlan from '../components/TopicStudyPlan.jsx'
import CollegeInfo from '../components/CollegeInfo.jsx'
import { useEffect, useState } from 'react'
import { Link, useLocation } from 'react-router-dom'
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
    <h3>{scenario.basis === 'college_cutoff' ? 'Your college benchmarks' : scenario.rank_low == null ? 'Rank evidence needed' : `CRL ${number(scenario.rank_low)}${scenario.rank_high !== scenario.rank_low ? `–${number(scenario.rank_high)}` : ''}`}</h3>
    <p>{scenario.basis === 'college_cutoff' ? 'Reference for your comparable college choices, based on historical closing ranks.' : scenario.basis === 'entered_crl' ? 'Your entered CRL; not independently verified.' : scenario.reference_year ? `Historical marks model: ${scenario.reference_year} · Rank reference: ${scenario.rank_reference_year}.` : 'Complete a baseline or choose a goal with available reference data. Estimates appear only within the available reference range.'}</p>
    {scenario.rank_inputs && <p>{Object.entries(scenario.rank_inputs).map(([list, rank]) => `${list}: ${number(rank)}`).join(' · ')}</p>}
    {scenario.percentile_low != null && <p>Estimated percentile {scenario.percentile_low.toFixed(2)}–{scenario.percentile_high.toFixed(2)}</p>}
    {scenario.colleges.length ? <ul className="roadmap-colleges">{scenario.colleges.map((college, i) => <li key={`${college.institute}-${college.program}-${i}`}><strong>{college.institute}<CollegeInfo institute={college.institute} program={college.program}/></strong><span>{college.program}</span><small>{college.reference_year} · Round {college.reference_round} · {college.quota} · {college.seat_type} · {college.gender_pool}</small><small>{college.rank_list || 'CRL'} closing rank {number(college.closing_rank)} · {scenario.basis === 'college_cutoff' ? 'Historical target benchmark' : college.meets_conservative_estimate ? 'Within the compared rank range' : 'Only overlaps the optimistic estimate'}</small></li>)}</ul> : <div className="roadmap-empty">{scenario.rank_low == null ? 'No college comparison yet.' : 'No matching cutoffs for the available rank evidence and eligibility details. This does not mean you have no admission options.'}</div>}
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
    <ol className="roadmap-choices">{choices.map((c, i) => <li key={c.id}><span className="roadmap-step">{i + 1}</span><div><strong>{c.institute}<CollegeInfo institute={c.institute} program={c.program}/></strong><small>{c.program}</small></div><button type="button" className="btn btn-quiet" onClick={() => remove(c.id)} aria-label={`Remove ${c.institute}, ${c.program}`}>Remove</button></li>)}</ol>
    {choices.length < 3 && <><label className="roadmap-search-label">Find a college or branch<input type="search" value={query} placeholder="Search institute name or branch" onChange={e => setQuery(e.target.value)}/></label>
    <div className="roadmap-search-results" aria-label="College and branch search results">{loading ? <p role="status">Finding choices…</p> : options.filter(o => !draft.college_choices.includes(o.id)).map(o => <button key={o.id} type="button" onClick={() => choose(o)}><span><strong>{o.institute}</strong><small>{o.program}</small></span><span aria-hidden="true">+</span></button>)}{!loading && options.length === 0 && <p>No matching programs in our catalog yet. Try another name, or use a marks goal.</p>}</div></>}
    {choices.length === 3 && <p role="status">All three choices added. Remove one to change it.</p>}{error && <p role="alert">{error}</p>}
  </div>
}

export default function Roadmap() {
  const { hash, search } = useLocation()
  const filters = new URLSearchParams(search)
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
    request('/api/roadmap', { cache: false }).then(value => {
      if (active) { setData(value); setDraft(value.settings) }
    }).catch(e => { if (active) setError(e.message) })
    return () => { active = false }
  }, [version])
  useEffect(() => {
    if (data && hash) {
      const target = document.getElementById(hash.slice(1))
      let parent = target?.parentElement
      while (parent) { if (parent.tagName === 'DETAILS') parent.open = true; parent = parent.parentElement }
      target?.scrollIntoView({ block: 'start' })
    }
  }, [data, hash])
  async function save(event) {
    event?.preventDefault()
    setBusy(true); setError(''); setNotice('')
    try {
      const value = await request('/api/roadmap', { method: 'PUT', body: {
        available_hours: draft.available_hours == null ? null : Number(draft.available_hours),
        admission: draft.admission,
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
    <header className="roadmap-heading"><div><span className="roadmap-kicker">YOUR NEXT CHAPTER</span><h1>My JEE Plan</h1><p>Know where you stand, what could open up, and what to practise today.</p></div>{data && <button className="btn btn-secondary" onClick={() => { setDraft(data.settings); setEditing(!editing) }} aria-expanded={editing}><SlidersHorizontal size={16}/> {editing ? 'Close goals' : 'Adjust my goals'}</button>}</header>
    {error && <div className="alert" role="alert">{error} <button className="btn btn-secondary btn-sm" onClick={() => setVersion(v => v + 1)}>Retry loading</button></div>}
    {notice && <p className="roadmap-notice" role="status"><Check size={16}/>{notice}</p>}
    {!data && !error && <div className="roadmap-loading" role="status"><span className="spin"/> Reading your recent practice and building your next steps…</div>}
    {data && <>
      {!data.saved && !editing && <div className="roadmap-notice"><p>Choose your marks target or up to three college and branch choices to personalise this plan.</p><button className="btn btn-secondary" onClick={() => setEditing(true)}>Set my goal</button></div>}
      {editing && <form className="roadmap-goals" onSubmit={save}><div className="roadmap-section-heading"><div><span className="roadmap-kicker">MAKE IT YOURS</span><h2>{data.saved ? 'A plan that fits your week' : 'Start with a goal you care about'}</h2></div><Flag size={22}/></div>
        <label className="roadmap-search-label">Hours you can study each week<input type="number" min="1" max="40" value={draft.available_hours ?? ''} placeholder={`Suggested: ${draft.weekly_hours} hours`} onChange={e => field('available_hours', e.target.value === '' ? null : Number(e.target.value))}/></label>
        <div className="roadmap-goal-switch" role="group" aria-label="Choose your goal type">
          <button type="button" aria-pressed={draft.goal_type === 'marks'} onClick={() => setDraft(d => ({ ...d, goal_type: 'marks', target_marks: d.target_marks || 150 }))}><Target size={20}/><strong>I have a marks target</strong><span>Choose the score you want to work towards.</span></button>
          <button type="button" aria-pressed={draft.goal_type === 'colleges'} onClick={() => setDraft(d => ({ ...d, goal_type: 'colleges' }))}><Flag size={20}/><strong>I have colleges in mind</strong><span>Add up to three college and branch choices.</span></button>
        </div>
        {draft.goal_type === 'marks' ? <div className="roadmap-fields"><label>Target marks / 300<input required type="number" min="1" max="300" value={draft.target_marks ?? ''} onChange={e => field('target_marks', e.target.value)}/></label></div> : <CollegePicker draft={draft} setDraft={setDraft}/>}
        <details className="roadmap-admission-settings" open={!data.settings.admission.state}><summary>Personalise college matches · category & state</summary>
          <p>For NIT quotas, select your <strong>Class XII state code of eligibility</strong>, not where you currently live. Details are self-reported; check your JoSAA eligibility.</p>
          <div className="roadmap-fields"><label>Category<select value={draft.admission.category} onChange={e => setDraft(d => ({ ...d, admission: { ...d.admission, category: e.target.value, category_rank: null, category_pwd_rank: null } }))}>{['OPEN','EWS','OBC-NCL','SC','ST'].map(c => <option key={c} value={c}>{c === 'OPEN' ? 'General / OPEN' : c}</option>)}</select></label>
          <label>State code of eligibility<select value={draft.admission.state || ''} onChange={e => setDraft(d => ({ ...d, admission: { ...d.admission, state: e.target.value || null } }))}><option value="">Choose state / union territory</option>{data.states.map(state => <option key={state}>{state}</option>)}</select></label></div>
          <div className="roadmap-admission-checks">{[['female_pool','Include female-only seat pools (if eligible)'],['pwd','Include PwD seat pools (if eligible)']].map(([key,label]) => <label key={key}><input type="checkbox" checked={draft.admission[key]} onChange={e => setDraft(d => ({ ...d, admission: { ...d.admission, [key]: e.target.checked } }))}/>{label}</label>)}</div>
          <details><summary>Already have JEE Main ranks? Add them for category comparisons</summary><p>Optional. Mock marks estimate CRL only. Category and PwD ranks must come from the corresponding rank list; leave them blank if you have not received them.</p><div className="roadmap-fields">{[['crl','CRL'], ...(draft.admission.category !== 'OPEN' ? [['category_rank',`${draft.admission.category} category rank`]] : []), ...(draft.admission.pwd ? [['crl_pwd','CRL-PwD'], ...(draft.admission.category !== 'OPEN' ? [['category_pwd_rank',`${draft.admission.category}-PwD rank`]] : [])] : [])].map(([key,label]) => <label key={key}>{label}<input type="number" min="1" max="3000000" value={draft.admission[key] || ''} onChange={e => setDraft(d => ({ ...d, admission: { ...d.admission, [key]: e.target.value ? Number(e.target.value) : null } }))}/></label>)}</div></details>
        </details>
        <p className="roadmap-help">We handle the schedule, suggested pace and assessment checkpoints using your profile and practice history.</p>
        <div className="roadmap-form-footer"><p>Saving starts a new seven-day plan and archives current checkpoints.</p><button className="btn btn-primary" disabled={busy || (draft.goal_type === 'colleges' && !draft.college_choices.length)}>{busy ? 'Building your plan…' : data.saved ? 'Save goals & rebuild plan' : 'Create my plan'}<ArrowRight size={16}/></button></div>
      </form>}
      {data.journey && <TopicStudyPlan key={version} data={data.journey} outlook={data} preferredSubject={filters.get('subject')} preferredChapter={filters.get('chapter')}/>}
      <SectionTabs labels={["Score & goal", "College explorer", "Past reviews"]} title="Your progress & possibilities"><section>
      <section className="roadmap-position" aria-label="Current position and goal"><article><span className="roadmap-kicker">WHERE YOU STAND</span><div className="roadmap-number">{data.baseline.score == null ? 'Let’s find out' : number(data.baseline.score)}{data.baseline.score != null && <small>/ 300</small>}</div><p>{data.baseline.count ? `${data.baseline.count} recent assessment${data.baseline.count === 1 ? '' : 's'} · median score` : 'Topic practice shapes your plan. A balanced assessment establishes your exam baseline.'}</p><Link to="/practice?assessment=1">{data.baseline.count ? 'Take another checkpoint' : 'Take a baseline assessment'} <ArrowUpRight size={16}/></Link></article><article><span className="roadmap-kicker">WHERE YOU WANT TO GO</span>{data.settings.goal_type === 'marks' ? <><div className="roadmap-number">{data.settings.target_marks}<small>/ 300</small></div><p>{gap == null ? 'Your chosen target. Your baseline will show the gap.' : gap > 0 ? `${number(gap)} marks from your current baseline. Progress must be demonstrated in fresh assessments.` : 'You have reached this marks target. Work on consistency or choose a new goal.'}</p></> : <><div className="roadmap-number">{data.settings.choices.length}<small>college & branch choices</small></div><p>{data.settings.target_crl ? `OPEN-seat reference: CRL ${number(data.settings.target_crl)} for the most demanding comparable OPEN choice. This is a past cutoff, not a guaranteed admission target.` : 'Each choice below shows its own category rank benchmark where applicable data is available.'}</p></>}<span className="roadmap-tag">{days == null ? `${data.settings.target_year} target year` : `${days} days to the configured exam date`}</span></article></section>
      <div className="roadmap-auto-plan"><span className="roadmap-kicker">PLANNED FOR YOU</span><strong>{data.settings.weekly_hours} suggested hours / week</strong><p>{data.settings.pace_basis} {data.settings.timeline_note}</p></div>
      {data.settings.goal_type === 'colleges' && <ol className="roadmap-choices roadmap-selected-goals">{data.settings.choices.map((c, i) => <li key={c.id}><span className="roadmap-step">{i + 1}</span><div><strong>{c.institute}<CollegeInfo institute={c.institute} program={c.program}/></strong><span>{c.program}</span><small>{c.rank ? `${c.year} · Round ${c.round} · ${c.quota} / ${c.seat_type} / ${c.gender_pool} · Closing ${c.rank_list} ${number(c.rank)}` : 'No applicable cutoff resolved. Add your state of eligibility, or check whether this program requires a different exam route.'}</small></div></li>)}</ol>}

      </section>
      <section><section id="college-reference-details" className="roadmap-college-section"><div className="roadmap-section-heading"><div><span className="roadmap-kicker">THE BIGGER PICTURE</span><h2>What could open up?</h2></div></div><p className="roadmap-intro-copy">Compare your current evidence with a chosen target. Following a plan does not guarantee marks, rank or admission.</p><div className="roadmap-outlook-grid"><Outlook scenario={data.current} label="CURRENT EVIDENCE"/><Outlook scenario={data.target} label="IF YOU REACH YOUR TARGET" target/></div><p className="roadmap-help">{data.college_note}</p></section>
      <section className="roadmap-cutoff-explorer"><div className="roadmap-section-heading"><div><span className="roadmap-kicker">EXPLORE YOUR OPTIONS</span><h2>NIT cutoffs · {data.settings.admission.category}{data.settings.admission.pwd ? ' / PwD' : ''}</h2></div><button className="btn btn-secondary" onClick={() => { setDraft(data.settings); setEditing(true); window.scrollTo({ top: 0, behavior: 'smooth' }) }}>Change category / state</button></div>
        <p className="roadmap-help">These are historical cutoffs, not colleges you are guaranteed to get. {data.settings.admission.state ? `Quota filtered for ${data.settings.admission.state}.` : 'Choose your state above to resolve NIT quotas. Until then these examples are not eligibility matches.'} Reserved-category cutoffs use category ranks; do not compare them to CRL.</p>
        <div className="roadmap-outlook-grid">{data.cutoff_preview.map((c, i) => <article className="roadmap-outlook" key={i}><span className="roadmap-kicker">{c.quota} · {c.seat_type} · {c.gender_pool}</span><h3>{c.institute}<CollegeInfo institute={c.institute} program={c.program}/></h3><p>{c.program}</p><strong>{c.rank_list} closing rank {number(c.closing_rank)}</strong><p>{c.reference_year} · Round {c.reference_round}{!c.quota_resolved ? ' · State eligibility unresolved' : ''}</p></article>)}</div>
        {!data.cutoff_preview.length && <p>No NIT rows are available for this selection yet. Reference data loads after backend deployment; retry if an import is still running.</p>}
      </section>
      </section>
      <section className="plan-review-list"><h3>Previous plan reviews</h3>{!data.checkpoints.length && <p>Your reviews will appear here as your plan evolves.</p>}{[...data.checkpoints].reverse().map((checkpoint, i) => <div key={i}><strong>{date(checkpoint.date)}</strong><p>{checkpoint.tasks.map(t => `${t.title}: ${t.met ? 'checkpoint met' : `${t.answered}/5 fresh answers, ${t.correct} correct`}`).join(' · ')}</p></div>)}</section></SectionTabs>
    </>}
  </main></div>
}

