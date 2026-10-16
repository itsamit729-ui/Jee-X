import { memo, useEffect, useState } from 'react'
import { ArrowRight, Check, Clock3, BookOpen, LoaderCircle, ArrowLeft } from 'lucide-react'
import AppHeader from './AppHeader.jsx'
import { instructionSeconds, testInstructions, canEnterTest, INSTRUCTION_SECONDS } from '../lib/testPreparation.js'
import './test-instructions.css'

const InstructionsHeader = memo(AppHeader)

export default function TestInstructions({ session, onEnter, onCancel, onRetry }) {
  const [now, setNow] = useState(Date.now)
  const [accepted, setAccepted] = useState(false)
  useEffect(() => { const tick = setInterval(() => setNow(Date.now()), 250); return () => clearInterval(tick) }, [])
  const seconds = instructionSeconds(session.startedAt, now)
  const details = testInstructions(session.details, session.paper)
  const ready = canEnterTest(session, now)
  return <div className="crackjee-root"><InstructionsHeader/><main className="test-instructions">
    <button className="btn btn-quiet btn-sm" onClick={onCancel}><ArrowLeft size={16}/> Back to selection</button>
    <header className="test-instructions-heading"><div><span className="test-instructions-eyebrow">{details.exam} · BEFORE YOU BEGIN</span><h1>A moment to prepare.</h1><p>Read how this test works while we get your paper ready.</p></div><div className="test-reading-clock" role="timer" aria-label={`${seconds} seconds of instruction time remaining`}><Clock3 size={20}/><strong>{Math.floor(seconds / 60)}:{String(seconds % 60).padStart(2, '0')}</strong><span>instruction time</span></div></header>
    <section className="test-instructions-card" aria-labelledby="instruction-title"><div className="test-instructions-summary"><div><BookOpen size={21}/><h2 id="instruction-title">{details.title}</h2></div><div><span>{details.count == null ? 'Preparing questions' : `${details.count} questions`}</span>{details.minutes && <span>{details.minutes} min{details.timed ? ' · timed' : ' · guide'}</span>}</div></div>
    <ol className="test-instructions-rules">{details.rules.map(rule => <li key={rule}>{rule}</li>)}</ol>
    <div className="test-preparation-status" role="status">{session.error ? <span>Paper preparation needs another try.</span> : session.loading ? <><LoaderCircle className="test-preparation-spin" size={17}/> Loading your questions and diagrams…</> : <><Check size={17}/> Your paper is ready. {seconds > 0 ? 'Finish reading before you begin.' : 'Enter whenever you are ready.'}</>}</div>
    {session.error && <div className="alert" role="alert">{session.error}<button className="btn btn-secondary btn-sm" onClick={onRetry}>Retry loading</button></div>}
    <progress max={INSTRUCTION_SECONDS} value={INSTRUCTION_SECONDS - seconds} aria-label="Instruction reading time completed"/>
    <div className="test-instructions-footer"><label><input type="checkbox" checked={accepted} onChange={e => setAccepted(e.target.checked)}/><span>I have read the instructions and am ready.</span></label><button className="btn btn-primary" disabled={!ready || !accepted} onClick={onEnter}>{seconds > 0 ? `Enter test in ${seconds}s` : session.loading ? 'Preparing paper…' : 'Enter test'}<ArrowRight size={17}/></button></div>
    <p className="test-instructions-note">These 90 seconds do not count towards your test time. Your test starts only after you press Enter test.</p></section>
  </main></div>
}
