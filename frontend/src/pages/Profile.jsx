import PublicProfileSettings from '../components/PublicProfileSettings.jsx'
import RatingSummary from '../components/RatingSummary.jsx'
import { useEffect, useRef, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useAuth } from '../auth/AuthContext.jsx'
import { Pencil } from 'lucide-react'
import { API_URL, api } from '../lib/api.js'
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
  const { user } = useAuth()
  const navigate = useNavigate()

  const [profile, setProfile] = useState(null)
  const [loading, setLoading] = useState(true)
  const [editing, setEditing] = useState(false)
  const [form, setForm] = useState(null)
  const [usernameStatus, setUsernameStatus] = useState(null)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')
  const [saved, setSaved] = useState(false)
  const [avatarBusy, setAvatarBusy] = useState(false)
  const [avatarError, setAvatarError] = useState('')
  const [avatarMessage, setAvatarMessage] = useState('')
  const [avatarVersion, setAvatarVersion] = useState(0)
  const debounceRef = useRef(null)

  useEffect(() => {
    (async () => {
      try {
        const me = await api.me()
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
  }, [navigate])

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
      const updated = await api.updateProfile(form)
      setProfile(updated)
      setEditing(false)
      setSaved(true)
    } catch (err) {
      setError(err.message)
    } finally {
      setSaving(false)
    }
  }

  const changeAvatar = async (event) => {
    const file = event.target.files?.[0]
    event.target.value = ''
    if (!file) return
    setAvatarMessage('')
    setAvatarError('')
    if (!['image/jpeg', 'image/png', 'image/webp'].includes(file.type) || file.size > 4 * 1024 * 1024) {
      setAvatarError('Choose a JPEG, PNG or WebP image under 4 MB.')
      return
    }
    setAvatarBusy(true)
    try {
      const result = await api.uploadAvatar(file)
      setProfile(current => ({ ...current, avatar_url: result.avatar_url }))
      setAvatarVersion(n => n + 1)
      setAvatarMessage('Photo updated.')
    } catch (err) { setAvatarError(err.message) }
    finally { setAvatarBusy(false) }
  }

  const removeAvatar = async () => {
    setAvatarBusy(true)
    setAvatarError('')
    setAvatarMessage('')
    try {
      await api.removeAvatar()
      setProfile(current => ({ ...current, avatar_url: null }))
      setAvatarMessage('Photo removed.')
    } catch (err) { setAvatarError(err.message) }
    finally { setAvatarBusy(false) }
  }

  if (loading || !profile) return <Loader fullScreen label="Loading your profile" />

  const classText = (c) => (c === 'dropper' ? 'Dropper' : `Class ${c}`)

  return (
    <div className="crackjee-root">
      <AppHeader />
      <main className="wrap-narrow page">
        <div className="page-head">
          <h1 className="page-title">Profile</h1><Link to="/account/security" className="btn btn-secondary btn-sm">Change password</Link>
        </div>

        <div className="panel">
          <div className="profile-head">
            <div className="avatar" role="img" aria-label={profile.avatar_url ? 'Your profile photo' : `Initials ${initials(profile.name)}`}>
              {profile.avatar_url ? <img src={`${API_URL}${profile.avatar_url}?v=${avatarVersion}`} alt="" /> : initials(profile.name)}
            </div>
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

          <div className="profile-photo-actions">
            <input id="profile-photo" className="visually-hidden" type="file" accept="image/jpeg,image/png,image/webp" onChange={changeAvatar} disabled={avatarBusy} />
            <label htmlFor="profile-photo" className={`btn btn-secondary btn-sm ${avatarBusy ? 'profile-photo-disabled' : ''}`}>{avatarBusy ? 'Updating photo…' : profile.avatar_url ? 'Change photo' : 'Add photo'}</label>
            {profile.avatar_url && <button type="button" className="btn btn-quiet btn-sm" disabled={avatarBusy} onClick={removeAvatar}>Remove photo</button>}
            <span className="muted">JPEG, PNG or WebP · up to 4 MB</span>
          </div>
          {avatarError && <p className="alert" role="alert">{avatarError}</p>}
          {avatarMessage && <p className="hint hint-ok" role="status">{avatarMessage}</p>}

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
