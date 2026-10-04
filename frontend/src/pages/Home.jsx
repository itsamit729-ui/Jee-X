import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useAuth } from '../auth/AuthContext.jsx'
import { ArrowUpRight, ArrowRight, Check, Clock3, ChevronDown, Menu, X } from 'lucide-react'
import './home.css'
import { Logo } from '../components/Brand.jsx'

const subjects = [
  { name: 'Physics', symbol: 'φ', subtitle: 'Physics', topics: 'Mechanics · Electrodynamics · Modern physics', className: 'physics' },
  { name: 'Chemistry', symbol: 'C', subtitle: 'Chemistry', topics: 'Physical · Organic · Inorganic chemistry', className: 'chemistry' },
  { name: 'Mathematics', symbol: '∑', subtitle: 'Mathematics', topics: 'Calculus · Algebra · Coordinate geometry', className: 'mathematics' },
]
const faqs = [
  ['Do I need an account to try it?', 'No. The free warm-up opens straight away: ten questions, thirty seconds each, and an explanation after every answer. Create an account afterwards if you want to keep your result.'],
  ['What can I practise on Jee Edge?', 'Choose a full JEE Main-style mock, a subject or chapter test, or a short mixed-subject warm-up. The full mock includes a timer and a question palette for reviewing answers.'],
  ['How do I know what to work on next?', 'Your plan connects recommended practice to topic milestones. As you complete tests, it uses the growing evidence to review your next steps. Each recommended question explains why it was selected.'],
]

const tasters = [
  { subject: 'Physics', topic: 'Work & energy', question: 'A car doubles its speed. What happens to its kinetic energy?', options: ['It doubles', 'It becomes 4×', 'It stays the same', 'It becomes 8×'], answer: 1, explanation: 'Kinetic energy = ½mv². Double the speed and the energy becomes four times as large.', next: 'Next, try a work–energy problem where the speed is unknown.' },
  { subject: 'Chemistry', topic: 'Chemical bonding', question: 'Which molecule has a tetrahedral shape?', options: ['NH₃', 'H₂O', 'CH₄', 'CO₂'], answer: 2, explanation: 'CH₄ has four bonding pairs and no lone pairs around carbon. VSEPR predicts a tetrahedral shape.', next: 'Next, compare shapes when the central atom has lone pairs.' },
  { subject: 'Mathematics', topic: 'Differentiation', question: 'If f(x) = x² + 3x, what is f′(2)?', options: ['7', '10', '5', '4'], answer: 0, explanation: 'Differentiate first: f′(x) = 2x + 3. At x = 2, that gives 7.', next: 'Next, use the derivative to find the slope of a tangent.' },
]

function PracticePreview({ onStart }) {
  const [subject, setSubject] = useState(0)
  const [selected, setSelected] = useState(null)
  const q = tasters[subject]
  return <div className="practice-preview edge-taster">
    <div className="preview-top"><span><span className="live-dot" /> YOUR FIRST SMALL WIN</span><span>TRY IT HERE ↙</span></div>
    <div className="taster-subjects" role="group" aria-label="Choose a sample subject">{tasters.map((item, i) => <button key={item.subject} aria-pressed={subject === i} onClick={() => { setSubject(i); setSelected(null) }}>{item.subject}</button>)}</div>
    <div className="preview-body">
      <div className="preview-meta"><span>{q.topic}</span><span>Concept warm-up · Untimed</span></div>
      <h2>{q.question}</h2>
      <div className="preview-options">{q.options.map((answer, i) => <button key={answer} disabled={selected !== null} aria-pressed={selected === i} className={selected !== null && i === q.answer ? 'correct' : selected === i ? 'incorrect' : ''} onClick={() => setSelected(i)}><span>{'ABCD'[i]}</span>{answer}{selected !== null && i === q.answer && <Check size={16} />}</button>)}</div>
      <div className="taster-result" aria-live="polite">{selected === null ? <p>One question. One concept. Give it a go.</p> : <><strong>{selected === q.answer ? 'You’ve got the concept.' : 'A useful mistake. Here’s the idea.'}</strong><p>{q.explanation}</p><div className="taster-next"><span>WHAT TO TRY NEXT</span><p>{q.next}</p></div><button className="text-action" onClick={onStart}>Keep going with the free warm-up <ArrowRight size={16}/></button></>}</div>
    </div>
    <div className="preview-bottom"><span>Instant feedback. No sign-up.</span><span>Sample question</span></div>
  </div>
}

