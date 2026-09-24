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

const FACT_REVEAL_DELAY_MS = 350
const FACT_READING_TIME_MS = 7500

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
  const [factIndex] = useState(() => Math.floor(Math.random() * IITIAN_FACTS.length))
  const [factVisible, setFactVisible] = useState(false)
  const factVisibleAtRef = useRef(null)
  const fact = IITIAN_FACTS[factIndex]

  useEffect(() => {
    // A new loading state should never compete visually with an old fact toast.
    window.dispatchEvent(new CustomEvent('jeex:loading-start'))

    let cancelled = false
    const revealTimer = window.setTimeout(() => {
      if (cancelled) return
      factVisibleAtRef.current = Date.now()
      setFactVisible(true)
    }, FACT_REVEAL_DELAY_MS)

    return () => {
      cancelled = true
      window.clearTimeout(revealTimer)

      // React StrictMode intentionally runs an early effect cleanup in development.
      // Only hand a fact to the toast if it was actually visible to the student.
      if (!factVisibleAtRef.current) return

      const timeAlreadyVisible = Date.now() - factVisibleAtRef.current
      const remainingReadingTime = Math.max(0, FACT_READING_TIME_MS - timeAlreadyVisible)

      if (remainingReadingTime > 600) {
        window.dispatchEvent(new CustomEvent('jeex:loading-fact-complete', {
          detail: { fact, duration: remainingReadingTime },
        }))
      }
    }
  }, [fact])

  return (
    <div className={fullScreen ? 'centered-screen loader-screen' : 'loader loader-screen'} role="status" aria-live="polite" aria-atomic="true">
      <span className="loader-orbit" aria-hidden="true"><i /></span>
      <span className="loader-label">{label}</span>
      <div
        className={`loader-fact ${factVisible ? 'is-visible' : 'is-pending'}`}
        aria-hidden={!factVisible}
      >
        <span className="loader-fact-kicker">WHILE YOU WAIT · IITIAN STORY</span>
        <strong>{fact.name}</strong>
        <p>{fact.text}</p>
        <span className="loader-fact-count">{String(factIndex + 1).padStart(2, '0')} / {String(IITIAN_FACTS.length).padStart(2, '0')}</span>
      </div>
    </div>
  )
}

export function IITianFactToast() {
  const [toast, setToast] = useState(null)
  const timerRef = useRef(null)
  const sequenceRef = useRef(0)

  useEffect(() => {
    const clearToast = () => {
      window.clearTimeout(timerRef.current)
      timerRef.current = null
      setToast(null)
    }

    const showFact = (event) => {
      const fact = event.detail?.fact
      const duration = Number(event.detail?.duration)
      if (!fact || !Number.isFinite(duration) || duration <= 0) return

      window.clearTimeout(timerRef.current)
      const id = ++sequenceRef.current
      setToast({ fact, duration, id })
      timerRef.current = window.setTimeout(() => setToast(null), duration)
    }

    window.addEventListener('jeex:loading-start', clearToast)
    window.addEventListener('jeex:loading-fact-complete', showFact)

    return () => {
      window.removeEventListener('jeex:loading-start', clearToast)
      window.removeEventListener('jeex:loading-fact-complete', showFact)
      window.clearTimeout(timerRef.current)
    }
  }, [])

  if (!toast) return null

  const dismissToast = () => {
    window.clearTimeout(timerRef.current)
    timerRef.current = null
    setToast(null)
  }

  return (
    <aside key={toast.id} className="fact-toast" aria-live="polite" aria-label="IITian fact">
      <button type="button" className="fact-toast-close" onClick={dismissToast} aria-label="Dismiss IITian fact">×</button>
      <span className="fact-toast-kicker">IITIAN STORY</span>
      <strong>{toast.fact.name}</strong>
      <p>{toast.fact.text}</p>
      <span className="fact-toast-progress" style={{ '--fact-duration': `${toast.duration}ms` }} aria-hidden="true" />
    </aside>
  )
}
