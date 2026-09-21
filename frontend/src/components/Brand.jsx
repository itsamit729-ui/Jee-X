import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'

const IITIAN_FACTS = [
  {
    name: 'Sundar Pichai · IIT Kharagpur',
    text: 'He studied metallurgical engineering before going on to lead Google and Alphabet.',
  },
  {
    name: 'Nandan Nilekani · IIT Bombay',
    text: 'The electrical engineering alumnus later co-founded Infosys and helped shape Aadhaar.',
  },
  {
    name: 'Raghuram Rajan · IIT Delhi',
    text: 'He studied electrical engineering before becoming an economist and Governor of the Reserve Bank of India.',
  },
  {
    name: 'K. Radhakrishnan · IIT Kharagpur',
    text: 'The alumnus led ISRO when India’s Mars Orbiter Mission reached the red planet.',
  },
  {
    name: 'Vinod Khosla · IIT Delhi',
    text: 'He studied electrical engineering and later co-founded Sun Microsystems.',
  },
  {
    name: 'Arvind Krishna · IIT Kanpur',
    text: 'The electrical engineering alumnus went on to lead IBM.',
  },
  {
    name: 'Deepinder Goyal · IIT Delhi',
    text: 'He studied mathematics and computing before co-founding Zomato.',
  },
  {
    name: 'Parag Agrawal · IIT Bombay',
    text: 'He studied computer science and engineering before later serving as Twitter’s CEO.',
  },
]

// The Jee Edge mark.
export function LogoMark() {
  return (
    <span className="logo-monogram" aria-hidden="true">JE</span>
  )
}

export function Logo({ to = '/' }) {
  return (
    <Link to={to} className="logo" aria-label="Jee Edge home">
      <LogoMark />
      <span>Jee Edge</span>
    </Link>
  )
}

export function Loader({ label, fullScreen = false }) {
  const [factIndex, setFactIndex] = useState(() => Math.floor(Math.random() * IITIAN_FACTS.length))

  useEffect(() => {
    const timer = window.setInterval(() => {
      setFactIndex((current) => (current + 1) % IITIAN_FACTS.length)
    }, 4800)
    return () => window.clearInterval(timer)
  }, [])

  const fact = IITIAN_FACTS[factIndex]
  return (
    <div className={fullScreen ? 'centered-screen loader-screen' : 'loader loader-screen'} role="status" aria-live="polite" aria-atomic="true">
      <span className="loader-orbit" aria-hidden="true"><i /></span>
      <span className="loader-label">{label}</span>
      <div className="loader-fact" key={factIndex}>
        <span className="loader-fact-kicker">WHILE YOU WAIT · IITIAN STORY</span>
        <strong>{fact.name}</strong>
        <p>{fact.text}</p>
        <span className="loader-fact-count">{String(factIndex + 1).padStart(2, '0')} / {String(IITIAN_FACTS.length).padStart(2, '0')}</span>
      </div>
    </div>
  )
}
