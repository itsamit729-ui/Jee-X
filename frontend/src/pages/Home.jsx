import { useState } from 'react'
import { Link } from 'react-router-dom'
import { useAuth } from '../auth/AuthContext.jsx'
import { ArrowUpRight, ArrowRight, Check, BookOpen, Target, ChartNoAxesCombined, GraduationCap, Users, Clock3, Trophy, CalendarCheck, ChevronDown, Play, RotateCcw, Layers3, Sparkles } from 'lucide-react'
import { Logo } from '../components/Brand.jsx'
import { preloadRoute } from '../lib/preloadRoute.js'
import useReveal from '../hooks/useReveal.js'
import './home.css'

const tasters = [
  { subject: 'Physics', topic: 'Work & energy', question: 'A car doubles its speed. What happens to its kinetic energy?', options: ['It doubles', 'It becomes 4×', 'It stays the same', 'It becomes 8×'], answer: 1, explanation: 'Kinetic energy = ½mv². Double the speed and the energy becomes four times as large.' },
  { subject: 'Chemistry', topic: 'Chemical bonding', question: 'Which molecule has a tetrahedral shape?', options: ['NH₃', 'H₂O', 'CH₄', 'CO₂'], answer: 2, explanation: 'CH₄ has four bonding pairs and no lone pairs around carbon, giving it a tetrahedral shape.' },
  { subject: 'Maths', topic: 'Differentiation', question: 'If f(x) = x² + 3x, what is f′(2)?', options: ['7', '10', '5', '4'], answer: 0, explanation: 'Differentiate first: f′(x) = 2x + 3. At x = 2, that gives 7.' },
]
const exams = [
  { label: 'JEE Main', text: 'Personalised practice, full mocks and a study plan that grows with you.', to: '/plan', action: 'Explore JEE preparation' },
  { label: 'MHT-CET', text: 'Year and shift mocks, subject practice and college cutoffs after your mock.', to: '/mhtcet-mock-tests', action: 'Explore MHT-CET papers' },
  { label: 'BITSAT', text: 'Build your concepts with the available memory-based BITSAT question collection.', to: '/pyq?exam=bitsat', action: 'Explore BITSAT questions' },
  { label: 'JEE Advanced', text: 'Explore IIT choices, Advanced cutoffs and the next stage of your preparation.', to: '/advanced', action: 'Explore IIT & Advanced' },
]
const features = [
  { id: 'practice', label: 'Practice', Icon: Target, tag: 'A SMALL SESSION. A REAL STEP.', title: 'Work on the gaps.\nBuild on the wins.', description: 'Choose a subject and chapter, or follow a recommended session. Get feedback on your answers and a clearer idea of what to work on next.', bullets: ['Subject & chapter practice', 'Personalised recommendations', 'Answer reviews & available solutions'], to: '/subject-test', action: 'Find your practice', secondary: '/plan', secondaryLabel: 'See my study plan' },
  { id: 'mocks', label: 'Mocks & PYQs', Icon: BookOpen, tag: 'GET FAMILIAR WITH EXAM DAY.', title: 'The paper. The pace.\nThe next attempt.', description: 'Rehearse with full mocks, explore previous-year questions, or choose an MHT-CET year and shift with its two timed sections.', bullets: ['JEE full mocks', 'MHT-CET year & shift papers', 'BITSAT memory-based practice'], to: '/pyq?exam=mht_cet', action: 'Browse the question archive', secondary: '/test', secondaryLabel: 'Take a JEE mock' },
  { id: 'progress', label: 'Plan & progress', Icon: ChartNoAxesCombined, tag: 'TURN RESULTS INTO A NEXT STEP.', title: 'See more than\na score.', description: 'Review your accuracy, spot subjects that need attention and connect your practice to a personal study plan. Every session gives you something to learn from.', bullets: ['Subject-level performance', 'Practice priorities & milestones', 'Your results, together in one place'], to: '/plan', action: 'Open my study plan', secondary: '/dashboard', secondaryLabel: 'View my progress' },
  { id: 'colleges', label: 'College outlook', Icon: GraduationCap, tag: 'KEEP YOUR DESTINATION IN VIEW.', title: 'Explore where\nyour work could lead.', description: 'Compare college and branch possibilities using historical cutoffs. Explore JEE choices in your plan and MHT-CET options from your mock results.', bullets: ['JEE college & branch exploration', 'IIT / Advanced cutoff data', 'MHT-CET percentile scenarios'], to: '/plan', action: 'Explore JEE college goals', secondary: '/pyq?exam=mht_cet', secondaryLabel: 'Start a CET mock' },
  { id: 'classes', label: 'Classrooms', Icon: Users, tag: 'GOOD TEACHING. CONNECTED PRACTICE.', title: 'Your class,\nwith a little more clarity.', description: 'Teachers can create classrooms and assign tests. Students get one place to find their assignments, while teachers can review results and topic accuracy.', bullets: ['Classrooms & assignments', 'Teacher-created tests', 'Submission & performance reports'], to: '/teacher', action: 'Open teacher studio', secondary: '/classes', secondaryLabel: 'Go to my classroom' },
]

