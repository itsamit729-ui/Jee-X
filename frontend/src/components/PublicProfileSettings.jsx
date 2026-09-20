import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { useAuth0 } from '@auth0/auth0-react'
import { request } from '../lib/api.js'
import '../public-profile.css'

export default function PublicProfileSettings({ username }) {
  const { getAccessTokenSilently } = useAuth0()
  const [form, setForm] = useState(null)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const [message, setMessage] = useState('')
  const [retry, setRetry] = useState(0)
  useEffect(() => {
    let active = true
    setError('')
    ;(async () => {
      try {
        const data = await request('/api/profile/public-settings', { token: await getAccessTokenSilently() })
        if (active) { setForm(data) }
      } catch (e) { if (active) setError(e.message) }
    })()
    return () => { active = false }
  }, [getAccessTokenSilently, retry])
  function update(key, value) { setForm(f => ({ ...f, [key]: value })); setMessage('') }
  async function save(e) {
    e.preventDefault(); setBusy(true); setError(''); setMessage('')
    try {
      const data = await request('/api/profile/public-settings', { method: 'PATCH', token: await getAccessTokenSilently(), body: form })
      setForm(data); setMessage('Public profile updated.')
    } catch (e) { setError(e.message) } finally { setBusy(false) }
  }
  async function copy() {
    try { await navigator.clipboard.writeText(`${window.location.origin}/u/${encodeURIComponent(username)}`); setMessage('Profile link copied.') }
    catch { setError('Could not copy. Open your public profile and copy its address.') }
  }
  return <section className="public-settings pp-card">
    <p className="pp-eyebrow">YOUR PRESENCE</p><h2>Public profile</h2>
    <p className="pp-muted">Every student has a public profile. Your email, date of birth, shipping details and test answers stay private. Leaderboard visibility is managed separately in Rankings.</p>
    {error && <p role="alert">{error} {!form && <button onClick={() => setRetry(n => n+1)}>Retry</button>}</p>}
    {!form && !error && <p role="status">Loading profile settings…</p>}
    {form && <form onSubmit={save}>
      <fieldset disabled={busy} className="pp-fields">
        <p className="pp-muted">Anyone with your username or link can view your current exam cohort, rating, badges and finalized rated contest history.</p>
        <label htmlFor="public-name">Public display name <span className="pp-muted">(optional)</span></label>
        <input id="public-name" className="input" maxLength={80} value={form.display_name} onChange={e => update('display_name', e.target.value)} placeholder="Use a name you’re comfortable sharing" />
        <label htmlFor="public-bio">Short bio</label>
        <textarea id="public-bio" className="input" rows={3} maxLength={280} value={form.bio} onChange={e => update('bio', e.target.value)} placeholder="What are you working towards?" />
        <small className="pp-muted">{form.bio.length}/280</small>
        <label className="pp-check"><input type="checkbox" checked={form.show_activity} onChange={e => update('show_activity', e.target.checked)} />Show daily-question activity and streaks</label>
        <button className="btn btn-primary" type="submit">{busy ? 'Saving…' : 'Save public profile'}</button>
      </fieldset>
    </form>}
    <div className="pp-actions"><Link className="btn btn-secondary" to={`/u/${encodeURIComponent(username)}`}>View public profile</Link><button className="btn btn-secondary" onClick={copy}>Copy profile link</button></div>
    {message && <p role="status">{message}</p>}
  </section>
}
