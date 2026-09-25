import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '../auth/AuthContext.jsx'

function useCountUp(target, { decimals = 0, duration = 1100 } = {}) {
  const [value, setValue] = useState(0)

  useEffect(() => {
    const prefersReduced = window.matchMedia('(prefers-reduced-motion: reduce)').matches
    if (prefersReduced) {
      setValue(target)
      return
    }
    let start
    let frame
    const step = (ts) => {
      if (start === undefined) start = ts
      const progress = Math.min((ts - start) / duration, 1)
      const eased = 1 - Math.pow(1 - progress, 3)
      setValue(target * eased)
      if (progress < 1) frame = requestAnimationFrame(step)
    }
    frame = requestAnimationFrame(step)
    return () => cancelAnimationFrame(frame)
  }, [target, duration])

  return decimals > 0 ? value.toFixed(decimals) : Math.round(value).toLocaleString('en-IN')
}

function GridBackground() {
  return (
    <svg className="hero-grid-bg" width="100%" height="100%" preserveAspectRatio="none">
      <defs>
        <pattern id="grid" width="40" height="40" patternUnits="userSpaceOnUse">
          <path d="M 40 0 L 0 0 0 40" fill="none" stroke="rgba(242,239,230,0.06)" strokeWidth="1" />
        </pattern>
      </defs>
      <rect width="100%" height="100%" fill="url(#grid)" />
    </svg>
  )
}

const SUBJECTS = [
  {
    name: 'Physics',
    color: 'var(--physics)',
    count: '1,620 questions',
    topics: [
      { n: '01', t: 'Mechanics' },
      { n: '02', t: 'Electrodynamics' },
      { n: '03', t: 'Thermodynamics' },
      { n: '04', t: 'Optics & waves' },
      { n: '05', t: 'Modern physics' },
    ],
  },
  {
    name: 'Chemistry',
    color: 'var(--chem)',
    count: '1,690 questions',
    topics: [
      { n: '01', t: 'Physical chemistry' },
      { n: '02', t: 'Organic chemistry' },
      { n: '03', t: 'Inorganic chemistry' },
      { n: '04', t: 'Chemical bonding' },
      { n: '05', t: 'Equilibrium' },
    ],
  },
  {
    name: 'Mathematics',
    color: 'var(--maths)',
    count: '1,690 questions',
    topics: [
      { n: '01', t: 'Calculus' },
      { n: '02', t: 'Algebra' },
      { n: '03', t: 'Coordinate geometry' },
      { n: '04', t: 'Trigonometry' },
      { n: '05', t: 'Vectors & 3D' },
    ],
  },
]

const STEPS = [
  {
    title: 'Take a full-length or chapter mock',
    body: 'Sit a JEE-pattern test under a real timer, on paper-accurate question formatting, whenever you have the time.',
  },
  {
    title: 'Get a topic-by-topic breakdown',
    body: 'See accuracy and time spent per chapter, not just a final score — so you know exactly where marks were lost.',
  },
  {
    title: 'Get your next test tuned to your gaps',
    body: 'Your next mock leans harder on the topics you\u2019re weakest in, so every test you take closes a real gap.',
  },
]

