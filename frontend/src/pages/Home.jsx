import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '../auth/AuthContext.jsx'
import { ArrowUpRight, ArrowRight, Check, Clock3, ChevronDown, Menu, X } from 'lucide-react'
import { Logo } from '../components/Brand.jsx'

const subjects = [
  { name: 'Physics', symbol: 'φ', subtitle: 'Physics', topics: 'Mechanics · Electrodynamics · Modern physics', className: 'physics' },
  { name: 'Chemistry', symbol: 'C', subtitle: 'Chemistry', topics: 'Physical · Organic · Inorganic chemistry', className: 'chemistry' },
  { name: 'Mathematics', symbol: '∑', subtitle: 'Mathematics', topics: 'Calculus · Algebra · Coordinate geometry', className: 'mathematics' },
]
const faqs = [
  ['Do I need an account to try it?', 'No. The free warm-up opens straight away: ten questions, thirty seconds each, and an explanation after every answer. Create an account afterwards if you want to keep your result.'],
  ['What can I practise on Jee Edge?', 'Choose a full JEE Main-style mock, a subject or chapter test, or a short mixed-subject warm-up. The full mock includes a timer and a question palette for reviewing answers.'],
  ['How do I know what to work on next?', 'Review your answers and subject accuracy after a test. Your dashboard keeps your test history so you can spot patterns, then choose a subject or chapter to revisit.'],
]

function PracticePreview() {
  const [selected, setSelected] = useState(null)
  return <div className="practice-preview">
    <div className="preview-top"><span><span className="live-dot" /> TRY A QUESTION</span><span>01 / 01</span></div>
    <div className="preview-body">
      <div className="preview-meta"><span>MATHEMATICS</span><span>Limits & continuity</span></div>
      <h2>Evaluate the following limit.</h2>
      <div className="limit-formula" aria-label="The limit as n tends to infinity of one plus one over n, raised to the n"><span className="lim">lim<small>n → ∞</small></span><span>(1 + <span className="fraction"><span>1</span><span>n</span></span>)<sup>n</sup> = ?</span></div>
      <div className="preview-options">{['1', '∞', 'e', '0'].map((answer, index) => <button type="button" key={answer} aria-pressed={selected === index} disabled={selected !== null} className={(selected !== null && index === 2 ? 'correct' : selected === index ? 'incorrect' : '')} onClick={() => setSelected(index)}><span>{'ABCD'[index]}</span>{answer}{selected !== null && index === 2 && <Check size={16} />}</button>)}</div>
      <div className="preview-feedback" aria-live="polite">{selected === null ? <><span className="tiny-square" /> Select an option to check your answer.</> : <><Check size={15} />{selected === 2 ? 'Exactly. ' : 'The answer is e. '}This limit is a definition of Euler’s number.</>}</div>
    </div>
    <div className="preview-bottom"><span>Practice question · Single correct answer</span><span>Jee Edge / PRACTICE</span></div>

  </div>
}

