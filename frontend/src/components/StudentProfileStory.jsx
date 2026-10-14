import { ArrowUpRight, Copy, Globe2, Target, Trophy } from 'lucide-react'
import RatingBadge from './RatingBadge.jsx'
import { API_URL } from '../lib/api.js'
import '../public-profile.css'

export const examLabel = exam => ({ jee_main: 'JEE Main', jee_advanced: 'JEE Advanced', mht_cet: 'MHT-CET', bitsat: 'BITSAT' }[exam] || 'Entrance exam')

// Calendar arithmetic stays in UTC after obtaining the IST calendar date.
// This keeps the same activity day visible in every visitor's timezone.
export function activityCalendar(dates, now = new Date()) {
  const today = new Date(`${new Intl.DateTimeFormat('en-CA', { timeZone: 'Asia/Kolkata', year: 'numeric', month: '2-digit', day: '2-digit' }).format(now)}T00:00:00Z`)
  const first = new Date(today)
  first.setUTCDate(first.getUTCDate() - 181)
  const active = new Set(dates)
  return Array.from({ length: 182 }, (_, index) => {
    const date = new Date(first)
    date.setUTCDate(first.getUTCDate() + index)
    const iso = date.toISOString().slice(0, 10)
    return { date: iso, active: active.has(iso) }
  })
}

export function ProfileActivity({ activity }) {
  const days = activityCalendar(activity.dates)
  return <section className="pp-card pp-consistency">
    <div className="pp-section-heading"><div><p className="pp-eyebrow">SHOWING UP</p><h2>Consistency, one day at a time.</h2></div><span className="pp-chip">Daily questions</span></div>
    <div className="pp-streak-numbers"><p><strong>{activity.current_streak}</strong><span>day current streak</span></p><p><strong>{activity.longest_streak}</strong><span>day best streak</span></p><p><strong>{days.filter(day => day.active).length}</strong><span>active days in 182 days</span></p></div>
    <div className="pp-heatmap" aria-label="Daily questions completed in the last 182 days, India Standard Time">
      {days.map(day => <time key={day.date} dateTime={day.date} className={day.active ? 'is-active' : ''} title={`${day.date}: ${day.active ? 'completed' : 'no completion'}`}><span className="visually-hidden">{day.date}: {day.active ? 'completed' : 'no completion'}.</span></time>)}
    </div><p className="pp-muted pp-calendar-note">Last 182 days · India Standard Time <span><i /> No completion <i className="is-active" /> Completed</span></p>
  </section>
}

export default function StudentProfileStory({ profile, onShare, actions, message, children, isOwner = false, avatarVersion = 0 }) {
  const r = profile.rating
  const cohort = `${examLabel(profile.exam)} · ${profile.target_year}`
  const rated = r.rating != null
  const NameHeading = isOwner ? 'h2' : 'h1'
  return <>
    <section className="pp-card pp-hero">
      <div className="pp-cover" aria-hidden="true"><span>THE NEXT CHAPTER IS YOURS.</span><Target size={108} strokeWidth={.7} /></div>
      <div className="pp-hero-body"><div className="pp-avatar" aria-hidden="true">{profile.avatar_url ? <img src={`${API_URL}${profile.avatar_url}?v=${avatarVersion}`} alt="" /> : (profile.display_name || profile.username).slice(0, 2).toUpperCase()}</div>
        <div className="pp-identity"><p className="pp-eyebrow"><Globe2 size={12} aria-hidden="true" /> Public student profile</p><NameHeading>{profile.display_name || profile.username}</NameHeading><p className="pp-muted">@{profile.username}</p></div>
        <div className="pp-hero-actions">{actions}<button className="btn btn-secondary btn-sm" onClick={onShare}><Copy size={14} aria-hidden="true" />Share profile</button></div>
      </div>
      <div className="pp-hero-foot"><span className="pp-chip"><Target size={14} aria-hidden="true" />{cohort}</span><span className="pp-muted">{rated ? `${r.title} · ${r.contests} rated contests` : 'Building a preparation journey'}</span></div>
    </section>
    {message && <p className="pp-feedback" role="status">{message}</p>}
    {children}
    <div className="pp-story-grid">
      <section className="pp-card pp-about"><p className="pp-eyebrow">BEHIND THE USERNAME</p><h2>About {profile.display_name || `@${profile.username}`}</h2>{profile.bio ? <p className="pp-bio">{profile.bio}</p> : <p className="pp-muted">This student hasn’t added a bio yet.</p>}<div className="pp-goal"><Target size={22} aria-hidden="true" /><div><small>Exam goal</small><strong>{examLabel(profile.exam)} <span>{profile.target_year}</span></strong></div></div></section>
      <section className="pp-card pp-next-step"><p className="pp-eyebrow">THE CLIMB</p><h2>{rated ? r.title : 'Every journey starts somewhere.'}</h2><p className="pp-muted">{rated ? (r.next_tier ? `${r.points_to_next} rating points to ${r.next_tier.title}.` : 'The highest rating tier has been reached.') : `${r.placements_completed} of 3 placement contests completed. A rating unlocks after all three.`}</p>{!rated && <div className="pp-placement-steps" aria-label={`${r.placements_completed} of 3 placements complete`}>{[1, 2, 3].map(n => <span key={n} className={n <= r.placements_completed ? 'is-complete' : ''}>{n <= r.placements_completed ? '✓' : n}</span>)}</div>}<p className="pp-rating-note"><ArrowUpRight size={16} aria-hidden="true" />Contest rating measures performance here, not predicted exam rank.</p></section>
    </div>
    <section className="pp-stats" aria-label="Rating overview"><div className="pp-card"><small>Current rating</small><strong>{r.rating ?? 'Unrated'}</strong><span>{r.title}</span></div><div className="pp-card"><small>Personal best</small><strong>{r.peak ?? '—'}</strong><span>Peak contest rating</span></div><div className="pp-card"><small>Cohort rank</small><strong>{profile.rank ? `#${profile.rank}` : '—'}</strong><span>{profile.rank ? cohort : 'Not currently ranked'}</span></div><div className="pp-card"><small>Rated contests</small><strong>{r.contests}</strong><span>In this exam cohort</span></div></section>
    <section className="pp-card"><div className="pp-section-heading"><div><p className="pp-eyebrow">MILESTONES</p><h2>Earned along the way.</h2></div><Trophy size={22} aria-hidden="true" /></div>{r.badges.length ? <div className="pp-badges">{r.badges.map(b => <div key={b.title}><RatingBadge index={Math.min(9, Math.floor(b.minimum / 500))} /><strong>{b.title}</strong><small>{b.title === r.title ? 'Current tier' : 'Unlocked'}</small></div>)}</div> : <p className="pp-muted">The first milestone is completing three placement contests. Earned rating badges will appear here.</p>}</section>
    {profile.activity && <ProfileActivity activity={profile.activity} />}
  </>
}
