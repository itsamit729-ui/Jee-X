import { useEffect, useId, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { ArrowRight, ArrowUpRight, Check, Flag, RefreshCw, Clock3, Play, MoveUpRight, Compass } from 'lucide-react'
import { request } from '../lib/api.js'
import { subjectTestBuilderService } from '../lib/subjectTests.js'
import { requestFullscreen } from '../lib/fullscreen.js'
import './goal-journey.css'

const subjects = { PHY: 'Physics', CHEM: 'Chemistry', MATH: 'Mathematics' }
const labels = { baseline: 'Find your level', foundation: 'Secure the basics', application: 'Think independently', fluency: 'Find your pace', retention: 'Make it stick', mocks: 'Build consistency', goal: 'Reach your goal' }
const positions = [[9,68,20,7],[32,68,69,20],[32,24,27,33],[55,24,70,46],[55,68,27,59],[79,68,69,72],[88,20,43,86]]
const status = { met: 'Evidence met', current: 'You are here', upcoming: 'Ahead of you', recheck: 'Ready for a recheck' }
const when = value => new Date(value.includes('T') ? `${value.replace(/Z$/, '')}Z` : `${value}T12:00:00`).toLocaleDateString('en-IN', { day: 'numeric', month: 'short' })

function JourneyMap({ data, selected, onSelect, detailId, afterTest }) {
  return <div className={`journey-map ${afterTest ? 'journey-map-updated' : ''}`}>
    <div className="journey-map-caption"><Compass size={16}/><span>Your route is personal.<br/><strong>Explore any stop.</strong></span></div>
    <svg className="journey-route journey-route-wide" viewBox="0 0 1000 400" preserveAspectRatio="none" aria-hidden="true"><path d="M90 272 H280 Q320 272 320 232 V136 Q320 96 360 96 H510 Q550 96 550 136 V232 Q550 272 590 272 H750 Q790 272 805 232 L880 80"/></svg>
    <svg className="journey-route journey-route-mobile" viewBox="0 0 1000 1000" preserveAspectRatio="none" aria-hidden="true"><path d="M200 70 C200 120 690 150 690 200 S270 280 270 330 S700 410 700 460 S270 540 270 590 S690 670 690 720 S430 810 430 860"/></svg>
    <ol className="journey-stops" aria-label="Your milestone map">{data.milestones.map((m, i) => {
      const [x,y,mx,my] = positions[i]
      return <li key={m.id} style={{ '--stop-x': `${x}%`, '--stop-y': `${y}%`, '--mobile-x': `${mx}%`, '--mobile-y': `${my}%` }}><button className={`journey-stop is-${m.status} ${selected === m.id ? 'is-selected' : ''}`} aria-label={`${m.number}. ${m.title}. ${status[m.status]}`} aria-pressed={selected === m.id} aria-current={data.active_id === m.id ? 'step' : undefined} aria-controls={detailId} onClick={() => onSelect(m.id)}><span className="journey-stop-dot">{m.met ? <Check size={20}/> : m.id === 'goal' ? <Flag size={20}/> : String(m.number).padStart(2,'0')}</span><strong>{labels[m.id]}</strong>{data.active_id === m.id && <small>You are here</small>}{m.status === 'recheck' && <small>Recheck</small>}</button></li>
    })}</ol>
    <span className="journey-map-footnote">Learning milestones · not an admission probability</span>
  </div>
}

function ProgressStory({ data }) {
  const history = data.assessment_history || []
  const first = history[0], latest = history.at(-1)
  const comparable = history.length >= 2 && first.date.slice(0,10) !== latest.date.slice(0,10)
  const delta = comparable ? latest.score-first.score : null
  const met = data.milestones.filter(m => m.met).length
  const anchor = data.saved ? data.starting_snapshot : null
  return <section className="journey-story" aria-label="Me then versus me now">
    <div><span className="journey-eyebrow">ME THEN / ME NOW</span><h3>Look back.<br/>{' '}<em>See what changed.</em></h3><p>{comparable ? 'Two recorded checkpoints. Your own progress, without the guesswork.' : 'Your story starts with a checkpoint. Come back after another assessment to see what has changed.'}</p></div>
    <div className="journey-score-story"><div className="journey-score-pair"><div><span>{first ? `Earlier · ${when(first.date)}` : 'Earlier checkpoint'}</span><strong>{first?.score ?? '—'}<small>/ 300</small></strong></div><ArrowRight size={22}/><div><span>{comparable ? `Latest · ${when(latest.date)}` : 'Next checkpoint'}</span><strong>{comparable ? latest.score : '—'}<small>/ 300</small></strong></div></div>
      {comparable ? <p className="journey-score-caption">{delta > 0 ? `+${delta} marks between these assessments` : delta < 0 ? `${delta} marks — a signal to revisit your next steps` : 'The same score — keep working on consistency'}. Generated balanced papers can differ in difficulty; this is an observed comparison.</p> : <Link to="/recommendations?assessment=1">Take a balanced checkpoint <ArrowUpRight size={14}/></Link>}
      <div className="journey-earned"><span><strong>{data.new_foundation_chapters ?? 0}</strong> new chapters with foundation evidence</span><span><strong>{anchor?.milestones_met ?? met} → {met}</strong> milestones with current evidence</span></div><small>{anchor ? `Since your saved snapshot on ${when(anchor.date)}. Older evidence can expire.` : 'Save your goal to keep a starting snapshot.'}</small>
    </div>
  </section>
}

export function JourneyPanel({ data, compact = false, afterTest = false, onStartMission, missionBusy = false, preferredSubject, preferredChapter }) {
  const navigate = useNavigate()
  const detailId = useId()
  const [selected, setSelected] = useState(data.active_id)
  const [destinationId, setDestinationId] = useState(null)
  const [subject, setSubject] = useState('ALL')
  const [launching, setLaunching] = useState(false)
  const [launchError, setLaunchError] = useState('')
  useEffect(() => { setSelected(data.active_id) }, [data.active_id, data.last_attempt_id])
  const active = data.milestones.find(m => m.id === data.active_id)
  const inspected = data.milestones.find(m => m.id === selected) || active
  const choices = data.destinations || []
  const destination = choices.find(c => c.id === destinationId) || choices[0]
  const focus = data.focus.filter(s => subject === 'ALL' || s.subject === subject)
  const mission = data.focus.find(s => preferredChapter ? String(s.chapter_id) === String(preferredChapter) : preferredSubject && s.subject === preferredSubject) || (!preferredSubject ? data.focus[0] : null)
  const missionTitle = mission ? ({ revisit_weak_concept: 'Turn a weak spot into a strength.', spaced_revision: 'See what stayed with you.', build_fluency: 'Find a faster way through.', stretch: 'Ready for a harder application?', build_evidence: 'Find your next breakthrough.' }[mission.reason_code]) : 'Find your next breakthrough.'
  const busy = launching || missionBusy
  async function launch() {
    if (busy) return
    setLaunching(true); setLaunchError('')
    const options = { mission: true, assessment: false, subjectCode: preferredSubject || mission?.subject || '', chapterId: preferredChapter ? Number(preferredChapter) : mission?.chapter_id || null, durationMinutes: 15, mode: 'recommended' }
    try {
      if (onStartMission) {
        if (!await onStartMission(options)) throw new Error('Your mission could not start. Try again or choose another focus below.')
      } else {
        requestFullscreen()
        const created = await subjectTestBuilderService.start(options)
        navigate('/recommendations', { state: { missionTest: created } })
      }
    } catch (e) { setLaunchError(e.message) }
    finally { setLaunching(false) }
  }
  const debrief = <div className={`journey-debrief ${afterTest ? 'is-new' : ''}`}><div><RefreshCw size={18}/><span className="journey-eyebrow">{afterTest ? 'WHAT YOUR TEST CHANGED' : 'YOUR LATEST CHAPTER'}</span></div><ul>{data.changes.map((text,i) => <li key={i}>{text}</li>)}</ul></div>
  return <section className={`goal-journey ${compact ? 'journey-compact' : ''}`} aria-label="Your personal goal journey">
    <header className="journey-destination"><div><span className="journey-eyebrow">{afterTest ? 'YOUR NEXT CHAPTER' : 'THE DESTINATION IS YOURS'}</span><h2>{!data.saved ? <>A goal worth<br/><em>showing up for.</em></> : destination ? destination.institute : <><span className="journey-target-number">{data.standing.target}</span> marks.<br/><em>One step closer.</em></>}</h2><p>{destination ? destination.program : data.saved ? 'Today’s work belongs to a bigger story. This is yours.' : 'Choose a marks target or up to three college and branch choices.'}</p></div><div className="journey-destination-meta"><span><Flag size={15}/> {data.target_year} JEE MAIN</span>{data.standing.score != null ? <strong>{data.standing.score}<small> / 300 current baseline</small></strong> : <strong>Your starting point<br/><small>is still taking shape</small></strong>}{data.standing.gap != null && <span>{data.standing.gap} marks between your baseline and goal</span>}{data.exam_date && <span>Exam date · {when(data.exam_date)}</span>}{!data.saved && <Link to="/roadmap">Set my goal <ArrowRight size={14}/></Link>}</div></header>
    {choices.length > 1 && <div className="journey-destinations" role="group" aria-label="Explore your college destinations">{choices.map((c,i) => <button key={c.id} aria-pressed={destination?.id === c.id} onClick={() => setDestinationId(c.id)}><span>CHOICE 0{i+1}</span>{c.institute}</button>)}</div>}
    {destination && <p className="journey-college-benchmark">{destination.rank ? `${destination.year} reference · ${destination.rank_list} closing rank ${Number(destination.rank).toLocaleString('en-IN')} · ${destination.quota} / ${destination.seat_type}` : 'Add your eligibility details on the roadmap to resolve this choice’s historical benchmark.'} <Link to="/roadmap#college-outlook">Explore college outlook <ArrowUpRight size={13}/></Link><small>Historical reference, not an admission guarantee. Switching destinations explores your saved choices; it does not change your goal.</small></p>}
    {afterTest && debrief}
    <div className="journey-expedition" id="milestones"><div className="journey-map-panel"><div className="journey-map-toolbar"><span className="journey-eyebrow">YOUR LEARNING ROUTE</span><span><i/>{data.milestones.filter(m => m.met).length} / 7 stops with evidence</span></div><JourneyMap data={data} selected={selected} onSelect={setSelected} detailId={detailId} afterTest={afterTest}/><div className="journey-inspector" id={detailId} aria-live="polite"><div className="journey-inspector-heading"><span className="journey-eyebrow">STOP 0{inspected.number} / {status[inspected.status]}</span>{selected !== data.active_id && <button onClick={() => setSelected(data.active_id)}>Back to my next step</button>}</div><h3>{inspected.title}</h3><p>{inspected.purpose}</p><details key={inspected.id}><summary>{inspected.progress} <span>What completes this stop?</span></summary><p>{inspected.requirement}</p>{inspected.first_met_at && <small>First achieved {when(inspected.first_met_at)}; current evidence is checked again as it ages.</small>}</details></div></div>
      <aside className="journey-mission"><div className="journey-mission-top"><span className="journey-eyebrow">TODAY’S MISSION</span><MoveUpRight size={25}/></div><span className="journey-mission-subject">{subjects[preferredSubject || mission?.subject] || 'A little of every subject'}</span><h3>{missionTitle}</h3><p>{mission?.reason || 'Try a fresh session to help us discover what you understand and where you need support.'}</p><div className="journey-mission-topic"><span>YOUR FOCUS</span><strong>{mission?.title || (preferredChapter ? 'Your selected chapter' : preferredSubject ? subjects[preferredSubject] : 'Build your practice evidence')}</strong><small>Works toward: {labels[active.id]}</small></div><div className="journey-mission-time"><Clock3 size={17}/><span>About 15 minutes · up to 8 questions</span></div><button className="btn btn-primary" disabled={busy} onClick={launch}>{busy ? 'Preparing your mission…' : afterTest ? 'Start my next mission' : 'Start my mission'}{!busy && <Play size={16}/>}</button>{launchError && <p className="journey-mission-error" role="alert">{launchError}</p>}<p className="journey-mission-note">Finish with explanations and an updated next step.</p>{['baseline','mocks','goal'].includes(active.id) && <Link className="journey-assessment-link" to="/recommendations?assessment=1">{active.id === 'baseline' ? 'Establish my exam baseline' : 'Take a full checkpoint'} <ArrowUpRight size={14}/><small>75 questions · allow 3 hours</small></Link>}{compact && <Link className="journey-assessment-link" to="/roadmap">Open my full roadmap <ArrowRight size={14}/></Link>}</aside>
    </div>
    {!afterTest && debrief}
    <ProgressStory data={data}/>
    {!compact && <>
      <div className="journey-section-head"><div><span className="journey-eyebrow">OTHER THREADS IN YOUR STORY</span><h3>A little attention here goes a long way.</h3></div><div className="journey-filters" role="group" aria-label="Filter priorities by subject">{['ALL',...Object.keys(subjects)].map(s => <button key={s} aria-pressed={subject === s} onClick={() => setSubject(s)}>{subjects[s] || 'All'}</button>)}</div></div>
      <div className="journey-focus-list">{focus.map((s,i) => <Link key={s.chapter_id} to={`/recommendations?subject=${s.subject}&chapter=${s.chapter_id}`}><span className="journey-focus-index">0{i+1}</span><div><span className="journey-eyebrow">{subjects[s.subject]}</span><h4>{s.title}</h4><p>{s.reason}</p></div><span className="journey-focus-accuracy"><strong>{s.accuracy}%</strong><small>{s.answered} fresh answers</small></span><ArrowUpRight size={20}/></Link>)}</div>{!focus.length && <p className="journey-note">Your chapter priorities will take shape as you practise this subject.</p>}
      <details className="journey-method"><summary>How your route adapts</summary><p>{data.evidence_note}</p><p>{data.timeline_note} Evidence updates after each submitted test when you open your plan. Weekly work refreshes after three submitted sessions or seven days.</p></details>
      {data.history.length > 0 && <details className="journey-method"><summary>Your journey log</summary><ol>{[...data.history].reverse().map((h,i) => <li key={i}><strong>{when(h.date)}</strong><p>{h.messages.join(' ')}</p></li>)}</ol></details>}
    </>}
  </section>
}

export default function GoalJourney({ afterTest = false, attemptId, ...props }) {
  const [data,setData] = useState(null), [error,setError] = useState(''), [retry,setRetry] = useState(0)
  useEffect(() => {
    let active = true
    setError('');setData(null)
    request('/api/roadmap/journey',{cache:false}).then(value => {if(active)setData(value)}).catch(e=>{if(active)setError(e.message)})
    return ()=>{active=false}
  },[attemptId,retry])
  if(error)return <div className="journey-loading" role="alert">We couldn’t load your route. Your practice is still available below.<button className="btn btn-secondary" onClick={()=>setRetry(v=>v+1)}>Retry</button></div>
  if(!data)return <div className="journey-loading" role="status"><Compass size={20}/>Finding your next step…</div>
  return <JourneyPanel data={data} compact afterTest={afterTest} {...props}/>
}
