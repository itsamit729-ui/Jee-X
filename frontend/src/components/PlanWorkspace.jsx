import { useEffect, useId, useRef, useState } from 'react'
import { Link, useLocation, useNavigate } from 'react-router-dom'
import { ArrowRight, ArrowUpRight, BookOpen, CalendarCheck, Check, ChevronDown, Clock3, Flag, GraduationCap, Target } from 'lucide-react'
import CollegeHorizon from './CollegeHorizon.jsx'
import { subjectTestBuilderService } from '../lib/subjectTests.js'
import { requestFullscreen } from '../lib/fullscreen.js'
import { evidenceLabel, planSubjects, planTopics, topicPracticeOptions } from '../lib/planPresentation.js'
import './topic-study-plan.css'

const tabs = [
  { title: 'Today', description: 'Your next step', Icon: Target },
  { title: 'This week', description: 'Make time for it', Icon: CalendarCheck },
  { title: 'Milestones', description: 'See your progress', Icon: Flag },
  { title: 'Colleges', description: 'Keep a goal in sight', Icon: GraduationCap },
]
const labels = { baseline: 'Find your starting point', foundation: 'Build your basics', application: 'Solve harder questions', fluency: 'Build your speed', retention: 'Remember it later', mocks: 'Build mock consistency', goal: 'Reach your goal' }
const purposes = { foundation: ['repair', 'diagnose'], application: ['apply'], fluency: ['fluency'], retention: ['retention', 'maintain'] }
const actions = { diagnose: 'Find your level', repair: 'Strengthen a concept', apply: 'Apply your knowledge', fluency: 'Build your speed', retention: 'Check your recall', maintain: 'Keep it fresh' }

function TopicRow({ topic, index, onChoose }) {
  return <li style={{ '--item': Math.min(index, 8) }}><button type="button" className="mp-topic-row" onClick={() => onChoose(topic)}>
    <span className="mp-topic-number">{String(index + 1).padStart(2, '0')}</span>
    <span className="mp-topic-copy"><small>{planSubjects[topic.subject]} · {topic.chapter}</small><strong>{topic.topic}</strong><span>{topic.reason}</span></span>
    <span className="mp-topic-time">{topic.minutes || 30} min<ArrowRight size={17}/></span>
  </button></li>
}

function WeekPlan({ plan, topics, onChoose }) {
  const [subject, setSubject] = useState('')
  const visible = topics.filter(topic => !subject || topic.subject === subject)
  const week = visible.filter(topic => topic.week === 1)
  const laterWeeks = [...new Set(visible.map(topic => topic.week))].filter(value => value > 1)
  return <div className="mp-week">
    <div className="mp-view-heading"><div><span className="mp-eyebrow">A WEEK YOU CAN WORK WITH</span><h2>A little structure. Room to revise.</h2><p>Work down the list at your own pace. Your answers can change what comes next.</p></div><span className="mp-time-badge"><Clock3 size={16}/>{plan.weekly_hours} hours / week</span></div>
    <div className="mp-week-budget"><div><BookOpen size={20}/><span><strong>{plan.topic_minutes} min</strong>Focused topic sessions</span></div><span className="mp-budget-plus">+</span><div><CalendarCheck size={20}/><span><strong>{plan.reserved_minutes} min</strong>Revisits, mistakes & checkpoints</span></div><p>Each topic block includes review, practice and time to learn from mistakes.</p></div>
    <div className="mp-list-heading"><h3>This week’s topics</h3><div className="mp-subject-filter" role="group" aria-label="Filter scheduled topics by subject">{[['', 'All subjects'], ...Object.entries(planSubjects)].map(([code, label]) => <button type="button" key={code} aria-pressed={subject === code} onClick={() => setSubject(code)}>{label}</button>)}</div></div>
    <ol className="mp-topic-list" key={subject}>{week.map((topic, index) => <TopicRow key={topic.topic_id} topic={topic} index={index} onChoose={onChoose}/>)}</ol>
    {!week.length && <div className="mp-empty"><p>No topics from this selection are scheduled for week one.</p><Link to="/subject-test">Choose a practice topic <ArrowRight size={15}/></Link></div>}
    {laterWeeks.length > 0 && <details className="mp-disclosure"><summary>Look ahead · your later weeks<ChevronDown size={17}/></summary><p>{plan.timeline_note} {plan.capacity_note}</p>{laterWeeks.map(number => <details className="mp-later-week" key={number}><summary>Week {number}<span>{visible.filter(topic => topic.week === number).length} topics{visible.find(topic => topic.week === number)?.within_horizon ? '' : ' · beyond current planning horizon'}</span><ChevronDown size={15}/></summary><ol className="mp-topic-list">{visible.filter(topic => topic.week === number).map((topic, index) => <TopicRow key={topic.topic_id} topic={topic} index={index} onChoose={onChoose}/>)}</ol></details>)}</details>}
  </div>
}

