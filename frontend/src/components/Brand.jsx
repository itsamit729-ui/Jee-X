import { useEffect, useRef, useState } from 'react'
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
  const factRef = useRef(IITIAN_FACTS[factIndex])
  const factShownAtRef = useRef(Date.now())

  useEffect(() => {
    factRef.current = IITIAN_FACTS[factIndex]
    factShownAtRef.current = Date.now()
  }, [factIndex])

  useEffect(() => {
    const timer = window.setInterval(() => {
      setFactIndex((current) => (current + 1) % IITIAN_FACTS.length)
    }, 4800)
    return () => {
      window.clearInterval(timer)
      const timeAlreadyVisible = Date.now() - factShownAtRef.current
      const remainingReadingTime = Math.max(0, 7500 - timeAlreadyVisible)
      if (remainingReadingTime > 500) {
        window.dispatchEvent(new CustomEvent('jeex:loading-fact-complete', {
          detail: { fact: factRef.current, duration: remainingReadingTime },
        }))
      }
    }
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

export function IITianFactToast() {
  const [fact, setFact] = useState(null)
  const [duration, setDuration] = useState(7500)
  const timerRef = useRef(null)

  useEffect(() => {
    const showFact = (event) => {
      window.clearTimeout(timerRef.current)
      setFact(event.detail.fact)
      setDuration(event.detail.duration)
      timerRef.current = window.setTimeout(() => setFact(null), event.detail.duration)
    }
    window.addEventListener('jeex:loading-fact-complete', showFact)
    return () => {
      window.removeEventListener('jeex:loading-fact-complete', showFact)
      window.clearTimeout(timerRef.current)
    }
  }, [])

  if (!fact) return null
  return (
    <aside className="fact-toast" aria-live="polite" aria-label="IITian fact">
      <button type="button" className="fact-toast-close" onClick={() => setFact(null)} aria-label="Dismiss IITian fact">×</button>
      <span className="fact-toast-kicker">IITIAN STORY</span>
      <strong>{fact.name}</strong>
      <p>{fact.text}</p>
      <span className="fact-toast-progress" style={{ '--fact-duration': `${duration}ms` }} aria-hidden="true" />
    </aside>
  )
}
