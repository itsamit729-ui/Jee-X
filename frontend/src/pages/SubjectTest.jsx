import { useEffect, useRef, useState } from 'react'
import { Link, useNavigate, useSearchParams, useLocation } from 'react-router-dom'
import { ArrowLeft, ArrowUpRight, Target, Compass, RotateCcw, Clock3, ArrowRight, Check, BookOpen, ChevronDown } from 'lucide-react'
import { catalogService, subjectTestBuilderService, subjectTestGraderService } from '../lib/subjectTests.js'
import MathText from '../components/MathText.jsx'
import QuestionAssets from '../components/QuestionAssets.jsx'
import GoalJourney from '../components/GoalJourney.jsx'
import AppHeader from '../components/AppHeader.jsx'
import Palette from '../components/Palette.jsx'
import RankPredictor from '../components/RankPredictor.jsx'
import MhtExam from '../components/MhtExam.jsx'
import MhtCollegePredictor from '../components/MhtCollegePredictor.jsx'
import { cetCanAnswer } from '../lib/mhtExam.js'
import FullscreenGuard from '../components/FullscreenGuard.jsx'
import { requestFullscreen, exitFullscreen, useFullscreenLock } from '../lib/fullscreen.js'
import { GOOD, BAD, PEN, SUBJECT_COLOR } from '../crackjee/ui.js'

import { archiveReturn, resultAnswer } from '../lib/pyqArchive.js'
import { createPracticeTimer } from '../lib/practiceTimer.js'
import useTestPreparation from '../hooks/useTestPreparation.js'
import TestInstructions from '../components/TestInstructions.jsx'
import TestSession from '../components/TestSession.jsx'
import ChapterPicker from '../components/ChapterPicker.jsx'
import { invalidateCache } from '../lib/requestCache.js'
import './practice.css'

const OUTCOME = { correct: 'correct', wrong: 'wrong' }