function Milestones({ data, topics, onChoose, onColleges }) {
  const milestones = data.milestones || []
  const active = milestones.find(item => item.id === data.active_id) || milestones.find(item => !item.met) || milestones.at(-1)
  const [selected, setSelected] = useState(null)
  const stop = milestones.find(item => item.id === selected) || active
  const relevant = topics.filter(topic => purposes[stop?.id]?.includes(topic.purpose))
  return <div>
    <div className="mp-view-heading"><div><span className="mp-eyebrow">PROGRESS YOU CAN DEMONSTRATE</span><h2>Seven skills. One step at a time.</h2><p>Checkpoints reflect your fresh answers and assessments. They can need another check as evidence gets older.</p></div></div>
    <div className="mp-milestone-layout"><ol className="mp-milestone-path" aria-label="Your learning milestones">{milestones.map((item, index) => <li key={item.id} className={item.met ? 'is-met' : ''} style={{ '--item': index }}><button type="button" aria-pressed={stop?.id === item.id} aria-controls="mp-milestone-detail" onClick={() => setSelected(item.id)}><span className="mp-milestone-node">{item.met ? <Check size={17}/> : index + 1}</span><span><strong>{labels[item.id] || item.title}</strong><small>{item.met ? 'Checkpoint met' : item.status === 'recheck' ? 'Needs another check' : item.id === active?.id ? 'Your current milestone' : 'Coming up'}</small></span><ArrowRight size={16}/></button></li>)}</ol>
      {stop && <article className="mp-milestone-detail" id="mp-milestone-detail" aria-live="polite"><div key={stop.id} className="mp-panel-enter"><span className="mp-eyebrow">MILESTONE {milestones.indexOf(stop) + 1} OF {milestones.length}</span><h3>{labels[stop.id] || stop.title}</h3><p>{stop.purpose}</p><div className="mp-check-requirement"><span><Check size={16}/>What you need to show</span><p>{stop.requirement}</p>{stop.progress && <p className="mp-evidence">{stop.progress}</p>}</div>
        {relevant.length > 0 && <><h4>Topics that help with this step</h4><ol className="mp-topic-list mp-related-topics">{relevant.slice(0, 3).map((topic, index) => <TopicRow key={topic.topic_id} topic={topic} index={index} onChoose={onChoose}/>)}</ol></>}
        {['baseline', 'mocks'].includes(stop.id) && <><p className="mp-small-copy">Set aside 3 hours for a balanced assessment. Your result updates your score baseline and topic priorities.</p><Link className="btn btn-primary" to="/practice?assessment=1">{stop.id === 'baseline' ? 'Find my starting score' : 'Take a checkpoint assessment'}<ArrowRight size={16}/></Link></>}
        <div className="mp-college-bridge"><GraduationCap size={20}/><p>Stronger skills support better exam performance. Your college outlook updates when an assessment shows that progress.</p><button className="mp-text-action" type="button" onClick={onColleges}>See your college outlook<ArrowRight size={15}/></button></div>
      </div></article>}
    </div>
  </div>
}