const journey = [
  { label: 'Find your starting point', title: 'Turn “I’m weak in Physics” into a topic to work on.', topic: 'Current electricity', action: 'Check circuit basics, then practise Kirchhoff’s laws.', why: 'Example: repeated errors in circuit questions suggest revisiting the concept before attempting harder problems.', evidence: 'Your attempts and accuracy establish the starting point.' },
  { label: 'Practise with a purpose', title: 'Know what to solve. And why it matters.', topic: 'Kirchhoff’s laws', action: 'Review the sign convention. Solve a focused set, then check each mistake.', why: 'Example: targeted practice helps distinguish a concept gap from a calculation error.', evidence: 'Fresh answers help decide whether to move on or revisit a topic.' },
  { label: 'Check. Adjust. Move forward.', title: 'A plan that responds to your next test.', topic: 'Mixed-topic checkpoint', action: 'Test the topic again alongside other chapters, then review your next milestone.', why: 'Example: performance on fresh questions is better evidence than repeating a memorised answer.', evidence: 'As evidence grows, review your progress and college possibilities in your plan.' },
]

function JourneyPreview({ onStart }) {
  const [step, setStep] = useState(0)
  const item = journey[step]
  return <section className="edge-journey" id="journey"><div className="wrap">
    <div className="section-intro"><div><span className="eyebrow">YOUR EFFORT NEEDS A DIRECTION</span><h2>From “what now?”<br/>to your next milestone.</h2></div><p>Recommendations and your roadmap, connected.<br/>Explore an example of the journey.</p></div>
    <div className="journey-demo"><div className="journey-stops" role="group" aria-label="Explore the example roadmap">{journey.map((stop, i) => <button key={stop.label} aria-pressed={step === i} onClick={() => setStep(i)}><span>0{i + 1}</span><div><small>{i === 0 ? 'START HERE' : i === 1 ? 'BUILD THE SKILL' : 'RECHECK YOUR PROGRESS'}</small><strong>{stop.label}</strong></div><ArrowRight size={18}/></button>)}</div><div className="journey-detail" aria-live="polite"><span className="example-tag">ILLUSTRATIVE PLAN · NOT YOUR ASSESSMENT</span><h3>{item.title}</h3><div className="journey-task"><span>FOCUS / {item.topic}</span><p>{item.action}</p></div><p>{item.why}</p><div className="journey-evidence"><Check size={17}/><span>{item.evidence}</span></div></div></div>
    <div className="journey-foot"><p>Set a marks goal or college preferences. Build evidence through practice.<br/><small>College possibilities are estimates based on available results and cutoff data, not admission guarantees.</small></p><button className="btn btn-secondary" onClick={onStart}>Build my plan <ArrowUpRight size={17}/></button></div>
  </div></section>
}

function SessionChooser({ navigate }) {
  const [choice, setChoice] = useState(0)
  const sessions = [
    { time: '5 minutes', label: 'Get a quick win.', body: 'Ten mixed-subject questions, with feedback after every answer. A warm-up to get moving, not a prediction of your JEE rank.', route: '/free-test', cta: 'Start my free warm-up', note: 'No account needed' },
    { time: 'At my pace', label: 'Work on one chapter.', body: 'Pick the subject that needs attention. Focus your session on a chapter, review your mistakes and build from there.', route: '/subject-test', cta: 'Choose my subject', note: 'Sign in to save your progress' },
    { time: '3 hours', label: 'Rehearse the real effort.', body: 'A 75-question JEE Main-style mock with a timer, review flags and a question palette. Make room for a full session.', route: '/test', cta: 'Start a full mock', note: 'Sign in to track your result' },
  ]
  const selected = sessions[choice]
  return <section id="method" className="edge-session wrap"><div><span className="eyebrow">MAKE TODAY COUNT</span><h2>How much time<br/>have you got?</h2><div className="session-switch" role="group" aria-label="Choose your session">{sessions.map((session, i) => <button key={session.time} aria-pressed={choice === i} onClick={() => setChoice(i)}>{session.time}</button>)}</div></div><div className="session-choice" aria-live="polite"><span className="session-index">0{choice + 1} / YOUR NEXT SESSION</span><h3>{selected.label}</h3><p>{selected.body}</p><div><button className="btn btn-primary" onClick={() => navigate(selected.route)}>{selected.cta}<ArrowRight size={17}/></button><small>{selected.note}</small></div></div></section>
}