function PracticePreview() {
  const [subject, setSubject] = useState(0)
  const [selected, setSelected] = useState(null)
  const q = tasters[subject]
  return <div className="edge-demo-window">
    <div className="edge-window-chrome"><span aria-hidden="true"><i/><i/><i/></span><span>A LITTLE PREVIEW OF YOUR PRACTICE</span><BookOpen size={14}/></div>
    <div className="edge-demo-inner">
      <div className="edge-demo-heading"><span className="edge-demo-badge"><Sparkles size={13}/> Try a concept</span><span>No account needed</span></div>
      <div className="edge-subject-tabs" role="group" aria-label="Choose a sample subject">{tasters.map((item, i) => <button key={item.subject} aria-pressed={subject === i} onClick={() => { setSubject(i); setSelected(null) }}>{item.subject}</button>)}</div>
      <div key={subject} className="edge-demo-question edge-content-in"><p>{q.topic} <span>· Concept warm-up</span></p><h2>{q.question}</h2>
        <div className="edge-demo-options">{q.options.map((answer, i) => <button key={answer} disabled={selected !== null} aria-pressed={selected === i} className={selected !== null && i === q.answer ? 'is-correct' : selected === i ? 'is-incorrect' : ''} onClick={() => setSelected(i)}><span>{'ABCD'[i]}</span>{answer}{selected !== null && i === q.answer && <Check size={15}/>}</button>)}</div>
      </div>
      <div className={`edge-demo-feedback${selected !== null ? ' has-answer' : ''}`} aria-live="polite">{selected === null ? <><span className="edge-answer-dot"/><p>Take a guess. That’s where learning starts.</p></> : <div className="edge-content-in"><strong>{selected === q.answer ? 'That’s it. A concept, connected.' : 'Let’s make that concept click.'}</strong><p>{q.explanation}</p></div>}</div>
      <div className="edge-demo-footer"><span>LEARN IT. TRY IT. MAKE IT STICK.</span>{selected !== null ? <button onClick={() => setSelected(null)}><RotateCcw size={13}/>Try again</button> : <ArrowUpRight size={17}/>}</div>
    </div>
    <div className="edge-demo-caption"><span className="edge-demo-check"><Check size={14}/></span><span>Small practice. <strong>Clearer understanding.</strong></span></div>
  </div>
}