export default function SubjectTest({ initialMode = 'recommended', fullMock: forceFullMock = false }) {
  const navigate = useNavigate()
  const location = useLocation()
  const [searchParams] = useSearchParams()
  const fullMock=forceFullMock||searchParams.get('mock')==='1'
  const requestedSubject = searchParams.get('subject')
  const requestedChapter = searchParams.get('chapter')
  const pyq = ['jee_main', 'bitsat', 'mht_cet'].includes(searchParams.get('pyq'))
  const pyqReturn = archiveReturn(searchParams)
  const assessment = fullMock || searchParams.get('assessment') === '1'
  const handedPaper = location.state?.instructionsComplete ? location.state?.missionTest : null
  const preparation = useTestPreparation(location.state?.missionTest && !location.state?.instructionsComplete ? { paper: location.state.missionTest, details: { exam: searchParams.get('pyq') || 'jee_main', pyq: Boolean(pyq), mock: location.state.missionTest.is_mock } } : null)
  const [deadline, setDeadline] = useState(() => handedPaper?.is_mock ? Date.now() + handedPaper.duration_sec * 1000 : null)
  const [remaining, setRemaining] = useState(10800)
  const [startedAt,setStartedAt]=useState(Date.now)
  const [elapsed,setElapsed]=useState(0)
  const [questionSeconds,setQuestionSeconds]=useState(0)
  const timeoutSubmitted = useRef(false)


  const [subjects, setSubjects] = useState(null) // null = loading
  const [chapters, setChapters] = useState([])
  const [chaptersLoading, setChaptersLoading] = useState(false)
  const [subjectCode, setSubjectCode] = useState('')
  const [chapterId, setChapterId] = useState('')
  const [durationMinutes, setDurationMinutes] = useState(15)
  const [mode, setMode] = useState(requestedSubject ? 'topic' : initialMode)
  const timer = useRef(createPracticeTimer())
  const [error, setError] = useState('')
  const [starting, setStarting] = useState(false)
  const [loadVersion, setLoadVersion] = useState(0)
  const [showPlanSuggestion, setShowPlanSuggestion] = useState(false)

  const [test, setTest] = useState(() => handedPaper) // { attempt_id, questions, ... }
  const mhtMock = searchParams.get('pyq') === 'mht_cet' && Boolean(test?.is_mock)
  const timed = assessment || Boolean(test?.is_mock)
  const [index, setIndex] = useState(0)
  const [answers, setAnswers] = useState({}) // question_id -> { option_ids, numeric_answer }
  const [submitting, setSubmitting] = useState(false)
  const [result, setResult] = useState(null)
  const submissionInFlight = useRef(false)
  const fullscreen = useFullscreenLock(Boolean(test) && !result, () => submitTest())

  useEffect(() => {
    let active = true
    setError('')
    catalogService.listSubjects()
      .then(data => { if (active) setSubjects(data) })
      .catch(e => { if (active) { setError(e.message); setSubjects([]) } })
    return () => { active = false }
  }, [loadVersion])

  useEffect(() => {
    if (!subjects || !requestedSubject) return
    const match = subjects.find(s => s.code === requestedSubject || s.name?.toLowerCase() === requestedSubject.toLowerCase())
    if (match) setSubjectCode(match.code)
  }, [subjects, requestedSubject])

  useEffect(() => {
    let active = true
    setChapters([])
    setChapterId('')
    setError('')
    setChaptersLoading(Boolean(subjectCode))
    if (!subjectCode) return
    catalogService.listChapters(subjectCode)
      .then(data => { if (active) { setChapters(data); if (data.some(c => String(c.id) === requestedChapter)) setChapterId(requestedChapter) } })
      .catch(e => { if (active) setError(e.message) })
      .finally(() => { if (active) setChaptersLoading(false) })
    return () => { active = false }
  }, [subjectCode, loadVersion])

  useEffect(() => {
    if (!test || result || submitting) return
    const id = test.questions[index]?.question_id
    const update = () => timer.current.activate(id, document.visibilityState === 'visible' && document.hasFocus())
    update()
    document.addEventListener('visibilitychange', update)
    window.addEventListener('focus', update)
    window.addEventListener('blur', update)
    return () => {
      timer.current.pause()
      document.removeEventListener('visibilitychange', update)
      window.removeEventListener('focus', update)
      window.removeEventListener('blur', update)
    }
  }, [test, index, result, submitting])

  useEffect(() => {
    if (timed && test && !result && remaining === 0 && !submitting && !timeoutSubmitted.current) {
      timeoutSubmitted.current = true
      submitTest()
    }
  }, [remaining, timed, test, result, submitting])

  useEffect(() => {
    if (location.state?.missionTest) navigate(location.pathname + location.search, { replace: true, state: null })
  }, [])

  const startTest = async (options) => {
    const mission = options?.mission === true ? options : null
    setError('')
    setStarting(true)
    try {
      return await preparation.open(() => subjectTestBuilderService.start({
        assessment: assessment && !fullMock,
        fullMock,
        subjectCode: mission ? mission.subjectCode : assessment ? '' : subjectCode,
        topicId: mission?.topicId || null,
        chapterId: mission ? mission.chapterId : chapterId ? Number(chapterId) : null,
        durationMinutes: mission ? mission.durationMinutes : durationMinutes,
        mode: mission ? mission.mode : mode,
      }), { exam: 'jee_main', mock: assessment, durationMinutes: mission ? mission.durationMinutes : durationMinutes })
    } catch (e) {
      setError(e.message)
      return null
    } finally {
      setStarting(false)
    }
  }

  const enterPreparedTest = () => {
    const created = preparation.enter()
    if (!created) return
    requestFullscreen()
    timeoutSubmitted.current = false
    timer.current.reset()
    setStartedAt(Date.now());setElapsed(0)
    setTest(created)
    setDeadline(created.is_mock || assessment ? Date.now() + created.duration_sec * 1000 : null)
    setRemaining(created.duration_sec)
    setIndex(0); setAnswers({}); setResult(null); setError('')
  }

  useEffect(() => {
    if (!test || result) return
    const tick=()=>{setElapsed(Math.floor((Date.now()-startedAt)/1000));setQuestionSeconds(timer.current.seconds(test.questions[index]?.question_id))}
    tick();const id=setInterval(tick,1000);return()=>clearInterval(id)
  },[test,result,index,startedAt])

  useEffect(() => {
    if (!timed || !test || result || !deadline) return
    const tick = () => setRemaining(Math.max(0, Math.ceil((deadline - Date.now()) / 1000)))
    tick()
    const id = setInterval(tick, 1000)
    return () => clearInterval(id)
  }, [timed, test, result, deadline])

  useEffect(() => {
    if (!timed || !test || result) return
    const warn = event => { event.preventDefault(); event.returnValue = '' }
    window.addEventListener('beforeunload', warn)
    return () => window.removeEventListener('beforeunload', warn)
  }, [timed, test, result])

  const exitTest = () => {
    if (!window.confirm('Leave this test? Your answers will be lost.')) return
    if (pyq) { navigate(pyqReturn); return }
    setTest(null)
    setAnswers({})
    setIndex(0)
  }

  const selectOption = (questionId, optionId) => {
    if (fullscreen.limitReached || submissionInFlight.current || result) return
    if (timed && remaining <= 0) return
    if (mhtMock && !cetCanAnswer(test.questions.find(q => q.question_id === questionId)?.subject_code, Math.max(0, Math.ceil((deadline - Date.now()) / 1000)))) return
    setAnswers(a=>{const multiple=test.questions.find(q=>q.question_id===questionId)?.type==='multi_correct';const old=a[questionId]?.option_ids||[];return {...a,[questionId]:{option_ids:multiple?(old.includes(optionId)?old.filter(id=>id!==optionId):[...old,optionId]):[optionId]}}})
  }

  const setNumeric = (questionId, value) => {
    if (fullscreen.limitReached || submissionInFlight.current || result) return
    if (timed && remaining <= 0) return
    if (mhtMock && !cetCanAnswer(test.questions.find(q => q.question_id === questionId)?.subject_code, Math.max(0, Math.ceil((deadline - Date.now()) / 1000)))) return
    setAnswers((a) => ({ ...a, [questionId]: { numeric_answer: value === '' ? null : Number(value) } }))
  }

  const submitTest = async () => {
    if (!test || result || submissionInFlight.current) return
    submissionInFlight.current = true
    setError('')
    timer.current.pause()
    setSubmitting(true)
    try {
      const payload = test.questions.map((q) => ({
        question_id: q.question_id,
        option_ids: answers[q.question_id]?.option_ids || [],
        numeric_answer: answers[q.question_id]?.numeric_answer ?? null,
        time_taken_sec: timer.current.seconds(q.question_id),
      }))
      const res = await subjectTestGraderService.submit(test.attempt_id, payload)
      setResult(res)
      invalidateCache()
      window.dispatchEvent(new Event('jee-attempt-submitted'))
      exitFullscreen()
      navigate(`/results/${res.attempt_id}?tab=questions`,{replace:true,state:{submitted:res}})
    } catch (e) {
      setError(e.message)
    } finally {
      submissionInFlight.current = false
      setSubmitting(false)
    }
  }

  const restart = () => { if (pyq) { navigate(pyqReturn); return }; setTest(null); setResult(null); setAnswers({}); setIndex(0) }
  const isAnswered = (q) => {
    const a = answers[q.question_id]
    return Boolean(a && (a.option_ids?.length || (a.numeric_answer !== null && a.numeric_answer !== undefined)))
  }
  const answeredCount = test ? test.questions.filter(isAnswered).length : 0

  useEffect(() => { if (pyq && !test && !preparation.session) navigate(pyqReturn, { replace: true }) }, [pyq, test, Boolean(preparation.session), navigate, pyqReturn])

  // ---------------------------------------------------------------- RESULTS
  if (preparation.session) return <TestInstructions session={preparation.session} onEnter={enterPreparedTest} onCancel={() => { preparation.cancel(); setStarting(false) }} onRetry={preparation.retry}/>

  if (result) {
    return (
      <div className="crackjee-root">
        <AppHeader />
        <main className="test-shell">
          <div className="result-head">
            <div className="score-big">{result.score}<small>marks</small></div>
            <Palette size="lg" states={result.questions.map((r) => OUTCOME[r.outcome] || 'skipped')} label="Your answers" />
            <p className="result-line"><strong>{result.accuracy}%</strong> accuracy across {result.total_questions} questions</p>
          </div>

          {!pyq && <GoalJourney afterTest attemptId={result.attempt_id} onStartMission={assessment ? undefined : startTest} missionBusy={starting}/>}
          {mhtMock && <MhtCollegePredictor attemptId={result.attempt_id} />}
          {(assessment || (test?.is_mock && !pyq)) && <RankPredictor attemptId={result.attempt_id}/>}
          {!assessment && !pyq && !test?.is_mock && <details className="journey-method"><summary>Explore rank and college reference data</summary><RankPredictor attemptId={result.attempt_id}/></details>}

          <div className="panel">
            <h2 className="panel-title">Solutions</h2>
            {result.questions.map((r, i) => (
              <div key={r.question_id} className="solution">
                <div className="solution-head">
                  <span className="sq" data-s={OUTCOME[r.outcome] || 'skipped'} />
                  Question {i + 1}
                  <span className="faint" style={{ fontWeight: 500 }}>{r.ref}</span>
                  <span className="marks" style={{ color: r.marks_awarded > 0 ? GOOD : r.marks_awarded < 0 ? BAD : undefined }}>
                    {r.marks_awarded > 0 ? '+' : ''}{r.marks_awarded}
                  </span>
                </div>
                {test.questions.find(q => q.question_id === r.question_id)?.recommendation && <p className="muted" style={{fontSize:13}}>{test.questions.find(q => q.question_id === r.question_id).recommendation.reason}</p>}
                <p>Correct answer: {resultAnswer(test.questions.find(q => q.question_id === r.question_id), r)}</p>
                <p><MathText text={r.solution || 'Worked solution is not available yet.'} /></p>
              </div>
            ))}
          </div>

          <div className="hero-actions">
            <Link className="btn btn-primary" to={`/results/${result.attempt_id}`}>See full analysis</Link>
            <button type="button" className="btn btn-secondary" onClick={restart}>Start another test</button>
            <button type="button" className="btn btn-secondary" onClick={() => navigate('/dashboard')}>Back to dashboard</button>
          </div>
        </main>
      </div>
    )
  }

  if (mhtMock && test) return <><FullscreenGuard {...fullscreen} onResume={fullscreen.resume} onSubmit={submitTest} submitting={submitting} error={error}/><MhtExam
    test={test} remaining={remaining} index={index} onIndex={setIndex} answers={answers}
    onAnswer={selectOption} onClear={questionId => {
      if (fullscreen.limitReached || submissionInFlight.current || result) return
      if (!cetCanAnswer(test.questions.find(q => q.question_id === questionId)?.subject_code, Math.max(0, Math.ceil((deadline - Date.now()) / 1000)))) return
      setAnswers(a => { const next = { ...a }; delete next[questionId]; return next })
    }} onSubmit={submitTest} onExit={exitTest} submitting={submitting} error={error}/></>

  // One viewport, one question-content scroll area; controls stay visible.
  if (test) return <><FullscreenGuard {...fullscreen} onResume={fullscreen.resume} onSubmit={submitTest} submitting={submitting} error={error}/><TestSession
    test={test} index={index} answers={answers} onIndex={setIndex} onOption={selectOption} onNumeric={setNumeric}
    onClear={id=>{if(submissionInFlight.current||fullscreen.limitReached)return;setAnswers(a=>{const next={...a};delete next[id];return next})}}
    onSubmit={submitTest} onExit={exitTest} submitting={submitting} error={error} timed={timed}
    remaining={remaining} elapsed={elapsed} questionSeconds={questionSeconds}/></>

  if (assessment) return <div className="crackjee-root"><AppHeader /><main className="wrap practice-page">
    <button className="btn btn-quiet" onClick={() => navigate('/plan')}><ArrowLeft size={16}/> My JEE Plan</button>
    <header className="practice-intro"><div><span className="practice-eyebrow">{fullMock ? 'JEE MAIN · FULL MOCK' : 'FIND YOUR STARTING POINT'}</span><h1>{fullMock ? <>The paper. The clock.<br/><em>Your next attempt.</em></> : <>A clear baseline.<br/><em>A better next step.</em></>}</h1><p>75 {fullMock ? 'bank' : 'fresh'} questions across Physics, Chemistry and Mathematics. Give yourself three uninterrupted hours.</p></div></header>
    <section id="practice-builder" className="practice-builder"><div className="practice-controls"><h2>{fullMock ? 'A full exam rehearsal' : 'One honest checkpoint'}</h2><p>Each subject has 20 multiple-choice and 5 numerical questions. Correct: +4 · Incorrect: −1 · Unanswered: 0.</p><p>The timer submits at three hours. Keep this page open; leaving or refreshing ends your local session.</p><p>{fullMock ? 'This mock draws from published questions, prioritising ones you have not answered.' : 'This generated assessment measures your starting point.'} It is not an official or statistically calibrated JEE paper.</p></div><aside className="practice-start"><strong>180 minutes · 300 marks</strong><button className="btn btn-primary" disabled={starting} onClick={startTest}>{starting ? 'Preparing your paper…' : fullMock ? 'Begin full mock' : 'Begin assessment'}</button><small>Your answers are scored on the server.</small></aside></section>
    {error && <p className="alert" role="alert">{error}</p>}
  </main></div>

  const focusLabel = chapters.find(c => String(c.id) === chapterId)?.name || subjects?.find(s => s.code === subjectCode)?.name || (mode === 'topic' ? 'Choose a subject' : 'All subjects')
  const approaches = [
    { key: 'recommended', Icon: Target, title: 'Personalised practice', hint: 'Questions shaped by your recent answers.', detail: 'Questions are selected using your recent answers and study priorities. If you’re new, your first set helps find your starting point.' },
    { key: 'topic', Icon: Compass, title: 'Choose a chapter', hint: 'Pick a subject or focus on one chapter.', detail: 'Pick a subject, then narrow it to a chapter. You’ll get a focused set from the available question bank.' },
    { key: 'revision', Icon: RotateCcw, title: 'Revise & remember', hint: 'Revisit concepts you’ve practised before.', detail: 'Revisit previously practised concepts. If there isn’t enough history yet, we include questions to establish a starting point.' },
  ]
  const approach = approaches.find(item => item.key === mode)
  const questionLimit = { 5: 3, 15: 8, 30: 16 }[durationMinutes]
  // ---------------------------------------------------------------- SETUP
  return <div className="crackjee-root"><AppHeader />
    <main className="wrap practice-page practice-setup">
      <header className="practice-welcome">
        <div><span className="practice-eyebrow"><span className="practice-live-dot"/> JEE QUESTION PRACTICE</span>
          <h1><span className="practice-desktop-only">Practise questions. <em>Learn from every answer.</em></span><span className="practice-mobile-only">A little practice.<br/><em>A little progress.</em></span></h1>
          <p>Short question sets, at your pace. Review your answers and solutions when you finish.</p>
        </div>
        <Link className="practice-paper-link" to="/pyq"><BookOpen size={19}/><span>Want an exam paper?<strong>Explore PYQs & mocks <ArrowUpRight size={14}/></strong></span></Link>
      </header>

      <div className="practice-studio">
        <section className="practice-config" aria-labelledby="practice-config-title">
          <div className="practice-section-heading"><span className="practice-number">01</span><h2 id="practice-config-title">What do you want to work on?</h2></div>
          <div className="practice-mobile-only practice-mobile-field">
            <label htmlFor="practice-approach">Practice type</label>
            <select id="practice-approach" className="input" value={mode} disabled={starting} aria-describedby="practice-mode-description" onChange={e => setMode(e.target.value)}>{approaches.map(item => <option key={item.key} value={item.key}>{item.title}</option>)}</select>
          </div>
          <div className="practice-choices" role="group" aria-label="Practice approach">
            {approaches.map(({key, Icon, title, hint}) => <button key={key} type="button" className={`practice-choice ${mode === key ? 'is-active' : ''}`} disabled={starting} aria-pressed={mode === key} aria-describedby="practice-mode-description" onClick={() => setMode(key)}>
              <span className="practice-choice-icon"><Icon size={20}/></span><span className="practice-choice-copy"><strong>{title}</strong><small>{hint}</small></span><span className="practice-choice-check" aria-hidden="true">{mode === key && <Check size={12}/>}</span>
            </button>)}
          </div>
          <p id="practice-mode-description" className="practice-mode-description" aria-live="polite"><span className="practice-desktop-only">{approach.detail}</span><span className="practice-mobile-only">{approach.hint}</span></p>

          <fieldset className="practice-focus-fields" disabled={starting}>
            <legend>Choose your focus <span>{mode === 'topic' ? 'Select a subject to begin' : 'Optional · keep all subjects for a mixed set'}</span></legend>
            <div className="practice-mobile-only practice-mobile-field">
              <label htmlFor="practice-subject">Subject</label>
              <select id="practice-subject" className="input" value={subjectCode} disabled={subjects === null} onChange={e => setSubjectCode(e.target.value)}>
                <option value="" disabled={mode === 'topic'}>{subjects === null ? 'Loading subjects…' : mode === 'topic' ? 'Choose a subject' : 'All subjects'}</option>
                {subjects?.map(s => <option key={s.code} value={s.code}>{s.name}</option>)}
              </select>
            </div>
            <div className="practice-focus-options" role="group" aria-label="Subject">
              {mode !== 'topic' && <button type="button" aria-pressed={!subjectCode} onClick={() => setSubjectCode('')}>All subjects</button>}
              {subjects === null ? <span role="status" className="practice-loading-subjects">Loading subjects…</span> : subjects.map(s => <button key={s.code} type="button" aria-pressed={subjectCode === s.code} onClick={() => setSubjectCode(s.code)}>{s.name}</button>)}
            </div>
            {subjectCode && <div className="practice-chapter-field"><span className="practice-chapter-label">Chapter</span>
              <ChapterPicker key={subjectCode} chapters={chapters} value={chapterId} loading={chaptersLoading} onChange={setChapterId}/>
              {chaptersLoading && <span role="status">Loading chapters…</span>}
            </div>}
          </fieldset>

          <div className="practice-section-heading practice-size-heading"><span className="practice-number">02</span><div><h2>How much time do you have?</h2><p>This sizes your question set. There’s no countdown.</p></div></div>
          <div className="practice-size-options" role="group" aria-label="Session length">
            {[[5,3,'Quick reset'],[15,8,'Focused session'],[30,16,'Longer practice']].map(([minutes,count,label]) => <button key={minutes} type="button" disabled={starting} aria-pressed={durationMinutes === minutes} onClick={() => setDurationMinutes(minutes)}><span>{label}</span><strong>{minutes}<small> min</small></strong><span>Up to {count} questions</span></button>)}
          </div>
        </section>

        <aside className="practice-ticket" aria-labelledby="practice-ticket-title">
          <p className="practice-mobile-only practice-mobile-summary" aria-live="polite">Up to {questionLimit} questions <span>· Self-paced</span></p>
          <div className="practice-ticket-top"><span className="practice-eyebrow">YOUR NEXT SESSION</span><span className="practice-self-paced"><Clock3 size={12}/> Self-paced</span></div>
          <h2 id="practice-ticket-title">{approach.title}</h2>
          <div className="practice-ticket-quantity" aria-live="polite"><div><span>UP TO</span><strong key={questionLimit}>{questionLimit}<small> questions</small></strong></div><span className="practice-ticket-estimate">About<br/><b>{durationMinutes} minutes</b></span></div>
          <div className="practice-ticket-focus"><span>YOUR FOCUS</span><strong aria-live="polite">{focusLabel}</strong></div>
          <div className="practice-ticket-outcome"><h3>Finish with more than a score</h3><ul><li><Check size={14}/> Your score and accuracy</li><li><Check size={14}/> Answer keys and available solutions</li><li><Check size={14}/> Results that inform your next practice</li></ul></div>
          <button type="button" className="btn btn-primary" disabled={starting || chaptersLoading || (mode === 'topic' && !subjectCode)} onClick={startTest}>{starting ? <><span className="spin" aria-hidden="true"/> Preparing your set…</> : <>Start practice <ArrowRight size={18}/></>}</button>
          <p className="practice-ticket-note" role={starting ? 'status' : undefined}>{starting ? 'Selecting available questions for your chosen focus.' : mode === 'topic' && !subjectCode ? 'Select a subject to start chapter practice.' : 'Question count depends on availability. Take the time you need.'}</p>
        </aside>
      </div>

      {error && <div className="alert" role="alert">{error} <button type="button" className="btn btn-secondary btn-sm" onClick={() => setLoadVersion(v => v + 1)}>Retry loading</button></div>}
      <div className="practice-bottom-line"><p><span>01</span> Choose your set <ArrowRight size={13}/><span>02</span> Solve at your pace <ArrowRight size={13}/><span>03</span> Submit & review</p><Link to="/plan">See how this fits your plan <ArrowUpRight size={14}/></Link></div>
      <details className="practice-plan-suggestion" open={showPlanSuggestion} onToggle={e => setShowPlanSuggestion(e.currentTarget.open)}><summary><Target size={18}/><span>Suggested practice from My Plan<small>Open your suggested topic and the reason behind it.</small></span><ChevronDown size={18}/></summary>{showPlanSuggestion && <GoalJourney onStartMission={startTest} missionBusy={starting} preferredSubject={requestedSubject} preferredChapter={requestedChapter}/>}</details>
    </main>
  </div>
}