export default function Landing() {
  const { openLogin, isAuthenticated, isLoading } = useAuth()
  const navigate = useNavigate()
  const rank = useCountUp(1284)
  const percentile = useCountUp(98.71, { decimals: 2 })

  // If someone lands here already authenticated (e.g. returning from the
  // account login page), send them straight into the app instead of
  // leaving them stranded on the marketing page.
  useEffect(() => {
    if (!isLoading && isAuthenticated) {
      navigate('/dashboard', { replace: true })
    }
  }, [isLoading, isAuthenticated, navigate])

  const goToSignup = () =>
    openLogin({ signup: true })
  const goToLogin = () => openLogin()
  const goToFreeTest = () => navigate('/free-test')

  return (
    <div>
      <nav className="nav">
        <div className="wrap nav-row">
          <span className="brand">Jee<span className="brand-x">X</span></span>
          <div className="nav-actions">
            <a className="nav-link desktop-only" href="#subjects">Subjects</a>
            <a className="nav-link desktop-only" href="#how-it-works">How it works</a>
            <button className="nav-link" onClick={goToLogin}>Log in</button>
            <button className="btn btn-amber" onClick={goToFreeTest}>Take a Free Test</button>
          </div>
        </div>
      </nav>

      <header className="hero">
        <GridBackground />
        <div className="wrap hero-inner">
          <div>
            <span className="hero-eyebrow">5,000 questions · fully classified · JEE Main &amp; Advanced</span>
            <h1>Crack JEE with data, not guesswork.</h1>
            <p className="lead">
              Take mock tests against other aspirants, see exactly which chapters are costing you rank,
              and get your next test built around your weak topics — automatically.
            </p>
            <div className="chip-row">
              <span className="chip"><span className="chip-dot" style={{ background: 'var(--physics)' }} />Physics</span>
              <span className="chip"><span className="chip-dot" style={{ background: 'var(--chem)' }} />Chemistry</span>
              <span className="chip"><span className="chip-dot" style={{ background: 'var(--maths)' }} />Mathematics</span>
            </div>
            <div className="hero-ctas">
              <button className="btn btn-amber" onClick={goToFreeTest}>Take a Free Test →</button>
              <a className="hero-note" href="#how-it-works">See how the analysis works</a>
            </div>
          </div>

          <div className="scorecard">
            <div className="scorecard-head">
              <span>MOCK TEST 14 · RESULT</span>
              <span>JEE MAIN PATTERN</span>
            </div>
            <div className="score-row">
              <span className="score-label">All India Rank</span>
              <span className="score-value amber">#{rank}</span>
            </div>
            <div className="score-row">
              <span className="score-label">Percentile</span>
              <span className="score-value">{percentile}</span>
            </div>
            <div className="score-row">
              <span className="score-label">Weakest chapter</span>
              <span className="score-value" style={{ fontSize: 16 }}>Electrodynamics</span>
            </div>
            <div className="score-row">
              <span className="score-label">Rank vs. last mock</span>
              <span className="score-delta">▲ 312 places</span>
            </div>
          </div>
        </div>
      </header>

      <section className="section" id="subjects">
        <div className="wrap">
          <div className="section-head">
            <h2>Every question, mapped to a chapter.</h2>
            <p>All 5,000 starter-pack questions are classified by subject, chapter and difficulty, so your results mean something the moment you finish a test.</p>
          </div>
          <div className="timetable">
            {SUBJECTS.map((s) => (
              <div className="timetable-col" key={s.name} style={{ '--subject-color': s.color }}>
                <h3>{s.name}</h3>
                <span className="count mono">{s.count}</span>
                <ul className="timetable-list">
                  {s.topics.map((topic) => (
                    <li key={topic.t}>
                      {topic.t}
                      <span className="n">{topic.n}</span>
                    </li>
                  ))}
                </ul>
              </div>
            ))}
          </div>
        </div>
      </section>

      <section className="section" id="how-it-works" style={{ paddingTop: 0 }}>
        <div className="wrap">
          <div className="section-head">
            <h2>How Jee Edge finds your weak topics</h2>
            <p>Three steps, repeated after every test, until your weak chapters run out.</p>
          </div>
          <div className="steps">
            {STEPS.map((step, i) => (
              <div className="step-row" key={step.title}>
                <span className="step-num mono">{String(i + 1).padStart(2, '0')}</span>
                <div>
                  <h3>{step.title}</h3>
                  <p>{step.body}</p>
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      <section className="stats">
        <div className="wrap stats-row">
          <div>
            <div className="stat-num">5,000</div>
            <div className="stat-label">questions in the starter pack</div>
          </div>
          <div>
            <div className="stat-num">3</div>
            <div className="stat-label">subjects, fully syllabus-mapped</div>
          </div>
          <div>
            <div className="stat-num">100%</div>
            <div className="stat-label">questions tagged by chapter &amp; difficulty</div>
          </div>
          <div>
            <div className="stat-num">1</div>
            <div className="stat-label">personalised retest after every mock</div>
          </div>
        </div>
      </section>

      <section className="final-cta">
        <div className="wrap">
          <h2>Your first mock test is free. See your rank before you commit.</h2>
          <button className="btn btn-ink" onClick={goToFreeTest}>Take a Free Test</button>
        </div>
      </section>

      <footer className="footer">
        <div className="wrap footer-row">
          <span>Jee Edge</span>
          <span>Built for JEE Main &amp; Advanced aspirants</span>
        </div>
      </footer>
    </div>
  )
}
