import { useEffect, useRef, useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { ArrowRight, ArrowUpRight, Check, ChevronDown, BookOpen, Target, Users, RefreshCw } from 'lucide-react'
import { Logo } from '../components/Brand.jsx'
import { useAuth } from '../auth/AuthContext.jsx'
import { request } from '../lib/api.js'
import './pricing.css'

const labels = { plus_monthly: 'Student Plus · monthly', plus_quarterly: 'Student Plus · three months', teacher: 'Teacher plan' }
const money = n => new Intl.NumberFormat('en-IN', { style: 'currency', currency: 'INR', maximumFractionDigits: 0 }).format(n)
const features = [
  ['Practice with explanations', 'Included', 'Included'],
  ['Personalised guidance', 'Starter recommendations', 'Full adaptive roadmap'],
  ['Focused practice', 'Daily practice', 'Practice sets for your gaps'],
  ['Progress reviews', 'Basic results', 'Milestones & progress history'],
  ['Revision planning', 'Self-directed', 'Scheduled revision priorities'],
]
const faqs = [
  ['Can I use JEE Edge without paying?', 'Yes. Start with the free warm-up without an account, or sign in to use the current practice experience. Existing features remain available during the launch period.'],
  ['What happens when I join the Plus waitlist?', 'We save your preferred plan against your account. You are not charged, subscribed or upgraded. You can change your preference or remove it here at any time. Checkout and final plan terms will be shown before any purchase.'],
  ['Is the three-month price a monthly charge?', 'No. The proposed three-month pass is ₹599 for the whole period. The monthly option is ₹249 for one month. Neither option takes payment on this page.'],
  ['How does the teacher pilot work?', 'Register your interest and open Teacher studio to create a classroom and assign tests. We propose a free 30-day supported pilot, with its start date agreed separately. Registering interest does not start a billing period or a countdown.'],
  ['Will following a plan guarantee my target college?', 'No. Your results guide practice priorities, and college possibilities depend on exam performance, eligibility, seat availability and counselling cutoffs. A roadmap supports your preparation; it cannot guarantee admission.'],
]

function Features({ items }) {
  return <ul className="pricing-features">{items.map(item => <li key={item}><Check size={17} aria-hidden="true"/><span>{item}</span></li>)}</ul>
}

export default function Pricing() {
  const { isAuthenticated, isLoading, openLogin } = useAuth()
  const [params] = useSearchParams()
  const initial = params.get('plan')
  const [audience, setAudience] = useState(initial === 'teacher' ? 'teacher' : 'student')
  const [quarterly, setQuarterly] = useState(initial === 'plus_quarterly')
  const [catalog, setCatalog] = useState(null)
  const [interest, setInterest] = useState(null)
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)
  const [loading, setLoading] = useState(true)
  const [retry, setRetry] = useState(0)
  const [notice, setNotice] = useState('')
  const noticeRef = useRef(null)
  useEffect(() => {
    if (isLoading) return
    let active = true
    setLoading(true); setError(''); setInterest(null); setNotice('')
    Promise.all([request('/api/plans'), isAuthenticated ? request('/api/plans/interest', { cache: false }) : Promise.resolve({ interest: null })])
      .then(([prices, saved]) => { if (active) { setCatalog(prices); setInterest(saved.interest) } })
      .catch(e => { if (active) setError(e.message) })
      .finally(() => { if (active) setLoading(false) })
    return () => { active = false }
  }, [isAuthenticated, isLoading, retry])
  async function choose(plan) {
    if (!isAuthenticated) { openLogin({ signup: true, returnTo: `/pricing?plan=${plan}` }); return }
    setBusy(true); setError(''); setNotice('')
    try {
      const data = await request('/api/plans/interest', { method: 'PUT', body: { plan } })
      setInterest(data.interest)
      setNotice(plan === 'teacher' ? 'Your teacher pilot interest is saved. You can explore Teacher studio now.' : 'You’re on the Plus waitlist. Your plan preference is saved; no payment has been taken.')
      noticeRef.current?.focus()
    } catch (e) { setError(e.message) }
    finally { setBusy(false) }
  }
  async function withdraw() {
    setBusy(true); setError('')
    try { await request('/api/plans/interest', { method: 'DELETE' }); setInterest(null); setNotice('Your request has been removed. Free practice is still here for you.') }
    catch (e) { setError(e.message) } finally { setBusy(false) }
  }
  const plan = quarterly ? 'plus_quarterly' : 'plus_monthly'
  const price = catalog?.plans[plan]
  const teacherPrice = catalog?.plans.teacher
  const disabled = busy || loading || isLoading || !catalog
  return <div className="pricing-page">
    <a className="skip-link" href="#pricing-main">Skip to plans</a>
    <header className="pricing-nav wrap"><Logo/><nav aria-label="Pricing navigation"><Link to="/">Home</Link><Link to="/free-test">Try a warm-up <ArrowUpRight size={15}/></Link>{isAuthenticated ? <Link to="/dashboard">My dashboard</Link> : <button onClick={() => openLogin({ returnTo: '/pricing' })}>Log in</button>}</nav></header>
    <main id="pricing-main">
      <section className="pricing-hero wrap"><span className="pricing-eyebrow">A LITTLE DIRECTION. A LOT TO BUILD ON.</span><h1>Start with curiosity.<br/><em>Grow with a plan.</em></h1><p>Make room for better practice, clearer next steps<br className="pricing-desktop-break"/> and progress you can understand.</p><div className="pricing-audience" role="group" aria-label="Choose student or teacher plans"><button aria-pressed={audience === 'student'} onClick={() => setAudience('student')}><BookOpen size={16}/>For students</button><button aria-pressed={audience === 'teacher'} onClick={() => setAudience('teacher')}><Users size={16}/>For teachers</button></div></section>
      <div className="wrap pricing-state" ref={noticeRef} tabIndex={-1}>
        {error && <div className="pricing-alert" role="alert"><p>{error}</p><button onClick={() => setRetry(n => n + 1)} disabled={busy}><RefreshCw size={15}/>Retry</button></div>}
        <div role="status" aria-live="polite">{notice && <p className="pricing-notice">{notice}</p>}</div>
        {interest && <div className="pricing-saved"><div><span>YOUR SAVED INTEREST</span><strong>{labels[interest.plan]}</strong><small>Waitlist only · No active subscription</small></div><button disabled={busy || loading} onClick={withdraw}>Remove request</button></div>}
        {isAuthenticated && initial && labels[initial] && !interest && !notice && <p className="pricing-return">Welcome back. Select <strong>{labels[initial]}</strong> below to confirm your interest.</p>}
      </div>
      <section className="wrap pricing-offers" aria-label={audience === 'student' ? 'Student plans' : 'Teacher plans'}>
        {audience === 'student' ? <>
          <div className="pricing-period"><span>Choose your Plus preference</span><div role="group" aria-label="Student Plus duration"><button aria-pressed={!quarterly} onClick={() => setQuarterly(false)}>Monthly</button><button aria-pressed={quarterly} onClick={() => setQuarterly(true)}>3 months <small>Save ₹148</small></button></div></div>
          <div className="pricing-grid"><article className="pricing-card"><div className="pricing-card-icon"><BookOpen size={23}/></div><span className="pricing-plan-label">THE FIRST STEP</span><h2>Free</h2><p className="pricing-card-description">A small start can change your whole study day.</p><div className="pricing-price">₹0<span>to get started</span></div><Link className="btn btn-secondary pricing-button" to="/free-test">Try the free warm-up <ArrowRight size={17}/></Link><small className="pricing-button-note">No account or card needed for the warm-up</small><Features items={['Mixed-subject warm-up', 'Daily practice and answer explanations', 'Basic test results', 'Starter personalised guidance']}/><p className="pricing-card-foot">Explore first. Find your rhythm.</p></article>
          <article className="pricing-card pricing-card-plus"><div className="pricing-card-top"><div className="pricing-card-icon"><Target size={23}/></div><span className="pricing-badge">COMING NEXT</span></div><span className="pricing-plan-label">MORE DIRECTION, EVERY DAY</span><h2>Student Plus</h2><p className="pricing-card-description">Connect today’s practice to the goal you’re working towards.</p><div className="pricing-price">{price ? money(price.price_inr) : '—'}<span>/{quarterly ? '3 months' : 'month'}</span></div><button className="btn btn-primary pricing-button" disabled={disabled} onClick={() => choose(plan)}>{busy ? 'Saving…' : interest?.plan === plan ? 'Keep this preference' : 'Join the Plus waitlist'}<ArrowRight size={17}/></button><small className="pricing-button-note">Proposed launch price · No charge today</small><Features items={['Everything in Free', 'Full adaptive roadmap to your goal', 'Focused practice with reasons', 'Revision priorities and milestone checks', 'Progress history across your tests']}/><p className="pricing-card-foot">{quarterly ? '₹599 total for three months. No monthly charge.' : 'One month at a time. Choose what fits.'}</p></article></div>
          <p className="pricing-launch-note">We’re building Plus with our early students. Current features remain available during launch; joining the waitlist does not unlock or restrict access.</p>
        </> : <div className="pricing-teacher"><div className="pricing-teacher-copy"><span className="pricing-eyebrow">A CLEARER VIEW OF YOUR CLASS</span><h2>You teach.<br/>Let practice show<br/><em>what needs attention.</em></h2><p>Give your batch a focused test. See their progress. Make the next lesson count.</p><div className="pricing-pilot-steps"><p><span>01</span>Register your interest</p><p><span>02</span>Explore Teacher studio</p><p><span>03</span>Agree your supported pilot dates</p></div><Link className="text-action" to="/teacher">Explore Teacher studio now <ArrowUpRight size={17}/></Link></div><article className="pricing-card"><div className="pricing-card-top"><Users size={26}/><span className="pricing-badge">EARLY TEACHER PILOT</span></div><h2>Your first batch,<br/>with our support.</h2><div className="pricing-price">₹0<span>/30-day agreed pilot</span></div><p className="pricing-card-description">Proposed ongoing plan: {teacherPrice ? money(teacherPrice.price_inr) : '—'}/month for up to 50 active students. No automatic billing.</p><button className="btn btn-primary pricing-button" disabled={disabled} onClick={() => choose('teacher')}>{busy ? 'Saving…' : 'Register pilot interest'}<ArrowRight size={17}/></button><small className="pricing-button-note">Pilot dates confirmed separately</small><Features items={['Create classrooms and assign tests', 'Review student and topic performance', 'Help setting up your first test', 'Start with one batch, learn what works']}/><Link className="text-action" to="/teacher">Open Teacher studio <ArrowUpRight size={16}/></Link></article></div>}
      </section>
      {audience === 'student' && <section className="wrap pricing-compare"><div><span className="pricing-eyebrow">THE DETAILS, WITHOUT THE GUESSWORK</span><h2>What changes with Plus?</h2><p>A preview of the planned tiers. Final terms will be available before checkout.</p></div><div className="pricing-table-scroll" tabIndex={0} role="region" aria-label="Compare planned tiers"><table><caption className="pricing-sr-only">Planned Free and Student Plus features</caption><thead><tr><th scope="col">Your practice experience</th><th scope="col">Free</th><th scope="col">Student Plus</th></tr></thead><tbody>{features.map(([feature, free, plus]) => <tr key={feature}><th scope="row">{feature}</th><td>{free}</td><td>{plus}</td></tr>)}</tbody></table></div></section>}
      <section className="pricing-promise"><div className="wrap"><span>OUR PROMISE</span><h2>Your mistakes should teach you something.</h2><p>Explanations stay part of practice. We won’t ask you to pay just to understand an answer you’ve already attempted.</p></div></section>
      <section className="wrap pricing-faq"><div><span className="pricing-eyebrow">GOOD QUESTIONS</span><h2>Before you choose.</h2></div><div>{faqs.map(([q, a]) => <details key={q}><summary>{q}<ChevronDown size={18}/></summary><p>{a}</p></details>)}</div></section>
      <section className="wrap pricing-final"><div><h2>Still deciding? Start solving.</h2><p>Five minutes is enough to take your first step.</p></div><Link className="btn btn-primary" to="/free-test">Take the free warm-up <ArrowRight size={17}/></Link></section>
    </main><footer className="wrap pricing-footer"><Logo/><span>Clear steps. Purposeful practice.</span><Link to="/">Back to home <ArrowUpRight size={15}/></Link></footer>
  </div>
}
