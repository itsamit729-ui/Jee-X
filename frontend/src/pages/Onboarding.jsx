import { useEffect, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '../auth/AuthContext.jsx'
import { api } from '../lib/api.js'
import { readPendingFreeTest, clearPendingFreeTest } from '../lib/pendingFreeTest.js'
import { Logo } from '../components/Brand.jsx'

const CLASSES = [['11', 'Class 11'], ['12', 'Class 12'], ['dropper', 'Dropper']]

export default function Onboarding() {
  const { user, refreshSession } = useAuth()
  const navigate = useNavigate()

  const [form, setForm] = useState({
    name: user?.name || '',
    username: '',
    dob: '',
    class_level: '11',
  })
  const [usernameStatus, setUsernameStatus] = useState(null) // null | 'checking' | 'available' | 'taken' | 'invalid'
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState('')
  const debounceRef = useRef(null)

  // Redirect straight to the dashboard if this account already has a profile.
  useEffect(() => {
    (async () => {
      try {
        const me = await api.me()
        if (me.onboarded) navigate('/dashboard', { replace: true })
      } catch {
        // ignore — user can still fill the form
      }
    })()
  }, [navigate])

  const handleUsernameChange = (value) => {
    const clean = value.replace(/\s/g, '').toLowerCase()
    setForm((f) => ({ ...f, username: clean }))

    if (debounceRef.current) clearTimeout(debounceRef.current)

    if (clean.length < 3) {
      setUsernameStatus(clean.length === 0 ? null : 'invalid')
      return
    }
    if (!/^[a-z0-9_]{3,20}$/.test(clean)) {
      setUsernameStatus('invalid')
      return
    }

    setUsernameStatus('checking')
    debounceRef.current = setTimeout(async () => {
      try {
        const res = await api.checkUsername(clean)
        setUsernameStatus(res.available ? 'available' : 'taken')
      } catch {
        setUsernameStatus(null)
      }
    }, 400)
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    setError('')

    if (usernameStatus !== 'available') {
      setError('Choose an available username to continue.')
      return
    }

    setSubmitting(true)
    try {
      await api.onboard(form)
      await refreshSession()

      const pending = readPendingFreeTest()
      if (pending) {
        const { savedAt, ...payload } = pending
        try {
          await api.submitTestAttempt(payload)
        } catch {
          // Non-fatal — don't block getting into the app over this.
        } finally {
          clearPendingFreeTest()
        }
      }

      navigate('/dashboard', { replace: true })
    } catch (err) {
      setError(err.message)
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <div className="crackjee-root auth">
      <div className="auth-inner">
        <Logo />
        <h1>Set up your profile</h1>
        <p className="sub">It takes a minute, and it's how we rank you against other aspirants.</p>

        <form onSubmit={handleSubmit}>
          <div className="field">
            <label className="field-label" htmlFor="name">Full name</label>
            <input id="name" type="text" className="input" value={form.name} autoComplete="name"
              onChange={(e) => setForm((f) => ({ ...f, name: e.target.value }))} placeholder="Rahul Sharma" required />
          </div>

          <div className="field">
            <label className="field-label" htmlFor="username">Username</label>
            <div className="input-prefix">
              <span aria-hidden="true">@</span>
              <input id="username" type="text" className="input" value={form.username} autoComplete="username"
                aria-describedby="username-hint" onChange={(e) => handleUsernameChange(e.target.value)} placeholder="rahul_23" required />
            </div>
            <p id="username-hint" className={`hint ${usernameStatus === 'available' ? 'hint-ok' : usernameStatus === 'taken' || usernameStatus === 'invalid' ? 'hint-err' : ''}`} aria-live="polite">
              {usernameStatus === 'checking' && 'Checking availability…'}
              {usernameStatus === 'available' && `@${form.username} is available.`}
              {usernameStatus === 'taken' && 'That username is taken.'}
              {usernameStatus === 'invalid' && '3 to 20 characters: letters, numbers and underscores.'}
              {usernameStatus === null && 'Shown on leaderboards instead of your name.'}
            </p>
          </div>

          <div className="field">
            <label className="field-label" htmlFor="dob">Date of birth</label>
            <input id="dob" type="date" className="input" value={form.dob}
              onChange={(e) => setForm((f) => ({ ...f, dob: e.target.value }))} required />
          </div>

          <div className="field">
            <span className="field-label" id="class-label">Class</span>
            <div className="seg" role="group" aria-labelledby="class-label">
              {CLASSES.map(([value, text]) => (
                <button key={value} type="button" aria-pressed={form.class_level === value}
                  onClick={() => setForm((f) => ({ ...f, class_level: value }))}>{text}</button>
              ))}
            </div>
          </div>

          {error && <p className="alert" role="alert">{error}</p>}

          <button type="submit" className="btn btn-primary btn-lg btn-block" disabled={submitting}>
            {submitting ? <><span className="spin" aria-hidden="true" />Saving</> : 'Continue to dashboard'}
          </button>
        </form>
      </div>
    </div>
  )
}
