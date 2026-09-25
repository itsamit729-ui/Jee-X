import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { ArrowUpRight } from 'lucide-react'
import { request } from '../lib/api.js'
import RatingBadge from './RatingBadge.jsx'

export default function RatingSummary() {

  const [rating, setRating] = useState(null)
  const [error, setError] = useState(false)

  useEffect(() => {
    let active = true
    ;(async () => {
      try {
        const data = await request('/api/ranking/me', {})
        if (active) setRating(data)
      } catch { if (active) setError(true) }
    })()
    return () => { active = false }
  }, [])

  const index = rating?.tiers?.findIndex((t) => t.title === rating.title) ?? -1

  let subtitle = 'Loading your progress…'
  if (error) subtitle = 'Open rankings to load your rating.'
  else if (rating) {
    subtitle = rating.rating
      ? `${rating.points_to_next ? `${rating.points_to_next} points to ${rating.next_tier.title}` : 'Highest tier unlocked'} · Peak ${rating.peak}`
      : `${rating.placements_completed}/3 placement contests complete`
  }

  return (
    <Link to="/ranking" className="panel rating-summary-card">
      <RatingBadge index={index} size={30} />
      <div style={{ flex: 1, minWidth: 0 }}>
        <strong>{rating ? `${rating.title}${rating.rating ? ` · ${rating.rating.toLocaleString()}` : ''}` : 'Jee Edge Rating'}</strong>
        <p className="muted" style={{ fontSize: 12, marginTop: 5 }}>{subtitle}</p>
      </div>
      <ArrowUpRight size={18} className="faint" />
    </Link>
  )
}