export default function Home() {
  const navigate = useNavigate()
  const { isAuthenticated, openLogin } = useAuth()
  const [menuOpen, setMenuOpen] = useState(false)
  const freeTest = () => navigate('/free-test')
  return <div className="editorial-home edge-home">
    <a className="skip-link" href="#main-content">Skip to content</a>
    <header className="site-header"><div className="wrap site-header-row">
      <Logo />
      <nav className="desktop-nav" aria-label="Main navigation"><a href="#journey">Your roadmap</a><a href="#subjects">Subjects</a><Link to="/pricing">Plans</Link></nav>
      <div className="site-header-actions"><button className="login-link" onClick={() => isAuthenticated ? navigate('/dashboard') : openLogin()}>{isAuthenticated ? 'My dashboard' : 'Log in'}<ArrowUpRight size={15} /></button><button className="btn btn-primary btn-sm" onClick={freeTest}>Free test <ArrowRight size={15} /></button><button className="menu-toggle" aria-label={menuOpen ? 'Close navigation' : 'Open navigation'} aria-expanded={menuOpen} aria-controls="mobile-nav" onClick={() => setMenuOpen(!menuOpen)}>{menuOpen ? <X size={21} /> : <Menu size={21} />}</button></div>
    </div>{menuOpen && <nav id="mobile-nav" className="mobile-nav" aria-label="Mobile navigation">{[['#journey', 'Your roadmap'], ['#subjects', 'Subjects'], ['/pricing', 'Plans']].map(([href, label]) => <a key={href} href={href} onClick={() => setMenuOpen(false)}>{label}<ArrowUpRight size={16}/></a>)}</nav>}</header>
    <main id="main-content">
      <section className="editorial-hero wrap">
        <div className="hero-copy"><div className="eyebrow">LESS SECOND-GUESSING. MORE PROGRESS.</div><h1>Your next<br/>breakthrough<br/><span>starts here.</span></h1><p>Big JEE goal. One clear next step.</p><p className="hero-detail">Find the topics holding you back, practise with a reason, and build a plan that evolves with your results.</p><div className="hero-cta"><button className="btn btn-primary btn-lg" onClick={freeTest}>Find my starting point <ArrowRight size={19}/></button><a className="text-action" href="#journey">Explore the roadmap <ArrowUpRight size={17}/></a></div><div className="hero-proof"><span>5-minute warm-up</span><span>No account needed</span></div></div>
        <div className="hero-object"><div className="taster-caption">A little less scrolling. A little more solving.</div><PracticePreview onStart={freeTest}/></div>
      </section>
      <div className="edge-principles wrap"><span>EVERY SESSION HAS A PURPOSE</span><p><Check size={16}/> Know your next topic</p><p><Check size={16}/> Understand every recommendation</p><p><Check size={16}/> Revisit your plan as you improve</p></div>
      <SessionChooser navigate={navigate}/>
      <JourneyPreview onStart={() => navigate('/plan')}/>
      <section id="subjects" className="subject-section"><div className="wrap"><div className="section-intro"><div><span className="eyebrow">THE SYLLABUS</span><h2>One chapter at a time.</h2></div><p>Start with the subject that needs your attention.</p></div><div className="subject-collection">{subjects.map((subject,i) => <button key={subject.name} className={`subject-editorial ${subject.className}`} onClick={() => navigate(`/subject-test?subject=${encodeURIComponent(subject.name)}`)}><span className="subject-code">0{i+1}</span><h3>{subject.name}</h3><p>{subject.topics}</p><ArrowUpRight size={24}/></button>)}</div></div></section>
      <section className="exam-editorial wrap"><div className="exam-paper"><div className="paper-heading">MOCK TEST / QUESTION STATUS <span>JEE MAIN</span></div><div className="paper-timer"><Clock3 size={19}/> 02:48:32 <span>Illustrative preview</span></div><div className="paper-palette" aria-label="Example exam question palette">{Array.from({length:20},(_,i)=><span key={i} className={i<8?'done':i===8?'review':i===9?'current':''}>{String(i+1).padStart(2,'0')}</span>)}</div><div className="paper-legend"><span><i className="done"/>Answered</span><span><i className="review"/>Review</span><span><i/>Not visited</span></div></div><div className="exam-editorial-copy"><span className="eyebrow">BUILT FOR A FULL SESSION</span><h2>Practise the paper.<br />And the pressure.</h2><p>Switch subjects, flag questions and review your answers before submitting. The full mock keeps the timer and question status in view.</p><button className="btn btn-secondary" onClick={() => navigate('/test')}>Start a full mock <ArrowUpRight size={17}/></button><span className="exam-footnote">75 questions · 3 hours · JEE Main-style interface</span></div></section>
      <section id="questions" className="faq-section wrap"><div><span className="eyebrow">BEFORE YOU START</span><h2>Questions?</h2></div><div>{faqs.map(([q,a])=><details key={q}><summary>{q}<ChevronDown size={18}/></summary><p>{a}</p></details>)}</div></section>
      <section className="home-pricing-link wrap"><div><h2>Find your rhythm. Choose your plan.</h2><p>Start free, explore Student Plus, or bring your classroom.</p></div><Link className="btn btn-secondary" to="/pricing">Explore plans <ArrowRight size={17}/></Link></section>
      <section className="closing-section"><div className="wrap closing-inner"><div><h2>Your goal is big.<br/>Your first step isn’t.</h2><p>Give yourself five minutes. Start with what you know.</p></div><button className="btn btn-primary btn-lg" onClick={freeTest}>Take the free test <ArrowRight size={19}/></button></div></section>
    </main>
    <footer className="editorial-footer wrap"><Logo/><span>JEE practice. Test. Review. Repeat.</span><a href="#main-content">Back to top ↑</a></footer>
  </div>
}
