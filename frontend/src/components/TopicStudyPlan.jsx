import SectionTabs from './SectionTabs.jsx'
import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { ArrowRight, Check, Flag } from 'lucide-react'
import { subjectTestBuilderService } from '../lib/subjectTests.js'
import { requestFullscreen } from '../lib/fullscreen.js'
import CollegeHorizon from './CollegeHorizon.jsx'
import './topic-study-plan.css'

const subjects = { PHY: 'Physics', CHEM: 'Chemistry', MATH: 'Mathematics' }
const labels = { baseline: 'Find your level', foundation: 'Build your basics', application: 'Solve harder questions', fluency: 'Build your speed', retention: 'Remember it later', mocks: 'Prove it in mocks', goal: 'Reach your goal' }
const purposes = { foundation: ['repair', 'diagnose'], application: ['apply'], fluency: ['fluency'], retention: ['retention', 'maintain'] }
export default function TopicStudyPlan({ data, outlook, compact = false, onStartMission, missionBusy = false, afterTest = false, preferredSubject, preferredChapter }) {
  const navigate = useNavigate()
  const [busy, setBusy] = useState(false), [error, setError] = useState('')
  const [selected, setSelected] = useState(null), [topicId, setTopicId] = useState(null)
  const plan = data?.topic_plan
  if (!plan) return null
  const topics = plan.topics.filter(t => (!preferredSubject || t.subject === preferredSubject) && (!preferredChapter || String(t.chapter_id) === String(preferredChapter)))
  const today = topics[0]
  const milestones = data.milestones || []
  const active = milestones.find(m => m.id === data.active_id) || milestones.find(m => !m.met) || milestones[milestones.length - 1]
  const stop = milestones.find(m => m.id === selected) || active
  const focus = topics.find(t => t.topic_id === topicId) || today
  const relevant = topics.filter(t => purposes[stop?.id]?.includes(t.purpose))
  const evidence = topic => topic.accuracy == null ? 'No fresh answers yet — start with a diagnostic topic set.' : `${topic.accuracy}% correct · ${topic.fresh_answers} fresh answers · ${topic.study_days} study days`
  async function start(topic) {
    const options = { mission: true, assessment: false, subjectCode: topic.subject, chapterId: topic.chapter_id, topicId: topic.topic_id, durationMinutes: 15, mode: 'recommended' }
    if (!onStartMission) requestFullscreen()
    setBusy(true); setError('')
    try {
      if (onStartMission) await onStartMission(options)
      else { const paper = await subjectTestBuilderService.start(options); navigate('/practice', { state: { missionTest: paper } }) }
    } catch (e) { setError(e.message) } finally { setBusy(false) }
  }
  function chooseTopic(topic) { setTopicId(topic.topic_id); document.getElementById('plan-practice-session')?.scrollIntoView({ behavior: 'smooth', block: 'start' }) }
  const session = focus && <article id="plan-practice-session" className="plan-session" aria-label="Your next topic">
    <span className="topic-plan-label">{focus === today ? 'YOUR NEXT STEP' : 'SELECTED TOPIC'} · {focus.minutes} MIN</span>
    <small>{subjects[focus.subject]} · {focus.chapter}</small><h2>{focus.topic}</h2>
    <p><strong>Why this topic:</strong> {focus.reason}</p>
    <button className="btn btn-primary" disabled={busy || missionBusy} onClick={() => start(focus)}>{busy || missionBusy ? 'Preparing practice…' : focus === today ? 'Start today’s practice' : 'Practise this topic'}<ArrowRight size={17}/></button>
    <details><summary>Your session & completion check</summary><ol>{focus.steps.map(step => <li key={step}>{step}</li>)}</ol><p><strong>Move forward when:</strong> {focus.check}</p><p>{evidence(focus)}</p>{focus.prerequisites?.length > 0 && <p>Prerequisites: {focus.prerequisites.join(', ')}. Unfinished prerequisites come earlier in your plan.</p>}{focus.bank_note && <p>{focus.bank_note}</p>}<small>Use your notes for the concept review. Practice opens questions from this exact topic.</small></details>
    {focus !== today && <button className="btn btn-quiet" onClick={() => setTopicId(null)}>Return to today’s recommendation</button>}
  </article>
  return <section className="topic-plan unified-plan" aria-label="Your JEE plan">
    {afterTest && <p className="plan-update" role="status"><Check size={16}/> Your plan has been updated using this test.</p>}
    {error && <p role="alert" className="alert">{error}</p>}
    {!compact && <>
      {outlook ? <CollegeHorizon outlook={outlook}/> : <div className="plan-compass"><span className="topic-plan-label">YOUR GOAL</span><h2>{plan.goal}</h2><p>{plan.weekly_hours} study hours / week</p></div>}
      {session}
      <div className="plan-route-heading"><div><h2>The route to your goal</h2><p>Each stop builds a skill. Your next assessment shows how it changes your college options.</p></div><span className="plan-live">Updated from your answers</span></div>
      <div className="plan-route-layout"><nav className="plan-map" aria-label="Learning milestones"><ol>{milestones.map((m, i) => <li key={m.id} className={m.met ? 'is-met' : m.id === active?.id ? 'is-current' : ''}><button type="button" aria-pressed={stop?.id === m.id} aria-controls="plan-stop-detail" onClick={() => setSelected(m.id)}><span className="plan-node">{m.met ? <Check size={18}/> : m.id === 'goal' ? <Flag size={18}/> : i + 1}</span><span><strong>{labels[m.id] || m.title}</strong><small>{m.met ? 'Checkpoint met' : m.id === active?.id ? 'You are here' : m.status === 'recheck' ? 'Needs another check' : 'Ahead on your path'}</small></span></button></li>)}</ol></nav>
      <div className="plan-stop" id="plan-stop-detail" aria-live="polite">{stop && <><span className="topic-plan-label">{stop.met ? 'CHECKPOINT MET' : stop.id === active?.id ? 'CURRENT MILESTONE' : 'EXPLORE YOUR PATH'}</span><h2>{labels[stop.id] || stop.title}</h2><p>{stop.purpose}</p><details className="plan-check"><summary>What you need to demonstrate</summary><p>{stop.requirement}</p></details>
      {relevant.length > 0 && <div className="plan-stop-topics"><strong>Topics to work on</strong>{relevant.slice(0, 3).map(t => <button type="button" key={t.topic_id} aria-pressed={focus?.topic_id === t.topic_id} onClick={() => chooseTopic(t)}><span><small>{subjects[t.subject]}</small>{t.topic}</span><ArrowRight size={15}/></button>)}<small>Select a topic to open its practice session above.</small></div>}
      {['baseline', 'mocks'].includes(stop.id) && <><p>Use a 3-hour study block for a balanced assessment. Its result updates your standing and topic priorities.</p><Link className="btn btn-secondary" to="/practice?assessment=1">{stop.id === 'baseline' ? 'Take baseline assessment' : 'Take a checkpoint assessment'}<ArrowRight size={15}/></Link></>}
      {outlook && <div className="plan-college-bridge"><span className="topic-plan-label">WHAT THIS MEANS FOR COLLEGES</span><p>{stop.id === 'goal' ? 'The target card above shows choices at your goal or historical benchmarks for your selected colleges.' : stop.id === 'baseline' || stop.id === 'mocks' ? 'A submitted balanced assessment refreshes your score and current college matches above.' : 'This skill supports exam performance. Your current college matches update when a balanced assessment demonstrates the improvement.'}</p><small>Skill checkpoints do not imply a fixed marks gain or unlock a college automatically.</small><a href="#college-outlook">Compare current & target colleges <ArrowRight size={14}/></a></div>}
      </>}</div></div>
    </>}
    {compact && session}
    {!session && <p>No complete topic sets are available for this selection yet. <Link to="/subject-test">Choose another focus</Link>.</p>}
    {compact ? <Link className="topic-plan-full" to="/plan">Open my full JEE plan <ArrowRight size={16}/></Link> : <>
      <SectionTabs labels={["This week", "Full schedule", "How it works"]} title="Your study desk"><section className="topic-plan-all"><h3>This week · {plan.weekly_hours} study hours</h3><p>{plan.topic_minutes} minutes for first-pass sessions; {plan.reserved_minutes} minutes reserved for revisits, mistakes and checkpoints.</p><ol className="plan-topic-queue">{topics.filter(t => t.week === 1).map(t => <li key={t.topic_id}><button type="button" aria-pressed={focus?.topic_id === t.topic_id} onClick={() => chooseTopic(t)}><span><small>{subjects[t.subject]} · {t.chapter}</small><strong>{t.topic}</strong><small>{t.reason}</small></span><ArrowRight size={16}/></button></li>)}</ol><p>Choose a topic to update the practice session above. The order may change after your next test.</p></section>
      <section className="topic-plan-all"><h3>Your full topic schedule</h3><p>{plan.timeline_note}</p><p>{plan.capacity_note}</p>{Array.from(new Set(topics.map(t => t.week))).map(week => <details key={week} className="plan-week"><summary>Week {week}{topics.find(t => t.week === week)?.within_horizon ? '' : ' · beyond current horizon'}</summary><ol className="plan-topic-queue">{topics.filter(t => t.week === week).map(t => <li key={t.topic_id}><strong>{subjects[t.subject]} · {t.topic}</strong><p>{t.reason}</p><details><summary>Study steps & checkpoint</summary><ol>{t.steps.map(step => <li key={step}>{step}</li>)}</ol><p>{t.check}</p><p>{evidence(t)}</p>{t.bank_note && <p>{t.bank_note}</p>}</details></li>)}</ol></details>)}</section>
      <section className="topic-plan-all"><h3>A plan that learns from your answers</h3><p>{plan.goal_explanation}</p><p>Errors, forgotten topics and slow correct answers change your next steps after each submitted test. Completed checkpoints can need another check when evidence becomes stale. Later weeks are provisional; completing a session does not automatically complete a milestone.</p><p>{plan.method}</p><p>Topic practice guides what to study. Balanced assessments demonstrate marks progress; following the plan cannot guarantee a score or admission.</p></section></SectionTabs>
      <Link className="topic-plan-full" to="/subject-test">Choose a different practice focus <ArrowRight size={16}/></Link>
    </>}
  </section>
}

