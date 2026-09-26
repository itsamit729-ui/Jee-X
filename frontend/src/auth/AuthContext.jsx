import { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { request, setCsrfToken } from '../lib/api.js'
import { setCacheIdentity, invalidateCache } from '../lib/requestCache.js'
import './auth.css'

const AuthContext = createContext(null)
export function safeReturnTo(value) {
  return typeof value === 'string' && value.startsWith('/') && !value.startsWith('//') && !value.includes('\\') && !/[\r\n]/.test(value)
    && !/^\/(login|signup|forgot-password|reset-password|verify-email)([/?#]|$)/.test(value) ? value : '/dashboard'
}

export function AuthProvider({ children }) {
  const navigate = useNavigate()
  const [user, setUser] = useState(null)
  const [isLoading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [expired, setExpired] = useState(false)
  const refreshSession = useCallback(async () => {
    setError('')
    try {
      const session = await request('/api/auth/session')
      setCacheIdentity(session.authenticated ? String(session.user.id ?? session.user.email) : null)
      setUser(session.authenticated ? session.user : null)
      return session
    } catch (e) { setError('We could not check your session. Please try again.'); throw e }
    finally { setLoading(false) }
  }, [])
  useEffect(() => { refreshSession().catch(() => {}) }, [refreshSession])
  useEffect(() => {
    const onExpired = () => { invalidateCache(); setExpired(true) }
    window.addEventListener('jee-session-expired', onExpired)
    return () => window.removeEventListener('jee-session-expired', onExpired)
  }, [])
  const login = useCallback(async (email, password) => {
    await request('/api/auth/login', { method: 'POST', body: { email, password } })
    // Detect blocked cross-site cookies before pretending the login worked.
    const session = await refreshSession()
    if (!session.authenticated) throw new Error('Your browser could not save the session. Open Jee Edge on its primary site and try again.')
    setExpired(false)
    return session.user
  }, [refreshSession])
  const logout = useCallback(async () => {
    setError('')
    try {
      await request('/api/auth/logout', { method: 'POST' })
      setCacheIdentity(null); setUser(null); setCsrfToken(null); setExpired(false); navigate('/', { replace: true })
    } catch (e) { setError('Could not sign out. Please retry when your connection is available.') }
  }, [navigate])
  const openLogin = useCallback(({ signup = false, returnTo = '/dashboard' } = {}) => {
    navigate(`${signup ? '/signup' : '/login'}?returnTo=${encodeURIComponent(safeReturnTo(returnTo))}`)
  }, [navigate])
  const value = useMemo(() => ({ user, isLoading, isAuthenticated: Boolean(user), error, refreshSession, login, logout, openLogin }),
    [user, isLoading, error, refreshSession, login, logout, openLogin])
  return <AuthContext.Provider value={value}>
    {error && <div className="native-auth-banner" role="alert">{error} <button onClick={() => refreshSession().catch(() => {})}>Retry</button></div>}
    {children}
    {expired && user && <SessionRenewal email={user.email} login={login} logout={logout} />}
  </AuthContext.Provider>
}

// Keep the exam component mounted when a session expires, preserving its answers.
function SessionRenewal({ email, login, logout }) {
  const [password, setPassword] = useState('')
  const [message, setMessage] = useState('')
  const [busy, setBusy] = useState(false)
  async function submit(e) {
    e.preventDefault(); setBusy(true); setMessage('')
    try { await login(email, password) } catch (err) { setMessage(err.message) } finally { setBusy(false) }
  }
  return <div className="native-auth-overlay"><section className="native-auth-card" role="dialog" aria-modal="true" aria-labelledby="renew-title">
    <h2 id="renew-title">Sign in to continue</h2><p>Your session ended. Your current screen is still open; exam timers continue running.</p>
    <form onSubmit={submit}><label htmlFor="renew-email">Email</label><input id="renew-email" type="email" autoComplete="username" value={email} readOnly />
    <label htmlFor="renew-password">Password</label><input id="renew-password" type="password" autoComplete="current-password" required value={password} onChange={e => setPassword(e.target.value)} autoFocus />
    {message && <p role="alert" className="native-auth-error">{message}</p>}<button className="btn btn-primary" disabled={busy}>{busy ? 'Signing in…' : 'Sign in again'}</button></form>
    <button className="native-auth-text" onClick={logout}>Sign out and leave this screen</button>
  </section></div>
}

export function useAuth() { return useContext(AuthContext) }