function FeatureVisual({ id }) {
  if (id === 'practice') return <div className="edge-visual-plan"><div className="edge-visual-label"><Target size={17}/><span>A FOCUSED SESSION</span></div><h3>One topic.<br/>Your full attention.</h3><div className="edge-subject-cards">{[['P','Physics','Understand the concept'],['C','Chemistry','Apply what you know'],['M','Mathematics','Find your approach']].map(([letter,subject,copy], i) => <div key={letter} style={{ '--step': i }}><span>{letter}</span><div><strong>{subject}</strong><small>{copy}</small></div><ArrowUpRight size={16}/></div>)}</div></div>
  if (id === 'mocks') return <div className="edge-visual-paper"><div className="edge-visual-label"><Layers3 size={17}/><span>YOUR NEXT REHEARSAL</span></div><h3>Pick a paper.<br/>Find your rhythm.</h3><div className="edge-paper-flow"><span>Choose year</span><ArrowRight size={15}/><span>Choose shift</span></div><div className="edge-timing-row"><span>01</span><div><strong>Physics & Chemistry</strong><small>First section · MHT-CET</small></div><b>90 <small>min</small></b></div><div className="edge-timing-row"><span>02</span><div><strong>Mathematics</strong><small>Second section · MHT-CET</small></div><b>90 <small>min</small></b></div><p>Reconstructed papers; coverage varies by shift.</p></div>
  if (id === 'progress') return <div className="edge-visual-progress"><div className="edge-visual-label"><ChartNoAxesCombined size={17}/><span>FROM PRACTICE TO PROGRESS</span></div><h3>Connect<br/>the dots.</h3><svg viewBox="0 0 360 132" aria-hidden="true"><path className="edge-chart-grid" d="M0 25H360M0 70H360M0 115H360"/><path className="edge-chart-area" d="M10 109L65 89L120 94L175 61L230 70L285 32L345 16V132H10Z"/><path className="edge-chart-line" d="M10 109L65 89L120 94L175 61L230 70L285 32L345 16"/>{[[10,109],[65,89],[120,94],[175,61],[230,70],[285,32],[345,16]].map(([cx,cy]) => <circle key={cx} cx={cx} cy={cy} r="4"/>)}</svg><div className="edge-chart-legend"><span>Practise</span><span>Review</span><span>Try again</span></div><p>Illustrative journey. Your dashboard shows your actual results.</p></div>
  if (id === 'colleges') return <div className="edge-visual-college"><div className="edge-visual-label"><GraduationCap size={17}/><span>A GOAL TO WORK TOWARDS</span></div><div className="edge-campus" aria-hidden="true"><GraduationCap size={45} strokeWidth={1.1}/><span/><span/><span/></div><h3>Your next chapter<br/>starts with a possibility.</h3><div className="edge-college-tags"><span>College</span><span>Branch</span><span>Cutoff</span></div><p>Historical comparisons, not admission guarantees.</p></div>
  return <div className="edge-visual-class"><div className="edge-visual-label"><Users size={17}/><span>THE CONNECTED CLASSROOM</span></div><h3>Set the work.<br/>See the understanding.</h3><div className="edge-class-assignment"><span>01</span><div><strong>Create an assignment</strong><small>Pick questions for your class</small></div><Check size={16}/></div><div className="edge-class-assignment"><span>02</span><div><strong>Give students a clear task</strong><small>One place for their next test</small></div><Check size={16}/></div><div className="edge-class-assignment"><span>03</span><div><strong>Review what needs attention</strong><small>Results & topic accuracy</small></div><ArrowRight size={16}/></div></div>
}

