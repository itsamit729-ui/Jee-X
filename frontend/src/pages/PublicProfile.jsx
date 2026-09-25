import { useEffect, useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { useAuth0 } from '@auth0/auth0-react'
import { LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid } from 'recharts'
import { Logo } from '../components/Brand.jsx'
import RatingBadge from '../components/RatingBadge.jsx'
import { API_URL, request } from '../lib/api.js'
import '../public-profile.css'

const dateLabel = value => new Date(value).toLocaleDateString(undefined, { month: 'short', day: 'numeric', year: 'numeric' })
export default function PublicProfile() {
  const { username } = useParams()
  const navigate = useNavigate()
  const { isAuthenticated } = useAuth0()
  const [search, setSearch] = useState('')
  const [profile, setProfile] = useState(null)
  const [history, setHistory] = useState(null)
  const [page, setPage] = useState(1)
  const [error, setError] = useState('')
  const [historyError, setHistoryError] = useState('')
  const [retry, setRetry] = useState(0)
  const [message, setMessage] = useState('')
  useEffect(() => { setPage(1); setMessage('') }, [username])
  useEffect(() => {
    let active = true
    setProfile(null); setError('')
    if (username) request(`/api/public-profiles/${encodeURIComponent(username)}`).then(data => { if (active) setProfile(data) }).catch(e => { if (active) setError(e.message) })
    return () => { active = false }
  }, [username, retry])
  useEffect(() => {
    let active = true
    setHistory(null); setHistoryError('')
    if (profile) request(`/api/public-profiles/${encodeURIComponent(profile.username)}/contests?page=${page}`).then(data => { if (active) setHistory(data) }).catch(e => { if (active) setHistoryError(e.message) })
    return () => { active = false }
  }, [profile, page, retry])
  async function copy() {
    try { await navigator.clipboard.writeText(window.location.href); setMessage('Profile link copied.') }
    catch { setMessage('Copy the profile address from your browser to share it.') }
  }
  function find(e) { e.preventDefault(); const value=search.trim().toLowerCase(); if (value) navigate(`/u/${encodeURIComponent(value)}`) }
  const r = profile?.rating
  const cohort = profile ? `${profile.exam.replace('_', ' ').toUpperCase()} · ${profile.target_year}` : ''
  return <div className="pp-page">
    <header className="pp-nav"><Logo to="/" /><nav aria-label="Profile navigation"><Link to="/students">Find a student</Link><Link to={isAuthenticated ? '/profile' : '/ranking'}>{isAuthenticated ? 'My profile' : 'Sign in'}</Link></nav></header>
    <main className="pp-main">
      <form className="pp-search" onSubmit={find}><label htmlFor="student-search">Find a student</label><div><input id="student-search" className="input" value={search} onChange={e => setSearch(e.target.value)} placeholder="Exact username" pattern="[A-Za-z0-9_]{3,20}" maxLength={20} required /><button className="btn btn-primary">Search</button></div></form>
      {!username && <section className="pp-card pp-intro"><p className="pp-eyebrow">THE PEOPLE BEHIND THE RATINGS</p><h1>Every climb has a story.</h1><p className="pp-muted">Find a student by username to explore their rating, badges and contest journey. Every active student has a public profile.</p><Link to="/ranking">Explore the leaderboard →</Link></section>}
      {username && !profile && !error && <p role="status">Loading profile…</p>}
      {error && <section className="pp-card" role="alert"><h1>Profile unavailable</h1><p>{error}</p><p className="pp-muted">The account may be unavailable, or the username may have changed.</p><button className="btn btn-secondary" onClick={() => setRetry(x => x+1)}>Try again</button></section>}
      {profile && <>
        <section className="pp-card pp-hero"><div className="pp-avatar" aria-hidden="true">{profile.avatar_url ? <img src={`${API_URL}${profile.avatar_url}`} alt="" /> : profile.username.slice(0,2).toUpperCase()}</div><div className="pp-identity"><p className="pp-eyebrow">{cohort}</p><h1>{profile.display_name || profile.username}</h1><p className="pp-muted">@{profile.username}</p>{profile.bio && <p className="pp-bio">{profile.bio}</p>}</div><button className="btn btn-secondary" onClick={copy}>Share profile</button></section>
        {message && <p role="status">{message}</p>}
        <section className="pp-stats" aria-label="Rating overview"><div className="pp-card"><small>Current rating · {r.title}</small><strong>{r.rating ?? 'Unrated'}</strong>{r.rating === null && <span>{r.placements_completed}/3 placement contests</span>}</div><div className="pp-card"><small>Peak rating</small><strong>{r.peak ?? '—'}</strong></div><div className="pp-card"><small>Cohort rank</small><strong>{profile.rank ? `#${profile.rank}` : '—'}</strong><span>{profile.rank ? cohort : 'Not currently ranked'}</span></div><div className="pp-card"><small>Rated contests</small><strong>{r.contests}</strong></div></section>
        <section className="pp-card"><div className="pp-section-heading"><h2>Rating journey</h2><span className="pp-muted">Latest 100 rated results · {cohort}</span></div>
          {profile.history.length ? <><div className="pp-chart" role="img" aria-label={`Rating journey across ${profile.history.length} contests. Latest rating ${profile.history.at(-1).after}. Exact results are in the contest history below.`}><ResponsiveContainer width="100%" height="100%"><LineChart data={profile.history} margin={{ top: 15, right: 20, bottom: 15, left: 0 }}><CartesianGrid strokeDasharray="3 3" vertical={false}/><XAxis dataKey="date" tickFormatter={value => new Date(value).toLocaleDateString(undefined,{month:'short',day:'numeric'})} minTickGap={40}/><YAxis domain={['auto','auto']} width={48}/><Tooltip labelFormatter={dateLabel} formatter={value => [value,'Rating']}/><Line type="linear" dataKey="after" stroke="#d76a32" strokeWidth={3} dot={{r:4}} isAnimationActive={false}/></LineChart></ResponsiveContainer></div><p className="pp-muted">JeeX ratings measure contest performance, not predicted JEE AIR.</p></> : <p className="pp-empty">The first rated contest will start this journey.</p>}
        </section>
        <section className="pp-card"><div className="pp-section-heading"><h2>Earned badges</h2><span className="pp-muted">Peak milestones stay unlocked</span></div>{r.badges.length ? <div className="pp-badges">{r.badges.map(b => <div key={b.title}><RatingBadge index={Math.min(9,Math.floor(b.minimum/500))}/><strong>{b.title}</strong><small>{b.title === r.title ? 'Current tier' : 'Earned'}</small></div>)}</div> : <p className="pp-empty">Badges unlock after three placement contests.</p>}</section>
        {profile.activity && <section className="pp-card"><h2>Daily-question activity</h2><p>{profile.activity.current_streak} day current streak · {profile.activity.longest_streak} day longest streak</p><p className="pp-muted">Completed daily questions in the last 182 days, by India Standard Time.</p><div className="pp-activity">{profile.activity.dates.map(d => <time key={d} dateTime={d}>{dateLabel(`${d}T12:00:00Z`)}</time>)}</div>{!profile.activity.dates.length && <p className="pp-empty">No daily-question activity yet.</p>}</section>}
        <section className="pp-card"><div className="pp-section-heading"><h2>Contest history</h2><span className="pp-muted">Finalized rated results</span></div>
          {historyError && <p role="alert">{historyError} <button onClick={() => setRetry(n=>n+1)}>Retry</button></p>}
          {!history && !historyError && <p role="status">Loading contests…</p>}
          {history?.entries.length ? <div className="pp-table-wrap"><table><thead><tr><th>Contest</th><th>Score</th><th>Rank</th><th>Rating</th><th>Change</th></tr></thead><tbody>{history.entries.map((h,i) => <tr key={`${h.date}-${i}`}><td><strong>{h.contest}</strong><small>{dateLabel(h.date)}</small></td><td>{h.score}</td><td>#{h.rank}</td><td>{h.after}</td><td>{h.delta>0?'+':''}{h.delta}</td></tr>)}</tbody></table></div> : history && <p className="pp-empty">No rated results to show yet.</p>}
          {history && history.total>20 && <div className="pp-pagination"><button className="btn btn-secondary" disabled={page===1} onClick={()=>setPage(n=>n-1)}>Previous</button><span>Page {page} of {Math.ceil(history.total/20)}</span><button className="btn btn-secondary" disabled={page*20>=history.total} onClick={()=>setPage(n=>n+1)}>Next</button></div>}
        </section>
      </>}
    </main>
  </div>
}

