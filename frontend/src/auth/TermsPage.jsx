import { useState } from 'react'
import { Link, Navigate, useSearchParams } from 'react-router-dom'
import { Logo, Loader } from '../components/Brand.jsx'
import { request } from '../lib/api.js'
import { safeReturnTo, useAuth } from './AuthContext.jsx'
import TermsFields, { emptyTerms } from './TermsFields.jsx'

export default function TermsPage() {
  const { user, isLoading, isAuthenticated, refreshSession, logout } = useAuth()
  const [terms, setTerms] = useState(emptyTerms)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const [params] = useSearchParams()
  const destination = safeReturnTo(params.get('returnTo'))
  if (isLoading) return <Loader fullScreen label="Checking your session"/>
  if (!isAuthenticated) return <Navigate replace to="/signup"/>
  if (!user.terms_required) return <Navigate replace to={destination === '/signup/terms' ? '/dashboard' : destination}/>
  async function submit(event) {
    event.preventDefault(); setBusy(true); setError('')
    try {
      await request('/api/auth/terms', { method: 'POST', body: terms })
      await refreshSession()
    } catch (err) { setError(err.message) } finally { setBusy(false) }
  }
  async function cancel() {
    setBusy(true); setError('')
    try { await logout() }
    catch (err) { setError(err.message) } finally { setBusy(false) }
  }
  return <div className="native-auth-page"><header className="native-auth-header"><Logo/><Link to="/terms">Read terms</Link></header>
    <main className="native-auth-main"><section className="native-auth-card"><h1>One more step.</h1><p className="native-auth-subtitle">Review these terms before setting up your study profile. If you’re under 18, ask your parent or guardian to join you.</p>
      <form onSubmit={submit}><TermsFields value={terms} onChange={setTerms}/>{error && <p role="alert" className="native-auth-error">{error}</p>}<button className="btn btn-primary native-auth-submit" disabled={busy}>{busy ? 'Please wait…' : 'Accept and continue'}</button></form>
      <button type="button" className="native-auth-text" disabled={busy} onClick={cancel}>Not now — sign out</button>
    </section></main></div>
}
