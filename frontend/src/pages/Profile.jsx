import StudentOmrId from '../components/StudentOmrId.jsx'
import PublicProfileSettings from '../components/PublicProfileSettings.jsx'
import RatingSummary from '../components/RatingSummary.jsx'
import { useEffect, useRef, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useAuth } from '../auth/AuthContext.jsx'
import { ExternalLink, Pencil } from 'lucide-react'
import { api, request } from '../lib/api.js'
import AppHeader from '../components/AppHeader.jsx'
import { Loader } from '../components/Brand.jsx'
import StreakCalendar from '../components/StreakCalendar.jsx'
import StudentProfileStory from '../components/StudentProfileStory.jsx'
import ProfileLearning from '../components/ProfileLearning.jsx'
import '../public-profile.css'

const CLASSES = [['11', 'Class 11'], ['12', 'Class 12'], ['dropper', 'Dropper']]

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
  const [loadVersion, setLoadVersion] = useState(0)
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
  const usernameRequest = useRef(0)
  const [section, setSection] = useState('public')
  const [publicEditing, setPublicEditing] = useState(false)
  const [publicProfile, setPublicProfile] = useState(null)
  const [publicError, setPublicError] = useState('')
  const [publicVersion, setPublicVersion] = useState(0)
  const [shareMessage, setShareMessage] = useState('')

  useEffect(() => () => { clearTimeout(debounceRef.current); usernameRequest.current++ }, [])
  useEffect(() => {
    if (!profile?.username) return
    let active = true
    setPublicProfile(current => current?.username === profile.username ? current : null); setPublicError('')
    request(`/api/public-profiles/${encodeURIComponent(profile.username)}`).then(data => {
      if (active) setPublicProfile(data)
    }).catch(e => { if (active) setPublicError(e.message) })
    return () => { active = false }
  }, [profile?.username, publicVersion])

  async function shareProfile() {
    try { await navigator.clipboard.writeText(`${window.location.origin}/u/${encodeURIComponent(profile.username)}`); setShareMessage('Public profile link copied.') }
    catch { setShareMessage('Open your public profile and copy the address to share it.') }
  }

  useEffect(() => {
    let active = true
    setLoading(true)
    setError('')
    ;(async () => {
      try {
        const me = await api.me()
        if (!active) return
        if (!me.onboarded) {
          navigate('/onboarding', { replace: true })
          return
        }
        setProfile(me.profile)
        setForm(me.profile)
      } catch (e) {
        if (active) setError(e.message || 'Could not load your profile.')
      } finally {
        if (active) setLoading(false)
      }
    })()
    return () => { active = false }
  }, [navigate, loadVersion])

  const handleUsernameChange = (value) => {
    clearTimeout(debounceRef.current)
    const requestId = ++usernameRequest.current
    const clean = value.replace(/\s/g, '').toLowerCase()
    setForm((f) => ({ ...f, username: clean }))
    setSaved(false)

    if (clean === profile.username) {
      setUsernameStatus('unchanged')
      return
    }
    if (clean.length < 3 || !/^[a-z0-9_]{3,20}$/.test(clean)) {
      setUsernameStatus('invalid')
      return
    }
    setUsernameStatus('checking')
    debounceRef.current = setTimeout(async () => {
      try {
        const res = await api.checkUsername(clean)
        if (requestId === usernameRequest.current) setUsernameStatus(res.available ? 'available' : 'taken')
      } catch {
        if (requestId === usernameRequest.current) setUsernameStatus(null)
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
    clearTimeout(debounceRef.current)
    usernameRequest.current++
    setForm(profile)
    setEditing(false)
    setError('')
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    setError('')
    if (usernameStatus === 'taken' || usernameStatus === 'invalid' || usernameStatus === 'checking') {
      setError('Fix the username before saving.')
      return
    }
    setSaving(true)
    try {
      const updated = await api.updateProfile({ name: form.name, username: form.username, dob: form.dob, class_level: form.class_level })
      setProfile(current => ({ ...updated, avatar_url: current.avatar_url ? `/api/public-profiles/${updated.username}/avatar` : null }))
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
      setPublicVersion(n => n + 1)
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
      setPublicVersion(n => n + 1)
      setAvatarMessage('Photo removed.')
    } catch (err) { setAvatarError(err.message) }
    finally { setAvatarBusy(false) }
  }

  if (loading) return <Loader fullScreen label="Loading your profile" />
  if (!profile) return <div className="crackjee-root"><AppHeader /><main className="wrap page"><div className="panel" role="alert"><p>{error || 'Could not load your profile.'}</p><button className="btn btn-secondary" onClick={() => setLoadVersion(v => v + 1)}>Try again</button></div></main></div>

  const classText = (c) => (c === 'dropper' ? 'Dropper' : `Class ${c}`)

  return (
    <div className="crackjee-root">
      <AppHeader />
      <main className="wrap page student-profile-page">
        <div className="pp-owner-heading"><div><p className="pp-eyebrow">YOUR SPACE ON JEE EDGE</p><h1>Your profile.</h1><p className="pp-muted">A little about you. Every step of your journey.</p></div><Link to={`/u/${encodeURIComponent(profile.username)}`} className="btn btn-secondary btn-sm">View as a visitor <ExternalLink size={14} aria-hidden="true" /></Link></div>
        <nav className="pp-owner-tabs" aria-label="Profile sections">
          {[['public', 'Public profile'], ['progress', 'My progress'], ['account', 'Account details']].map(([key, label]) => <button key={key} type="button" aria-current={section === key ? 'page' : undefined} onClick={() => { setSection(key); setShareMessage('') }}>{label}</button>)}
        </nav>
        {section === 'public' && <div className="pp-owner-section">
          <div className="pp-owner-notice"><span>Everyone can view your student profile. You choose your public name, bio and activity sharing.</span></div>
          {publicError && <div className="pp-card" role="alert"><p>{publicError}</p><button className="btn btn-secondary" onClick={() => setPublicVersion(n => n + 1)}>Retry public profile</button></div>}
          {!publicProfile && !publicError && <div className="pp-card" role="status">Loading your public profile…</div>}
          {publicProfile && <StudentProfileStory isOwner profile={publicProfile} onShare={shareProfile} avatarVersion={avatarVersion} message={shareMessage} actions={<button className="btn btn-primary btn-sm" aria-expanded={publicEditing} aria-controls="public-profile-editor" onClick={() => setPublicEditing(open => !open)}><Pencil size={14} aria-hidden="true" />{publicEditing ? 'Close editor' : 'Edit public profile'}</button>}>
          {publicEditing && <div id="public-profile-editor"><PublicProfileSettings username={profile.username} onSaved={() => setPublicVersion(n => n + 1)} />
            <section className="pp-card"><p className="pp-eyebrow">YOUR PUBLIC PHOTO</p><h2>Put a face to your profile.</h2>
          <div className="profile-photo-actions">
            <input id="profile-photo" className="visually-hidden" type="file" accept="image/jpeg,image/png,image/webp" onChange={changeAvatar} disabled={avatarBusy} />
            <label htmlFor="profile-photo" className={`btn btn-secondary btn-sm ${avatarBusy ? 'profile-photo-disabled' : ''}`}>{avatarBusy ? 'Updating photo…' : profile.avatar_url ? 'Change photo' : 'Add photo'}</label>
            {profile.avatar_url && <button type="button" className="btn btn-quiet btn-sm" disabled={avatarBusy} onClick={removeAvatar}>Remove photo</button>}
            <span className="muted">JPEG, PNG or WebP · up to 4 MB</span>
          </div>
          {avatarError && <p className="alert" role="alert">{avatarError}</p>}
          {avatarMessage && <p className="hint hint-ok" role="status">{avatarMessage}</p>}

            </section></div>}
          </StudentProfileStory>}
        </div>}
        {section === 'progress' && <div className="pp-owner-section"><ProfileLearning /><RatingSummary /><StreakCalendar /></div>}
        {section === 'account' && <div className="pp-owner-section pp-account-grid"><section className="pp-card">
          <div className="pp-section-heading"><div><p className="pp-eyebrow">ONLY YOU CAN SEE THIS</p><h2>Account details</h2></div>{!editing && <button className="btn btn-secondary btn-sm" onClick={startEditing}><Pencil size={14} aria-hidden="true" />Edit details</button>}</div>
          <p className="pp-muted">Your full name, birthday and email stay in your account. Your username is public.</p>
          {!editing ? (
            <dl className="dl">
              <div><dt>Full name</dt><dd>{profile.name}</dd></div>
              <div><dt>Username</dt><dd>@{profile.username}</dd></div>
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
                <button type="submit" className="btn btn-primary" disabled={saving || usernameStatus === 'checking' || usernameStatus === 'taken' || usernameStatus === 'invalid'}>
                  {saving ? <><span className="spin" aria-hidden="true" />Saving</> : 'Save changes'}
                </button>
                <button type="button" className="btn btn-secondary" onClick={cancelEditing} disabled={saving}>Cancel</button>
              </div>
            </form>
          )}

          {saved && !editing && <p className="hint hint-ok" style={{ marginTop: 18 }} role="status">Changes saved.</p>}
        </section>

        <section className="pp-card pp-account-tools"><p className="pp-eyebrow">YOUR STUDENT IDENTITY</p><h2>Ready for class.</h2><StudentOmrId studentId={profile.id} /><p className="pp-muted">Your permanent OMR ID is for matching your offline test sheets to your account.</p><Link to="/account/security" className="btn btn-secondary">Account security</Link><p className="pp-muted">Manage your password, Google sign-in and active sessions.</p></section>
        </div>}
      </main>
    </div>
  )
}