export default function Home() {
  const navigate = useNavigate()
  const { isAuthenticated, openLogin } = useAuth()
  const [menuOpen, setMenuOpen] = useState(false)
  const freeTest = () => navigate('/free-test')
  return <div className="editorial-home">
    <a className="skip-link" href="#main-content">Skip to content</a>
    <header className="site-header"><div className="wrap site-header-row">
      <Logo />
      <nav className="desktop-nav" aria-label="Main navigation"><a href="#method">Test formats</a><a href="#subjects">Subjects</a><a href="#questions">FAQs</a></nav>
      <div className="site-header-actions"><button className="login-link" onClick={() => isAuthenticated ? navigate('/dashboard') : openLogin()}>{isAuthenticated ? 'My dashboard' : 'Log in'}<ArrowUpRight size={15} /></button><button className="btn btn-primary btn-sm" onClick={freeTest}>Free test <ArrowRight size={15} /></button><button className="menu-toggle" aria-label={menuOpen ? 'Close navigation' : 'Open navigation'} aria-expanded={menuOpen} aria-controls="mobile-nav" onClick={() => setMenuOpen(!menuOpen)}>{menuOpen ? <X size={21} /> : <Menu size={21} />}</button></div>
    </div>{menuOpen && <nav id="mobile-nav" className="mobile-nav" aria-label="Mobile navigation">{[['#method', 'Test formats'], ['#subjects', 'Subjects'], ['#questions', 'FAQs']].map(([href, label]) => <a key={href} href={href} onClick={() => setMenuOpen(false)}>{label}<ArrowUpRight size={16}/></a>)}</nav>}</header>
    <main id="main-content">
      <section className="editorial-hero wrap">
        <div className="hero-copy"><div className="eyebrow">JEE MAIN / PRACTICE & ANALYSIS</div><h1>Know your gaps.<br /><span>Get to work.</span></h1><p>Full mocks when you’re ready.<br />Chapter practice when you’re not.</p><p className="hero-detail">Test yourself, review the mistakes, and choose exactly what to practise next.</p><div className="hero-cta"><button className="btn btn-primary btn-lg" onClick={freeTest}>Take a free test <ArrowRight size={19}/></button><button className="text-action" onClick={() => navigate('/test')}>Start a full mock <ArrowUpRight size={17}/></button></div><div className="hero-proof"><span>10 questions</span><span>5 minutes</span><span>No account needed</span></div></div>
        <div className="hero-object"><PracticePreview /></div>
      </section>
      <section id="method" className="method-section wrap"><div className="section-intro"><h2>What are you working on today?</h2><p>Choose the session that fits.</p></div><div className="method-grid">{[
        ['01', 'Quick diagnostic', '10 questions across all three subjects. Get feedback on every answer.', '5 MIN', 'Take free test', freeTest],
        ['02', 'Full mock', '75 questions, timed sections and a question palette. Set aside a proper session.', '180 MIN', 'Start mock', () => navigate('/test')],
        ['03', 'Subject practice', 'Choose a subject or chapter and focus on the concepts you need to revisit.', 'YOUR PACE', 'Choose subject', () => navigate('/subject-test')],
      ].map(([number, title, body, duration, link, action]) => <article className="method-item" key={number}><span className="method-number">{number}</span><div><h3>{title}</h3><p>{body}</p></div><span className="session-duration">{duration}</span><button className="text-action" onClick={action}>{link}<ArrowRight size={16}/></button></article>)}</div></section>
      <section id="subjects" className="subject-section"><div className="wrap"><div className="section-intro"><div><span className="eyebrow">THE SYLLABUS</span><h2>One chapter at a time.</h2></div><p>Start with the subject that needs your attention.</p></div><div className="subject-collection">{subjects.map((subject,i) => <button key={subject.name} className={`subject-editorial ${subject.className}`} onClick={() => navigate(`/subject-test?subject=${encodeURIComponent(subject.name)}`)}><span className="subject-code">0{i+1}</span><h3>{subject.name}</h3><p>{subject.topics}</p><ArrowUpRight size={24}/></button>)}</div></div></section>
      <section className="exam-editorial wrap"><div className="exam-paper"><div className="paper-heading">MOCK TEST / QUESTION STATUS <span>JEE MAIN</span></div><div className="paper-timer"><Clock3 size={19}/> 02:48:32 <span>Illustrative preview</span></div><div className="paper-palette" aria-label="Example exam question palette">{Array.from({length:20},(_,i)=><span key={i} className={i<8?'done':i===8?'review':i===9?'current':''}>{String(i+1).padStart(2,'0')}</span>)}</div><div className="paper-legend"><span><i className="done"/>Answered</span><span><i className="review"/>Review</span><span><i/>Not visited</span></div></div><div className="exam-editorial-copy"><span className="eyebrow">BUILT FOR A FULL SESSION</span><h2>Practise the paper.<br />And the pressure.</h2><p>Switch subjects, flag questions and review your answers before submitting. The full mock keeps the timer and question status in view.</p><button className="btn btn-secondary" onClick={() => navigate('/test')}>Start a full mock <ArrowUpRight size={17}/></button><span className="exam-footnote">75 questions · 3 hours · JEE Main-style interface</span></div></section>
      <section id="questions" className="faq-section wrap"><div><span className="eyebrow">BEFORE YOU START</span><h2>Questions?</h2></div><div>{faqs.map(([q,a])=><details key={q}><summary>{q}<ChevronDown size={18}/></summary><p>{a}</p></details>)}</div></section>
      <section className="closing-section"><div className="wrap closing-inner"><div><h2>Start with ten questions.</h2><p>See what you know. Find out what needs work.</p></div><button className="btn btn-primary btn-lg" onClick={freeTest}>Take the free test <ArrowRight size={19}/></button></div></section>
    </main>
    <footer className="editorial-footer wrap"><Logo/><span>JEE practice. Test. Review. Repeat.</span><a href="#main-content">Back to top ↑</a></footer>
  </div>
}