export default function PlanWorkspace({ data, outlook, onEditGoals, preferredSubject, preferredChapter, collegeDetails }) {
  const { hash } = useLocation()
  const navigate = useNavigate()
  const id = useId()
  const sessionRef = useRef(null), launchLock = useRef(false)
  const [view, setView] = useState(hash.includes('college') ? 3 : 0)
  const [topicId, setTopicId] = useState(null)
  const [busy, setBusy] = useState(false), [error, setError] = useState('')
  const plan = data?.topic_plan
  const topics = planTopics(plan, preferredSubject, preferredChapter)
  const today = topics[0], focus = topics.find(topic => topic.topic_id === topicId) || today
  const milestones = data?.milestones || []
  const met = milestones.filter(item => item.met).length
  const current = milestones.find(item => item.id === data?.active_id) || milestones.find(item => !item.met) || milestones.at(-1)

  useEffect(() => { if (hash.includes('college')) setView(3) }, [hash])
  useEffect(() => {
    if (view !== 3 || !hash.includes('college')) return
    const frame = requestAnimationFrame(() => {
      const target = document.getElementById(hash.slice(1))
      let parent = target
      while (parent) { if (parent.tagName === 'DETAILS') parent.open = true; parent = parent.parentElement }
      target?.scrollIntoView({ block: 'start' })
    })
    return () => cancelAnimationFrame(frame)
  }, [view, hash])

  if (!plan) return <div className="mp-empty"><h2>Your plan is getting ready</h2><p>Choose a topic to start practising while your personalised schedule becomes available.</p><Link className="btn btn-primary" to="/subject-test">Choose a topic<ArrowRight size={16}/></Link></div>

  async function start() {
    if (!focus || launchLock.current) return
    launchLock.current = true
    requestFullscreen()
    setBusy(true); setError('')
    try { const paper = await subjectTestBuilderService.start(topicPracticeOptions(focus)); navigate('/practice', { state: { missionTest: paper } }) }
    catch (failure) { setError(failure.message || 'Practice could not be prepared. Please try again.') }
    finally { launchLock.current = false; setBusy(false) }
  }
  function chooseTopic(topic) {
    setTopicId(topic.topic_id); setView(0); setError('')
    requestAnimationFrame(() => { sessionRef.current?.focus({ preventScroll: true }); sessionRef.current?.scrollIntoView({ block: 'start' }) })
  }
  function changeView(index, focusTab = false) {
    setView(index)
    if (focusTab) requestAnimationFrame(() => document.getElementById(`${id}-tab-${index}`)?.focus())
  }
  function moveTab(event, index) {
    const next = event.key === 'ArrowRight' ? (index + 1) % tabs.length : event.key === 'ArrowLeft' ? (index + tabs.length - 1) % tabs.length : event.key === 'Home' ? 0 : event.key === 'End' ? tabs.length - 1 : null
    if (next !== null) { event.preventDefault(); changeView(next, true) }
  }
  const session = focus ? <article className="mp-session" ref={sessionRef} tabIndex={-1} aria-label="Your next study session">
    <div className="mp-session-top"><span className="mp-eyebrow"><span className="mp-live-dot"/>{focus === today ? 'YOUR NEXT BEST STEP' : 'YOUR SELECTED TOPIC'}</span><span><Clock3 size={14}/>{focus.minutes || 30} min study block</span></div>
    <div className="mp-session-content" key={focus.topic_id}><div className="mp-session-subject"><span>{planSubjects[focus.subject]}</span>{focus.chapter}</div><h2>{focus.topic}</h2><span className="mp-purpose">{actions[focus.purpose] || focus.action}</span><div className="mp-session-reason"><strong>Why this topic?</strong><p>{focus.reason}</p></div>
      <ol className="mp-session-steps">{[['01', 'Review', '10 min', 'Use your notes'], ['02', 'Practise', '15 min', 'A fresh topic set'], ['03', 'Reflect', '5 min', 'Learn from mistakes']].map(([step, title, time, detail]) => <li key={step}><span>{step}</span><div><strong>{title}<small>{time}</small></strong><p>{detail}</p></div></li>)}</ol>
      <div className="mp-start-row"><button type="button" className="btn btn-primary" disabled={busy} onClick={start}>{busy ? 'Preparing your questions…' : 'Start 15-minute practice'}<ArrowRight size={18}/></button><span>Review your notes first.<br/>Then we’ll open this exact topic.</span></div>
      {error && <p className="mp-error" role="alert">{error}</p>}
      <details className="mp-session-detail"><summary>Study guidance & your completion check<ChevronDown size={16}/></summary><ol>{focus.steps?.map(step => <li key={step}>{step}</li>)}</ol><p><strong>Move forward when:</strong> {focus.check}</p><p>{evidenceLabel(focus)}</p>{focus.prerequisites?.length > 0 && <p><strong>Useful foundations:</strong> {focus.prerequisites.join(', ')}. Unfinished prerequisites come earlier in your schedule.</p>}{focus.bank_note && <p>{focus.bank_note}</p>}</details>
      {focus !== today && <button type="button" className="mp-text-action" onClick={() => { setTopicId(null); setError('') }}>Back to your recommended topic<ArrowRight size={15}/></button>}
    </div>
  </article> : <div className="mp-empty"><BookOpen size={28}/><h2>Choose where to begin</h2><p>No complete topic sets are available for this selection yet.</p><Link className="btn btn-primary" to="/subject-test">Choose another practice focus<ArrowRight size={16}/></Link></div>

  return <section className="mp-workspace" aria-label="Your study plan">
    {(preferredSubject || preferredChapter) && <div className="mp-filter-note">Showing your selected {preferredChapter ? 'chapter' : planSubjects[preferredSubject] || 'subject'}.<Link to="/plan">Show my full plan</Link></div>}
    <div className="mp-tabs" role="tablist" aria-label="Explore your study plan" style={{ '--active-tab': view }}><span className="mp-tab-marker" aria-hidden="true"/>{tabs.map(({ title, description, Icon }, index) => <button type="button" role="tab" key={title} id={`${id}-tab-${index}`} aria-controls={`${id}-panel-${index}`} aria-selected={view === index} tabIndex={view === index ? 0 : -1} onKeyDown={event => moveTab(event, index)} onClick={() => changeView(index)}><Icon size={19}/><span><strong>{title}</strong><small>{description}</small></span></button>)}</div>
    {tabs.map((tab, index) => <div key={tab.title} role="tabpanel" hidden={view !== index} id={`${id}-panel-${index}`} aria-labelledby={`${id}-tab-${index}`} tabIndex={0} className="mp-tab-panel">
      {index === 0 && <div className="mp-today-grid">{session}<aside className="mp-today-aside">
        <article className="mp-progress-card"><div className="mp-card-heading"><span className="mp-eyebrow">YOUR MOMENTUM</span><Flag size={17}/></div><div className="mp-progress-overview"><div className="mp-progress-ring" role="img" aria-label={`${met} of ${milestones.length} milestones met`}><svg viewBox="0 0 88 88" aria-hidden="true"><circle cx="44" cy="44" r="37"/><circle className="mp-progress-fill" cx="44" cy="44" r="37" pathLength="100" strokeDasharray={`${milestones.length ? met / milestones.length * 100 : 0} 100`}/></svg><span><strong>{met}</strong><small>of {milestones.length}</small></span></div><div><h3>Milestones met</h3><p>Built from your answers,<br/>one skill at a time.</p></div></div><div className="mp-current-milestone"><span>{met === milestones.length && met ? 'Keep it consistent' : 'Focus on this checkpoint'}</span><strong>{labels[current?.id] || current?.title || 'Start with a topic session'}</strong></div><button className="mp-text-action" type="button" onClick={() => changeView(2, true)}>See what counts as progress<ArrowRight size={15}/></button></article>
        <article className="mp-up-next"><div className="mp-card-heading"><h3>Up next</h3><span>In your plan</span></div>{topics.filter(topic => topic.topic_id !== focus?.topic_id).slice(0, 2).map((topic, index) => <button type="button" key={topic.topic_id} onClick={() => chooseTopic(topic)}><span className="mp-topic-number">0{index + 2}</span><span><small>{planSubjects[topic.subject]}</small><strong>{topic.topic}</strong></span><ArrowRight size={15}/></button>)}{topics.length < 2 && <p>Your upcoming topics appear here as question sets become available.</p>}<button className="mp-text-action" type="button" onClick={() => changeView(1, true)}>See this week’s schedule<ArrowRight size={15}/></button></article>
      </aside><article className="mp-assessment-note"><span className="mp-assessment-icon"><Target size={23}/></span><div><h3>{outlook.baseline.count ? 'Check how your work is translating into marks.' : 'Curious where you stand in a full paper?'}</h3><p>{outlook.baseline.count ? 'A balanced assessment updates your score baseline and college outlook.' : 'Start with topic practice, or take a balanced assessment to find your starting score.'} Set aside 3 hours.</p></div><Link to="/practice?assessment=1">{outlook.baseline.count ? 'Take a checkpoint' : 'Find my starting score'}<ArrowUpRight size={16}/></Link></article></div>}
      {index === 1 && <WeekPlan plan={plan} topics={topics} onChoose={chooseTopic}/>}
      {index === 2 && <Milestones data={data} topics={topics} onChoose={chooseTopic} onColleges={() => changeView(3, true)}/>}
      {index === 3 && <div className="mp-colleges"><div className="mp-college-actions"><p>Compare your current evidence with the goal you’re working towards.</p><button type="button" className="btn btn-secondary btn-sm" onClick={onEditGoals}>Edit goal & eligibility<ArrowUpRight size={14}/></button></div><CollegeHorizon outlook={outlook}/>{collegeDetails}<Link className="mp-text-action" to="/advanced">Planning for an IIT? Explore JEE Advanced<ArrowUpRight size={15}/></Link></div>}
    </div>)}
    <details className="mp-disclosure mp-how-it-works"><summary>How does my plan adapt?<ChevronDown size={17}/></summary><div className="mp-how-grid">{[['Practise a topic', 'Your fresh answers help identify gaps, forgotten concepts and slow responses.'], ['Review the result', 'Read explanations and record what caused each mistake before your next session.'], ['Come back for your next step', 'Your priorities update after submitted tests. A session alone does not complete a milestone.']].map(([title, copy], index) => <div key={title}><span>0{index + 1}</span><h3>{title}</h3><p>{copy}</p></div>)}</div><p>{plan.goal_explanation} {plan.method}</p><p>Topic practice guides what to study. Balanced assessments demonstrate marks progress. The plan cannot guarantee a score or admission.</p></details>
  </section>
}
