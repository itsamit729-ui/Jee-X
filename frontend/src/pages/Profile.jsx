import PublicProfileSettings from '../components/PublicProfileSettings.jsx'
import RatingSummary from '../components/RatingSummary.jsx'
import { useEffect, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth0 } from '@auth0/auth0-react'
import { Pencil } from 'lucide-react'
import { api } from '../lib/api.js'
import AppHeader from '../components/AppHeader.jsx'
import { Loader } from '../components/Brand.jsx'
import StreakCalendar from '../components/StreakCalendar.jsx'

const CLASSES = [['11', 'Class 11'], ['12', 'Class 12'], ['dropper', 'Dropper']]

function initials(name = '') {
  return name.trim().split(/\s+/).slice(0, 2).map((p) => p[0]?.toUpperCase()).join('')
}

// "2008-05-14" -> "14 May 2008", read as a local date so no timezone shifts it.
function formatDate(iso) {
  if (!iso) return 'Not set'
  const [y, m, d] = iso.split('-').map(Number)
  return new Date(y, m - 1, d).toLocaleDateString('en-IN', { day: 'numeric', month: 'long', year: 'numeric' })
}

export default function Profile() {
  const { getAccessTokenSilently, user } = useAuth0()
  const navigate = useNavigate()

  const [profile, setProfile] = useState(null)
  const [loading, setLoading] = useState(true)
  const [editing, setEditing] = useState(false)
  const [form, setForm] = useState(null)
  const [usernameStatus, setUsernameStatus] = useState(null)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')
  const [saved, setSaved] = useState(false)
  const debounceRef = useRef(null)

  useEffect(() => {
    (async () => {
      try {
        const token = await getAccessTokenSilently()
        const me = await api.me(token)
        if (!me.onboarded) {
          navigate('/onboarding', { replace: true })
          return
        }
        setProfile(me.profile)
        setForm(me.profile)
      } catch {
        navigate('/onboarding', { replace: true })
      } finally {
        setLoading(false)
      }
    })()
  }, [getAccessTokenSilently, navigate])

  const handleUsernameChange = (value) => {
    const clean = value.replace(/\s/g, '').toLowerCase()
    setForm((f) => ({ ...f, username: clean }))
    setSaved(false)

    if (clean === profile.username) {
      setUsernameStatus('unchanged')
      return
    }
    if (debounceRef.current) clearTimeout(debounceRef.current)
    if (clean.length < 3 || !/^[a-z0-9_]{3,20}$/.test(clean)) {
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

  const startEditing = () => {
    setForm(profile)
    setUsernameStatus('unchanged')
    setError('')
    setSaved(false)
    setEditing(true)
  }

  const cancelEditing = () => {
    setForm(profile)
    setEditing(false)
    setError('')
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    setError('')
    if (usernameStatus === 'taken' || usernameStatus === 'invalid') {
      setError('Fix the username before saving.')
      return
    }
    setSaving(true)
    try {
      const token = await getAccessTokenSilently()
      const updated = await api.updateProfile(token, form)
      setProfile(updated)
      setEditing(false)
      setSaved(true)
    } catch (err) {
      setError(err.message)
    } finally {
      setSaving(false)
    }
  }

  if (loading || !profile) return <Loader fullScreen label="Loading your profile" />

  const classText = (c) => (c === 'dropper' ? 'Dropper' : `Class ${c}`)

  return (
    <div className="crackjee-root">
      <AppHeader />
      <main className="wrap-narrow page">
        <div className="page-head">
          <h1 className="page-title">Profile</h1>
        </div>

        <div className="panel">
          <div className="profile-head">
            <div className="avatar" aria-hidden="true">{initials(profile.name)}</div>
            <div style={{ flex: 1, minWidth: 0 }}>
              <h2>{profile.name}</h2>
              <p className="muted">@{profile.username}</p>
            </div>
            {!editing && (
              <button type="button" className="btn btn-secondary btn-sm" onClick={startEditing}>
                <Pencil size={14} aria-hidden="true" />Edit
              </button>
            )}
          </div>

          {!editing ? (
            <dl className="dl">
              <div><dt>Email</dt><dd>{user?.email || 'Not set'}</dd></div>
              <div><dt>Date of birth</dt><dd>{formatDate(profile.dob)}</dd></div>
              <div><dt>Class</dt><dd>{classText(profile.class_level)}</dd></div>
            </dl>
          ) : (
            <form onSubmit={handleSubmit}>
              <div className="field">
                <label className="field-label" htmlFor="p-name">Full name</label>
                <input id="p-name" type="text" className="input" value={form.name}
                  onChange={(e) => { setForm((f) => ({ ...f, name: e.target.value })); setSaved(false) }} required />
              </div>
              <div className="field">
                <label className="field-label" htmlFor="p-username">Username</label>
                <div className="input-prefix">
                  <span aria-hidden="true">@</span>
                  <input id="p-username" type="text" className="input" value={form.username} aria-describedby="p-username-hint"
                    onChange={(e) => handleUsernameChange(e.target.value)} required />
                </div>
                <p id="p-username-hint" className={`hint ${usernameStatus === 'available' ? 'hint-ok' : usernameStatus === 'taken' || usernameStatus === 'invalid' ? 'hint-err' : ''}`} aria-live="polite">
                  {usernameStatus === 'checking' && 'Checking availability…'}
                  {usernameStatus === 'available' && `@${form.username} is available.`}
                  {usernameStatus === 'taken' && 'That username is taken.'}
                  {usernameStatus === 'invalid' && '3 to 20 characters: letters, numbers and underscores.'}
                </p>
              </div>
              <div className="field">
                <label className="field-label" htmlFor="p-dob">Date of birth</label>
                <input id="p-dob" type="date" className="input" value={form.dob}
                  onChange={(e) => { setForm((f) => ({ ...f, dob: e.target.value })); setSaved(false) }} required />
              </div>
              <div className="field">
                <span className="field-label" id="p-class-label">Class</span>
                <div className="seg" role="group" aria-labelledby="p-class-label">
                  {CLASSES.map(([value, text]) => (
                    <button key={value} type="button" aria-pressed={form.class_level === value}
                      onClick={() => { setForm((f) => ({ ...f, class_level: value })); setSaved(false) }}>{text}</button>
                  ))}
                </div>
              </div>

              {error && <p className="alert" role="alert">{error}</p>}

              <div style={{ display: 'flex', gap: 10, flexWrap: 'wrap' }}>
                <button type="submit" className="btn btn-primary" disabled={saving}>
                  {saving ? <><span className="spin" aria-hidden="true" />Saving</> : 'Save changes'}
                </button>
                <button type="button" className="btn btn-secondary" onClick={cancelEditing} disabled={saving}>Cancel</button>
              </div>
            </form>
          )}

          {saved && !editing && <p className="hint hint-ok" style={{ marginTop: 18 }} role="status">Changes saved.</p>}
        </div>

        <PublicProfileSettings username={profile.username} />
        <RatingSummary />
        <div style={{ marginTop: 20 }}>
          <StreakCalendar />
        </div>
      </main>
    </div>
  )
}
