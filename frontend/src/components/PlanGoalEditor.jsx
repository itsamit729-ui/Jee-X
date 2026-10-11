import { useEffect, useRef, useState } from 'react'
import { ArrowRight, Check, ChevronDown, Flag, Target, X } from 'lucide-react'
import CollegeInfo from './CollegeInfo.jsx'
import { request } from '../lib/api.js'

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

export default function PlanGoalEditor({ draft, setDraft, data, busy, error, onSave, onCancel }) {
  const heading = useRef(null)
  useEffect(() => { heading.current?.focus({ preventScroll: true }); heading.current?.scrollIntoView({ block: 'start' }) }, [])
  const field = (name, value) => setDraft(current => ({ ...current, [name]: value }))
  const admission = (name, value) => setDraft(current => ({ ...current, admission: { ...current.admission, [name]: value } }))
  return <form id="my-plan-goals" className="mp-goal-editor" onSubmit={onSave} aria-labelledby="my-plan-goals-heading">
    <header><div><span className="mp-eyebrow">MAKE THIS PLAN YOURS</span><h2 id="my-plan-goals-heading" ref={heading} tabIndex={-1}>A goal. A pace. Your way forward.</h2><p>Choose what you’re aiming for and the time you can give it. You can change these later.</p></div><button type="button" className="mp-close" aria-label="Cancel goal changes" disabled={busy} onClick={onCancel}><X size={20}/></button></header>
    <fieldset disabled={busy}>
      <section className="mp-goal-step"><div className="mp-goal-step-title"><span>01</span><div><h3>What are you working towards?</h3><p>A score to aim for, or colleges you’d love to explore.</p></div></div>
        <div className="mp-goal-options" role="group" aria-label="Choose your goal type"><button type="button" aria-pressed={draft.goal_type === 'marks'} onClick={() => setDraft(value => ({ ...value, goal_type: 'marks', target_marks: value.target_marks || 150 }))}><Target size={21}/><span><strong>A marks target</strong><small>Choose a JEE Main score out of 300</small></span><span className="mp-option-check">{draft.goal_type === 'marks' && <Check size={13}/>}</span></button><button type="button" aria-pressed={draft.goal_type === 'colleges'} onClick={() => field('goal_type', 'colleges')}><Flag size={21}/><span><strong>A college goal</strong><small>Choose up to three college & branch pairs</small></span><span className="mp-option-check">{draft.goal_type === 'colleges' && <Check size={13}/>}</span></button></div>
        {draft.goal_type === 'marks' ? <div className="mp-target-input"><label htmlFor="mp-target-marks">Your target score</label><div><input id="mp-target-marks" required type="number" min="1" max="300" value={draft.target_marks ?? ''} onChange={event => field('target_marks', event.target.value)}/><span>/ 300 marks</span></div><div className="mp-goal-presets" role="group" aria-label="Suggested marks targets">{[120, 150, 180, 210].map(marks => <button type="button" key={marks} aria-pressed={Number(draft.target_marks) === marks} onClick={() => field('target_marks', marks)}>{marks}</button>)}</div><p>Pick a starting target. Your assessments will show the distance to it.</p></div> : <CollegePicker draft={draft} setDraft={setDraft}/>}
      </section>
      <section className="mp-goal-step"><div className="mp-goal-step-title"><span>02</span><div><h3>How much time fits your week?</h3><p>Include topic study, revision and assessments.</p></div></div><div className="mp-hours-row"><label htmlFor="mp-available-hours">Hours per week<input id="mp-available-hours" type="number" min="1" max="40" value={draft.available_hours ?? ''} placeholder={String(draft.weekly_hours)} onChange={event => field('available_hours', event.target.value === '' ? null : Number(event.target.value))}/></label><p>Leave this blank to use your suggested pace of <strong>{draft.weekly_hours} hours per week</strong>. We’ll keep room for revisits and mistakes.</p></div></section>
      <section className="mp-goal-step"><div className="mp-goal-step-title"><span>03</span><div><h3>Make college comparisons more useful <small>Optional</small></h3><p>Add eligibility details if you want more relevant historical cutoff comparisons.</p></div></div><details className="mp-eligibility"><summary>Category, state & existing ranks<ChevronDown size={17}/></summary><p>For NIT quotas, use your <strong>Class XII state code of eligibility</strong>, not where you currently live. Details are self-reported; check your JoSAA eligibility.</p><div className="roadmap-fields"><label>Category<select value={draft.admission.category} onChange={event => setDraft(value => ({ ...value, admission: { ...value.admission, category: event.target.value, category_rank: null, category_pwd_rank: null } }))}>{['OPEN', 'EWS', 'OBC-NCL', 'SC', 'ST'].map(category => <option key={category} value={category}>{category === 'OPEN' ? 'General / OPEN' : category}</option>)}</select></label><label>State code of eligibility<select value={draft.admission.state || ''} onChange={event => admission('state', event.target.value || null)}><option value="">Choose state / union territory</option>{data.states.map(state => <option key={state}>{state}</option>)}</select></label></div>
        <div className="mp-eligibility-checks">{[['female_pool', 'Include female-only seat pools (if eligible)'], ['pwd', 'Include PwD seat pools (if eligible)']].map(([name, label]) => <label key={name}><input type="checkbox" checked={draft.admission[name]} onChange={event => admission(name, event.target.checked)}/>{label}</label>)}</div>
        <details className="mp-ranks"><summary>Already have your JEE Main ranks?<ChevronDown size={15}/></summary><p>Mock marks estimate CRL only. Use the corresponding category or PwD rank for those seat pools; leave blank if you have not received one.</p><div className="roadmap-fields">{[['crl', 'CRL'], ...(draft.admission.category !== 'OPEN' ? [['category_rank', `${draft.admission.category} category rank`]] : []), ...(draft.admission.pwd ? [['crl_pwd', 'CRL-PwD'], ...(draft.admission.category !== 'OPEN' ? [['category_pwd_rank', `${draft.admission.category}-PwD rank`]] : [])] : [])].map(([name, label]) => <label key={name}>{label}<input type="number" min="1" max="3000000" value={draft.admission[name] || ''} onChange={event => admission(name, event.target.value ? Number(event.target.value) : null)}/></label>)}</div></details>
      </details></section>
    </fieldset>
    {error && <p className="mp-error" role="alert">{error}</p>}
    <footer><p>Saving creates a new seven-day schedule.<br/>Your current checkpoints stay in Past reviews.</p><div><button type="button" className="btn btn-secondary" onClick={onCancel} disabled={busy}>Cancel</button><button type="submit" className="btn btn-primary" disabled={busy || (draft.goal_type === 'colleges' && !draft.college_choices.length)}>{busy ? 'Building your plan…' : data.saved ? 'Save & update my plan' : 'Create my plan'}<ArrowRight size={16}/></button></div></footer>
  </form>
}
