import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { useAuth0 } from '@auth0/auth0-react'
import { Swords, ArrowUpRight, LockKeyhole } from 'lucide-react'
import AppHeader from '../components/AppHeader.jsx'
import RatingBadge from '../components/RatingBadge.jsx'
import { request } from '../lib/api.js'
import { useCrackJeeStyles } from '../crackjee/screens.jsx'
import '../ranking.css'

export default function Ranking() {
  useCrackJeeStyles()
  const { getAccessTokenSilently } = useAuth0()
  const [data, setData] = useState(null)
  const [board, setBoard] = useState(null)
  const [contests, setContests] = useState([])
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)
  const [page, setPage] = useState(1)
  const [retry, setRetry] = useState(0)
  useEffect(() => {
    let cancelled = false
    setError('')
    ;(async () => {
      try {
        const token = await getAccessTokenSilently()
        // One round trip instead of four (settle, then me/leaderboard/contests
        // separately) — each round trip to the DB carries real latency, and
        // that was stacking up into several seconds of load time.
        const { me, leaderboard, contests: events } = await request(`/api/ranking/dashboard?page=${page}`, { token })
        if (!cancelled) { setData(me); setBoard(leaderboard); setContests(events) }
      } catch (e) { if (!cancelled) setError(e.message) }
    })()
    return () => { cancelled = true }
  }, [getAccessTokenSilently, page, retry])
  async function toggleVisibility() {
    setBusy(true)
    try {
      const token = await getAccessTokenSilently()
      await request('/api/ranking/visibility', { token, method: 'PATCH', body: { visibility: data.visibility === 'hidden' ? 'username' : 'hidden' } })
      setRetry(x => x + 1)
    } catch (e) { setError(e.message) } finally { setBusy(false) }
  }
  const index = data?.tiers.findIndex(t => t.title === data.title) ?? -1
  const minimum = index >= 0 ? data.tiers[index].minimum : 0
  const progress = data?.rating ? data.next_tier ? (data.rating-minimum)/(data.next_tier.minimum-minimum)*100 : 100 : (data?.placements_completed || 0)/3*100
  return <div className="crackjee-root"><AppHeader/><main className="wrap ranking-page">
    <div className="ranking-heading"><div><p className="ranking-eyebrow">THE CLIMB / JEEX RATING</p><h1>Earn your place.</h1><p>One fair test. One step forward. Every milestone, yours to keep.</p></div><span className="cohort-label">{data ? `${data.exam.replace('_', ' ').toUpperCase()} · ${data.target_year}` : 'Your exam cohort'}</span></div>
    {error && <div className="ranking-panel" role="alert">{error} <button className="btn btn-secondary btn-sm" onClick={() => setRetry(x=>x+1)}>Retry</button></div>}
    {!data && !error && <p role="status">Loading your rating…</p>}
    {data && <>
      <section className="rating-hero" aria-label="Your rating"><div className="rating-hero-main"><RatingBadge index={index} size={44}/><div><p className="ranking-eyebrow">{data.title}</p><div className="rating-number">{data.rating?.toLocaleString() || 'Unrated'}{data.rating && <span> / 5,000</span>}</div><p>{data.rating ? `${data.points_to_next ? `${data.points_to_next} points to ${data.next_tier.title}` : 'Legend unlocked. Keep setting the standard.'}` : `${data.placements_completed} of 3 placement contests complete`}</p></div></div>
      <div className="rating-stats"><div><small>JeeX rank</small><strong>{board?.my_rank ? `#${board.my_rank}` : '—'}</strong></div><div><small>Peak rating</small><strong>{data.peak || '—'}</strong></div><div><small>Rated contests</small><strong>{data.contests}</strong></div></div>
      <div className="rating-track" role="progressbar" aria-label="Progress to next milestone" aria-valuenow={Math.round(progress)} aria-valuemin={0} aria-valuemax={100}><span style={{width:`${progress}%`}}/></div></section>
      <div className="ranking-columns"><section className="ranking-panel"><div className="ranking-section-title"><h2>Contest arena</h2><span>+4 correct · −1 wrong · 0 skipped</span></div><p className="ranking-muted">Common questions, server-timed attempts. Ratings are published after the contest closes.</p>
      {!contests.length && <div className="ranking-empty"><Swords size={30}/><h3>Your first contest is on its way.</h3><p>Scheduled contests will appear here. Keep practising while you wait.</p><Link className="btn btn-secondary" to="/subject-test">Go to practice <ArrowUpRight size={15}/></Link></div>}
      {contests.map(c => <article className="contest-row" key={c.id}><div><span className={`contest-status ${c.status}`}>{c.status}</span><h3>{c.title}</h3><p>{new Date(c.opens_at).toLocaleString()} · {Math.round(c.duration_sec/60)} min · {c.question_count} questions</p>{c.finalized && c.entry_id && <p>Score {c.score} · Contest rank #{c.rank}{!c.rated && ' · Unrated: fewer than two entrants'}</p>}</div>{c.status==='live' && !c.submitted ? <Link className="btn btn-primary btn-sm" to={`/ranked-test/${c.id}`}>{c.entry_id ? 'Resume' : 'Enter contest'}</Link> : <span className="ranking-muted">{c.submitted ? c.finalized ? 'Results published' : 'Submitted' : c.status==='closed' ? c.finalized ? 'Finalized' : 'Awaiting results' : 'Opens soon'}</span>}</article>)}
      </section><section className="ranking-panel"><h2>How the climb works</h2><ol className="ranking-rules"><li>Complete three contests to establish your rating.</li><li>Outperform expectations to gain points. Weaker results can lower your rating.</li><li>Your current title follows your rating. Earned badges stay forever.</li><li>Practice, daily questions and retests never change your rating.</li></ol><p className="ranking-muted">At least two entrants are needed for a rated contest. Starting an attempt counts as entering; saved answers are graded even if you leave.</p><p className="ranking-muted">JeeX rank is a platform position, not a predicted JEE AIR.</p></section></div>
      <section className="ranking-panel"><div className="ranking-section-title"><h2>Your badge collection</h2><span>{data.badges.length} / 10 unlocked</span></div><div className="badge-grid">{data.tiers.map((t,i) => {const unlocked=data.badges.some(b=>b.title===t.title); return <div key={t.title} className={`badge-item ${unlocked?'unlocked':'locked'} ${index===i?'current':''}`}><RatingBadge index={i}/><strong>{t.title}</strong><small>{t.minimum.toLocaleString()}–{t.maximum.toLocaleString()}</small><span>{index===i?'Current title':unlocked?'Earned':<><LockKeyhole size={11}/> Locked</>}</span></div>})}</div></section>
      <div className="ranking-columns"><section className="ranking-panel"><div className="ranking-section-title"><h2>Leaderboard</h2><Link to="/students">Find a student</Link><span>{board?.total || 0} active students</span></div><p className="ranking-muted">Same exam and attempt year. Active means a rated contest in the last 30 days. No rating decay.</p><button className="visibility-button" disabled={busy} onClick={toggleVisibility}>{data.visibility==='hidden'?'Show my username on the leaderboard':'Hide my username from the leaderboard'}</button>
      {board?.entries.length ? <div className="ranking-table-wrap"><table className="ranking-table"><thead><tr><th>JeeX rank</th><th>Student</th><th>Title</th><th>Rating</th></tr></thead><tbody>{board.entries.map(r=><tr key={r.username} className={r.is_me?'is-me':''}><td>#{r.rank}</td><td><Link to={`/u/${encodeURIComponent(r.username)}`}>{r.username}</Link>{r.is_me?' (you)':''}</td><td>{r.title}</td><td><strong>{r.rating}</strong></td></tr>)}</tbody></table></div> : <p className="ranking-empty">The leaderboard is waiting for its first rated students.</p>}
      {board?.total>50 && <div className="ranking-pagination"><button disabled={page===1} onClick={()=>setPage(p=>p-1)}>Previous</button><span>Page {page}</span><button disabled={page*50>=board.total} onClick={()=>setPage(p=>p+1)}>Next</button></div>}</section>
      <section className="ranking-panel"><h2>Rating history</h2>{!data.history.length && <p className="ranking-empty">Your first rated result starts the story.</p>}{data.history.map((h,i)=><div className="history-row" key={`${h.date}-${i}`}><div><strong>{h.contest}</strong><p>{new Date(h.date+'Z').toLocaleDateString()} · Contest #{h.rank}</p></div><div><strong>{h.after}</strong><span className={h.delta>=0?'delta-up':'delta-down'}>{h.delta>=0?'+':''}{h.delta}</span></div></div>)}</section></div>
    </>}
  </main></div>
}
