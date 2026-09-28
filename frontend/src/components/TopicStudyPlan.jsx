import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { ArrowRight, Check, Clock3 } from 'lucide-react'
import { subjectTestBuilderService } from '../lib/subjectTests.js'
import './topic-study-plan.css'

const subjects = { PHY: 'Physics', CHEM: 'Chemistry', MATH: 'Mathematics' }
export default function TopicStudyPlan({ data, compact = false, onStartMission, missionBusy = false, afterTest = false, preferredSubject, preferredChapter }) {
  const plan = data.topic_plan
  const navigate = useNavigate()
  const [busy, setBusy] = useState(false), [error, setError] = useState('')
  if (!plan) return null
  const topics = plan.topics.filter(t => (!preferredSubject || t.subject === preferredSubject) && (!preferredChapter || String(t.chapter_id) === String(preferredChapter)))
  const today = topics[0]
  async function start(topic) {
    const options = { mission: true, assessment: false, subjectCode: topic.subject, chapterId: topic.chapter_id, topicId: topic.topic_id, durationMinutes: 15, mode: 'recommended' }
    setBusy(true); setError('')
    try {
      if (onStartMission) await onStartMission(options)
      else { const paper = await subjectTestBuilderService.start(options); navigate('/recommendations', { state: { missionTest: paper } }) }
    } catch (e) { setError(e.message) } finally { setBusy(false) }
  }
  const evidence = topic => topic.accuracy == null ? 'Not assessed yet' : `${topic.accuracy}% correct · ${topic.fresh_answers} fresh answers · ${topic.study_days} study days`
  const topicRow = (topic, index) => <li key={topic.topic_id} className="topic-plan-row"><span className="topic-plan-index">{index + 1}</span><div><small>{subjects[topic.subject]} · {topic.chapter}</small><h3>{topic.topic}</h3><p><strong>{topic.action}.</strong> {topic.reason}</p><details><summary>What to do & how to pass the checkpoint</summary><ol>{topic.steps.map(step => <li key={step}>{step}</li>)}</ol><p>{topic.check}</p><p>{evidence(topic)}</p><p>{topic.foundation_met ? '✓ Foundation checkpoint met' : 'Foundation checkpoint still open'} · {topic.retention_met ? '✓ Retention check met' : 'Retention check still open'}</p>{topic.prerequisites.length > 0 && <p>Work on these first: {topic.prerequisites.join(', ')}. They appear earlier in your plan.</p>}{topic.bank_note && <p>{topic.bank_note}</p>}</details></div><button className="btn btn-secondary btn-sm" disabled={busy || missionBusy} onClick={() => start(topic)}>Practise <ArrowRight size={14}/></button></li>
  return <section className="topic-plan" aria-label="Your topic-by-topic study plan">
    <div className="topic-plan-goal"><div><span className="topic-plan-label">YOUR DESTINATION</span><h2>{plan.goal}</h2>{data.destinations?.length > 0 && <p>{data.destinations.map(c => `${c.institute} · ${c.program}`).join(' / ')}</p>}</div><div><small>Current assessment evidence</small><strong>{plan.score_range ? `${plan.score_range[0]}–${plan.score_range[1]} / 300` : plan.score != null ? `${plan.score} / 300` : 'Starting point needed'}</strong><small>{plan.score_range ? 'Observed range across 3 recent assessments' : plan.score != null ? 'Baseline score; more separate-day assessments needed for a range' : 'Topic practice cannot establish your JEE score'}</small></div></div>
    <p className="topic-plan-explanation">{plan.goal_explanation}</p>
    {afterTest && <div className="topic-plan-update" role="status"><Check size={18}/><div><strong>Your next step has been recalculated.</strong><p>{today ? `${today.topic}: ${today.reason}` : 'Your submitted answers are saved. Check back when more topic questions are available.'}</p></div></div>}
    {error && <p role="alert" className="alert">{error}</p>}
    {today ? <article className="topic-plan-today"><div><span className="topic-plan-label">TODAY · {today.minutes} MINUTES</span><small>{subjects[today.subject]} → {today.chapter}</small><h2>{today.topic}</h2><p>{today.reason}</p><ol>{today.steps.map(step => <li key={step}>{step}</li>)}</ol><button className="btn btn-primary" disabled={busy || missionBusy} onClick={() => start(today)}>{busy || missionBusy ? 'Preparing your topic…' : `Start ${today.topic}`}<ArrowRight size={17}/></button></div><aside><span className="topic-plan-label">HOW YOU MOVE FORWARD</span><h3>{today.foundation_met ? 'Keep it reliable over time.' : 'Build reliable answers first.'}</h3><p>{today.foundation_met ? 'Return after at least 3 days. Answer 4 fresh questions with at least 3 correct to check retention.' : 'Answer at least 8 fresh questions across 2 study days, with 70% correct.'}</p><details><summary>All checkpoint requirements</summary><p>{today.check}</p></details><strong>{evidence(today)}</strong><p>{today.foundation_met ? 'Foundation met. Next, validate retention and application.' : 'Meet the foundation check before treating this topic as reliable.'}</p>{today.bank_note && <small>{today.bank_note}</small>}<small>Use your notes for the concept review. The practice button opens questions from this exact topic.</small></aside></article> : <div className="topic-plan-update"><p>No complete question sets are available for this selection yet. Choose another subject or chapter below.</p></div>}
    <div className="topic-plan-week-head"><div><span className="topic-plan-label">THIS WEEK</span><h2>Your next topics, in order</h2></div><span><Clock3 size={15}/>{plan.weekly_hours} hours available</span></div>
    <p className="topic-plan-explanation">{plan.topic_minutes} minutes for first-pass topic sessions; {plan.reserved_minutes} minutes reserved for revisits, error review and checkpoints. A difficult topic may need more than one session.</p>
    {!topics.some(t => t.week === 1) && <p>This selection is later in your full plan. You can work ahead using the topic session above.</p>}<ol className="topic-plan-list">{topics.filter(t => t.week === 1).slice(0, compact ? 3 : plan.week.length).map(topicRow)}</ol>
    {!plan.assessment_count && <div className="topic-plan-assessment"><div><strong>Find your exam starting point.</strong><p>When you have a 3-hour block, take a balanced assessment. Replace other study time that week; don’t add it on top.</p></div><Link className="btn btn-secondary" to="/recommendations?assessment=1">Take baseline <ArrowRight size={15}/></Link></div>}
    {compact ? <Link className="topic-plan-full" to="/roadmap">See all topics and the path to exam day <ArrowRight size={16}/></Link> : <>
      <div className="topic-plan-week-head"><div><span className="topic-plan-label">FROM HERE TO YOUR GOAL</span><h2>How the work turns into progress</h2></div></div>
      <ol className="topic-plan-phases">{plan.phases.map((phase, i) => <li key={phase.title}><span className="topic-plan-index">{i + 1}</span><div><small>{phase.when}</small><h3>{phase.title}</h3><p>{phase.action}</p><strong>Move forward when:</strong><p>{phase.check}</p></div></li>)}</ol>
      <details className="topic-plan-all"><summary>See your full topic order ({plan.topics.length} topics)</summary><p>{plan.timeline_note}</p><p>{plan.capacity_note}</p>{Array.from(new Set(plan.topics.map(t => t.week))).map(week => <section key={week}><h3>Week {week}{plan.topics.find(t => t.week === week)?.within_horizon ? '' : ' · beyond current horizon'}</h3><ol className="topic-plan-list">{plan.topics.filter(t => t.week === week).map((t) => topicRow(t, t.order - 1))}</ol></section>)}</details>
      <details className="topic-plan-all"><summary>Why this order, and what changes after a test</summary><p>Repeated errors come first, followed by overdue recall, slow correct answers and topics needing more evidence. Subjects are interleaved. Where an explicit prerequisite exists in our catalog map, its unfinished topics come first.</p><p>Every submitted test updates the evidence. Stronger topics move toward application and retention; weaker or forgotten topics return to review. Future weeks are a provisional first pass, not fixed completion promises.</p><p>{plan.method}</p></details>
    </>}
  </section>
}