export default function Home() {
  const { isAuthenticated } = useAuth()
  const [exam, setExam] = useState(0)
  const [feature, setFeature] = useState(0)
  const revealRef = useReveal()
  const chosen = exams[exam], current = features[feature]
  return <div className="edge-landing" ref={revealRef} onPointerOver={preloadRoute} onFocus={preloadRoute}>
    <a className="skip-link" href="#main-content">Skip to content</a>
    <header className="edge-public-header"><div className="edge-container edge-public-nav"><Logo/><nav aria-label="Main navigation"><a href="#what-you-get">What you get</a><Link to="/teacher">For teachers</Link><Link to="/pricing">Pricing</Link></nav><div className="edge-public-actions">{!isAuthenticated && <Link className="edge-login-link" to="/login">Log in</Link>}<Link className="btn btn-primary" to={isAuthenticated ? '/dashboard' : '/signup'}>{isAuthenticated ? 'My workspace' : 'Get started'}<ArrowUpRight size={16}/></Link></div></div></header>
    <main id="main-content">
      <section className="edge-container edge-hero">
        <div className="edge-hero-copy"><span className="edge-kicker"><span/>YOUR AMBITION. A LITTLE MORE DIRECTION.</span><h1>Make your next<br/>session <span>count.<svg viewBox="0 0 290 15" aria-hidden="true"><path d="M3 11Q142 -5 286 8"/></svg></span></h1><p>From “where do I start?” to “I’ve got this.”<br/>Practice, mocks and a clearer path to your college goals.</p>
          <div className="edge-hero-actions"><Link className="btn btn-primary btn-lg" to="/free-test">Try a free warm-up <ArrowRight size={18}/></Link><a className="edge-tour-link" href="#what-you-get"><span><Play size={12} fill="currentColor"/></span>Take a look around</a></div><div className="edge-hero-note"><Check size={14}/>No signup for the warm-up<span/>Start at your own pace</div>
          <div className="edge-exam-picker"><span>WHAT ARE YOU PREPARING FOR?</span><div role="group" aria-label="Explore your exam">{exams.map((item,i) => <button key={item.label} aria-pressed={i === exam} onClick={() => setExam(i)}>{item.label}</button>)}</div><div className="edge-exam-detail" key={exam}><p>{chosen.text}</p><Link to={chosen.to}>{chosen.action}<ArrowUpRight size={14}/></Link></div></div>
        </div><div className="edge-hero-preview"><div className="edge-preview-orbit" aria-hidden="true"/><PracticePreview/></div>
      </section>
      <div className="edge-container edge-offering-strip" aria-label="What Jee Edge offers">{[[Target,'Personalised practice'],[BookOpen,'PYQs & timed mocks'],[ChartNoAxesCombined,'Progress insights'],[GraduationCap,'College outlook']].map(([Icon,label]) => <a key={label} href="#what-you-get"><Icon size={18} strokeWidth={1.6}/>{label}</a>)}</div>
      <section className="edge-container edge-feature-section" id="what-you-get" data-reveal>
        <div className="edge-section-heading"><div><span className="edge-kicker">YOUR PREP, ALL TOGETHER</span><h2>Everything you need.<br/><span>With a next step that makes sense.</span></h2></div><p>Less jumping between tools.<br/>More time to actually learn.</p></div>
        <div className="edge-feature-tabs" role="group" aria-label="Explore platform features">{features.map(({ id, label, Icon },i) => <button key={id} aria-pressed={i === feature} aria-controls="edge-feature-panel" onClick={() => setFeature(i)}><Icon size={17}/>{label}<ArrowUpRight size={14}/></button>)}</div>
        <div className="edge-feature-panel" id="edge-feature-panel" key={current.id}><div className="edge-feature-copy edge-content-in"><span className="edge-kicker">{current.tag}</span><h3>{current.title}</h3><p>{current.description}</p><ul>{current.bullets.map(bullet => <li key={bullet}><Check size={15}/>{bullet}</li>)}</ul><div><Link className="btn btn-primary" to={current.to}>{current.action}<ArrowRight size={16}/></Link><Link className="edge-text-link" to={current.secondary}>{current.secondaryLabel}<ArrowUpRight size={14}/></Link></div></div><div className="edge-feature-visual edge-content-in"><FeatureVisual id={current.id}/></div></div>
      </section>
      <section className="edge-container edge-more-section" data-reveal><div className="edge-section-heading"><div><span className="edge-kicker">A LITTLE MOMENTUM GOES A LONG WAY</span><h2>Make it your kind of prep.</h2></div><Link className="edge-text-link" to={isAuthenticated ? '/dashboard' : '/signup'}>Find your starting point<ArrowRight size={16}/></Link></div><div className="edge-more-grid">{[
        { Icon: CalendarCheck, title: 'A daily reason to show up', detail: 'One question, a growing streak. Build a habit you can come back to.', to: '/daily', label: 'Try the daily question' },
        { Icon: Trophy, title: 'A little healthy competition', detail: 'Rated contests, student rankings and a profile that reflects your progress.', to: '/ranking', label: 'Explore rankings' },
        { Icon: Clock3, title: 'Get ready for the pressure', detail: 'Practise difficult exam moments in focused 15–45 minute situations.', to: '/scenarios', label: 'Explore exam situations' },
      ].map(({Icon,title,detail,to,label}) => <Link className="edge-more-card" key={to} to={to}><span className="edge-more-icon"><Icon size={23} strokeWidth={1.5}/></span><h3>{title}</h3><p>{detail}</p><span className="edge-more-link">{label}<ArrowUpRight size={17}/></span></Link>)}</div></section>
      <section className="edge-container edge-closing" data-reveal><div><span className="edge-kicker">YOU DON’T NEED TO HAVE IT ALL FIGURED OUT.</span><h2>You just need a place to start.</h2></div><Link className="btn btn-primary btn-lg" to="/free-test">Take the first step<ArrowRight size={18}/></Link></section>
      <div className="edge-container edge-home-faq"><details><summary>Can I try it before creating an account?<ChevronDown size={17}/></summary><p>Yes. Try the question above or take the free warm-up. Create an account when you’re ready to save your progress and use the study tools. If you’re under 18, review signup with a parent or guardian.</p></details><details><summary>Are the papers and college predictions official?<ChevronDown size={17}/></summary><p>Jee Edge is an independent preparation platform. PYQ coverage varies, some papers are reconstructed, and college comparisons use historical cutoffs. Always check the examination and counselling authorities for current rules and admissions decisions.</p></details></div>
    </main>
    <footer className="edge-container edge-public-footer"><div><Logo/><p>For the work behind the result.</p></div><nav aria-label="Footer"><Link to="/syllabus">Syllabus</Link><Link to="/pricing">Plans</Link><Link to="/terms">Terms</Link><Link to="/privacy">Privacy</Link><a href="mailto:admin@jeeedge.in">Contact</a></nav><span>JEE · MHT-CET · BITSAT</span></footer>
  </div>
}
