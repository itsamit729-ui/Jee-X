import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useAuth } from '../auth/AuthContext.jsx'
import { ArrowUpRight, ArrowRight, Check } from 'lucide-react'
import './home.css'
import '../studio-ui.css'
import { Logo } from '../components/Brand.jsx'

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

export default function Home() {
  const navigate = useNavigate()
  const { isAuthenticated, openLogin } = useAuth()
  const [preview, setPreview] = useState(0)
  const freeTest = () => navigate('/free-test')
  return <div className="editorial-home edge-home studio-home">
    <a className="skip-link" href="#main-content">Skip to content</a>
    <header className="studio-public-nav"><Logo/><nav aria-label="Main navigation"><Link to="/pricing">Plans</Link><Link to="/teacher">For teachers</Link><button onClick={() => isAuthenticated ? navigate('/dashboard') : openLogin()}>{isAuthenticated ? 'My workspace' : 'Log in'}<ArrowUpRight size={16}/></button></nav></header>
    <main id="main-content" className="studio-home-main">
      <div className="studio-home-intro"><span className="studio-overline">JEE PREPARATION, WITH DIRECTION</span><span className="studio-home-edition">YOUR NEXT CHAPTER STARTS HERE</span></div>
      <section className="studio-home-stage"><div className="studio-home-story"><span className="studio-story-tag"><span/>A PLAN THAT LEARNS WITH YOU</span><h1>Big ambition.<br/>Clear steps.<br/><em>Your edge.</em></h1><p>Know what to practise next,<br/>why it matters, and where it can take you.</p><button className="btn" onClick={freeTest}>Find my starting point <ArrowRight size={18}/></button><small>5-minute warm-up · No account needed</small><div className="studio-story-footer"><span>01 <strong>Discover</strong></span><span>02 <strong>Practise</strong></span><span>03 <strong>Progress</strong></span></div></div>
      <div className="studio-home-demo"><div className="studio-demo-switch" role="group" aria-label="Explore JEE Edge"><button aria-pressed={preview === 0} onClick={() => setPreview(0)}>Try a question</button><button aria-pressed={preview === 1} onClick={() => setPreview(1)}>See the approach</button></div>{preview === 0 ? <PracticePreview onStart={freeTest}/> : <div className="studio-approach"><span className="studio-overline">FROM ANSWERS TO ACTION</span><h2>A next step.<br/>Not another to-do list.</h2><ol>{[['Find your starting point','Your answers help identify topics that need attention.'],['Practise with a reason','See why a topic is recommended and what to work on.'],['Check your progress','Fresh tests help update your milestones and college possibilities.']].map(([title,body],i) => <li key={title}><span>0{i+1}</span><div><strong>{title}</strong><p>{body}</p></div></li>)}</ol><button className="btn btn-primary" onClick={() => navigate('/plan')}>Explore my plan <ArrowUpRight size={17}/></button><small>College possibilities are estimates, not admission guarantees.</small></div>}</div></section>
      <section className="studio-home-paths" aria-label="Other ways to begin">{[['01','Start small','Free mixed-subject warm-up','/free-test'],['02','Pick your focus','Subject & chapter practice','/subject-test'],['03','Bring your class','Assignments & student progress','/teacher']].map(([n,title,detail,path]) => <Link key={path} to={path}><span>{n}</span><div><strong>{title}</strong><small>{detail}</small></div><ArrowUpRight size={19}/></Link>)}</section>
    </main><footer className="studio-public-footer"><span>Built for the work behind the result.</span><Link to="/pricing">Free to start. Explore our plans <ArrowRight size={15}/></Link></footer>
  </div>
}
