import { useEffect, useState } from 'react'
import { Link, Navigate, useNavigate, useSearchParams } from 'react-router-dom'
import { ArrowLeft, ArrowRight, CheckCircle2, Eye, EyeOff, Mail } from 'lucide-react'
import { Logo } from '../components/Brand.jsx'
import { request } from '../lib/api.js'
import { safeReturnTo, useAuth } from './AuthContext.jsx'

const COPY = {
  login: ['Welcome back.', 'Your next good session starts here.', 'Sign in'],
  signup: ['Make room for progress.', 'Create your Jee Edge account.', 'Create account'],
  forgot: ['Forgot your password?', 'We’ll send you a link to choose a new one.', 'Send reset link'],
  reset: ['A fresh start.', 'Choose a new password for your account.', 'Update password'],
  verify: ['Check your inbox.', 'Verify your email to start practising.', 'Verify email'],
  change: ['Update your password.', 'A long, unique password keeps your account protected.', 'Save new password'],
}

function PasswordField({ id, label = 'Password', value, onChange, newPassword = false }) {
  const [visible, setVisible] = useState(false)
  return <div className="native-auth-field"><label htmlFor={id}>{label}</label><div className="native-auth-password">
    <input id={id} type={visible ? 'text' : 'password'} autoComplete={newPassword ? 'new-password' : 'current-password'} required minLength={newPassword ? 15 : 1} maxLength={128} value={value} onChange={onChange} aria-describedby={newPassword ? `${id}-hint` : undefined} />
    <button type="button" onClick={() => setVisible(!visible)} aria-label={visible ? `Hide ${label.toLowerCase()}` : `Show ${label.toLowerCase()}`} aria-pressed={visible}>{visible ? <EyeOff size={18}/> : <Eye size={18}/>}</button>
  </div>{newPassword && <small id={`${id}-hint`}>At least 15 characters. A phrase is easier to remember.</small>}</div>
}

export default function AuthPage({ mode = 'login' }) {
  const { login, refreshSession, user, isAuthenticated, isLoading } = useAuth()
  const navigate = useNavigate()
  const [params] = useSearchParams()
  const returnTo = safeReturnTo(params.get('returnTo'))
  const [email, setEmail] = useState(user?.email || '')
  const [password, setPassword] = useState('')
  const [currentPassword, setCurrentPassword] = useState('')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const [message, setMessage] = useState('')
  const [linkToken] = useState(() => new URLSearchParams(window.location.hash.slice(1)).get('token') || '')
  useEffect(() => {
    if (window.location.hash) window.history.replaceState(null, '', window.location.pathname + window.location.search)
  }, [])
  const [title, subtitle, label] = COPY[mode]
  const emailVisible = ['login', 'signup', 'forgot'].includes(mode) || (mode === 'verify' && !linkToken)
  const passwordVisible = ['login', 'signup', 'reset', 'change'].includes(mode)

  if (!isLoading && isAuthenticated && ['login', 'signup'].includes(mode)) return <Navigate replace to={user.onboarded ? returnTo : '/onboarding'} />

  async function submit(event) {
    event.preventDefault(); setError(''); setBusy(true)
    try {
      if (mode === 'login') {
        const account = await login(email, password)
        navigate(account.onboarded ? returnTo : '/onboarding', { replace: true })
      } else {
        const paths = { signup: 'register', forgot: 'forgot-password', reset: 'reset-password', verify: linkToken ? 'verify-email' : 'resend-verification', change: 'change-password' }
        const body = mode === 'signup' ? { email, password } : mode === 'reset' ? { token: linkToken, password }
          : mode === 'verify' && linkToken ? { token: linkToken } : mode === 'change' ? { current_password: currentPassword, password } : { email }
        const result = await request(`/api/auth/${paths[mode]}`, { method: 'POST', body })
        setPassword(''); setCurrentPassword('')
        setMessage(mode === 'change' ? 'Password updated. Other devices have been signed out.' : result.message)
        if (mode === 'change' || mode === 'reset') await refreshSession()
      }
    } catch (err) { setError(err.message) } finally { setBusy(false) }
  }

  return <div className="native-auth-page">
    <header className="native-auth-header"><Logo /><Link to="/" className="native-auth-back"><ArrowLeft size={15}/>Back to Jee Edge</Link></header>
    <main className="native-auth-main"><section className="native-auth-card" aria-labelledby="auth-heading">
      <span className="native-auth-eyebrow">YOUR STUDY SPACE</span><h1 id="auth-heading">{title}</h1><p className="native-auth-subtitle">{subtitle}</p>
      {message ? <div className="native-auth-success" role="status"><CheckCircle2 size={25}/><p>{message}</p>
        {['signup', 'forgot'].includes(mode) && <small>Use the most recent email. Links expire after 30 minutes.</small>}
        <Link className="btn btn-primary" to={mode === 'change' ? '/profile' : '/login'}>{mode === 'change' ? 'Back to profile' : 'Back to sign in'}<ArrowRight size={16}/></Link>
        {mode === 'signup' && <Link to="/verify-email">Resend verification email</Link>}
      </div> : <form onSubmit={submit}>
        {emailVisible && <div className="native-auth-field"><label htmlFor="auth-email">Email address</label><input id="auth-email" type="email" autoComplete="username" placeholder="you@example.com" required maxLength={254} value={email} onChange={e => setEmail(e.target.value)} /></div>}
        {mode === 'change' && <PasswordField id="current-password" label="Current password" value={currentPassword} onChange={e => setCurrentPassword(e.target.value)} />}
        {passwordVisible && <PasswordField id="auth-password" value={password} onChange={e => setPassword(e.target.value)} newPassword={mode !== 'login'} />}
        {mode === 'login' && <div className="native-auth-forgot"><Link to="/forgot-password">Forgot password?</Link></div>}
        {mode === 'verify' && linkToken && <p className="native-auth-link-note"><Mail size={20}/>Confirm your email address to activate your account.</p>}
        {mode === 'reset' && !linkToken && <p className="native-auth-error">Open the link from your reset email, or <Link to="/forgot-password">request a new one</Link>.</p>}
        {error && <p className="native-auth-error" role="alert">{error}</p>}
        <button className="btn btn-primary native-auth-submit" disabled={busy || (mode === 'reset' && !linkToken)}>{busy ? 'Please wait…' : mode === 'verify' && !linkToken ? 'Send verification link' : label}{!busy && <ArrowRight size={17}/>}</button>
      </form>}
      {!message && <div className="native-auth-bottom">
        {mode === 'login' ? <><p>New here? <Link to={`/signup?returnTo=${encodeURIComponent(returnTo)}`}>Create an account</Link></p><Link to="/verify-email">Resend verification email</Link></>
          : mode === 'signup' ? <><p>Already have an account? <Link to="/login">Sign in</Link></p><small>New accounts start with a fresh profile.</small></>
          : <Link to={mode === 'change' ? '/profile' : '/login'}>{mode === 'change' ? 'Back to profile' : 'Back to sign in'}</Link>}
      </div>}
    </section></main><footer className="native-auth-footer">A little practice. A clearer next step.</footer>
  </div>
}
