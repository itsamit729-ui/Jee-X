import { useEffect, useState } from 'react'
import { Flame, Trophy } from 'lucide-react'
import { dailyQuestionService } from '../lib/dailyQuestion.js'

const CALENDAR_DAYS = 182
const WEEKDAY_LABELS = ['', 'Mon', '', 'Wed', '', 'Fri', '']
const MONTH_LABELS = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']

// A local calendar-day string, NOT Date#toISOString (which converts to UTC first).
// The backend computes "today" in IST; a browser not set to UTC would otherwise have
// every cell's date silently shift by a day, so a just-solved question never lit up.
function localISODate(d) {
  const y = d.getFullYear()
  const m = String(d.getMonth() + 1).padStart(2, '0')
  const day = String(d.getDate()).padStart(2, '0')
  return `${y}-${m}-${day}`
}

// A GitHub/LeetCode-style contribution heatmap of daily-question activity, built
// from GET /api/daily-question/calendar. Weeks run left (oldest) to right
// (this week), Sunday at the top of each column.
function buildWeeks(activityDates, today) {
  const activeSet = new Set(activityDates)
  const start = new Date(today)
  start.setDate(start.getDate() - (CALENDAR_DAYS - 1))
  start.setDate(start.getDate() - start.getDay()) // back up to the preceding Sunday

  const weeks = []
  const cursor = new Date(start)
  while (cursor <= today) {
    const week = []
    for (let d = 0; d < 7; d++) {
      const iso = localISODate(cursor)
      week.push({ date: iso, month: cursor.getMonth(), active: activeSet.has(iso), future: cursor > today })
      cursor.setDate(cursor.getDate() + 1)
    }
    weeks.push(week)
  }
  return weeks
}

// A month label sits above the first week column that crosses into it.
function monthLabels(weeks) {
  let lastMonth = null
  return weeks.map((week) => {
    const month = week[0].month
    const isNew = month !== lastMonth
    lastMonth = month
    return isNew ? MONTH_LABELS[month] : ''
  })
}

export default function StreakCalendar() {

  const [state, setState] = useState('loading') // loading | ready | error
  const [data, setData] = useState(null)
  const [error, setError] = useState('')

  useEffect(() => {
    let cancelled = false
    ;(async () => {
      try {
        const res = await dailyQuestionService.getCalendar()
        if (!cancelled) {
          setData(res)
          setState('ready')
        }
      } catch (e) {
        if (!cancelled) {
          setError(e.message)
          setState('error')
        }
      }
    })()
    return () => { cancelled = true }
  }, [])

  if (state === 'loading') {
    return (
      <div className="panel">
        <h2 className="panel-title">Daily streak</h2>
        <p className="muted" style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <span className="spin" aria-hidden="true" />Loading your streak
        </p>
      </div>
    )
  }

  if (state === 'error') {
    return (
      <div className="panel">
        <h2 className="panel-title">Daily streak</h2>
        <p className="alert" role="alert">{error || "Couldn't load your streak."}</p>
      </div>
    )
  }

  const today = new Date()
  today.setHours(0, 0, 0, 0)
  const weeks = buildWeeks(data.activity_dates, today)
  const months = monthLabels(weeks)

  return (
    <div className="panel">
      <h2 className="panel-title">Daily streak</h2>

      <div className="streak-badges">
        <div className="streak-badge streak-badge-current">
          <Flame size={22} aria-hidden="true" />
          <div>
            <div className="streak-badge-value">{data.current_streak}</div>
            <div className="streak-badge-label">Current streak</div>
          </div>
        </div>
        <div className="streak-badge streak-badge-best">
          <Trophy size={22} aria-hidden="true" />
          <div>
            <div className="streak-badge-value">{data.longest_streak}</div>
            <div className="streak-badge-label">Longest streak</div>
          </div>
        </div>
      </div>

      <div className="streak-grid-scroll">
        <div className="streak-grid-wrap">
          <div className="streak-months-row">
            <span className="streak-weekday-spacer" aria-hidden="true" />
            <div className="streak-months">
              {months.map((m, i) => <span key={i} className="streak-month">{m}</span>)}
            </div>
          </div>
          <div className="streak-grid-body">
            <div className="streak-weekdays" aria-hidden="true">
              {WEEKDAY_LABELS.map((label, i) => <span key={i}>{label}</span>)}
            </div>
            <div className="streak-grid">
              {weeks.map((week, wi) => (
                <div key={wi} className="streak-col">
                  {week.map((day) => (
                    <span
                      key={day.date}
                      className="streak-cell"
                      data-active={day.active ? 'true' : undefined}
                      data-future={day.future ? 'true' : undefined}
                      title={day.future ? undefined : `${day.date}${day.active ? ' — solved' : ' — not solved'}`}
                    />
                  ))}
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>

      <div className="faint streak-legend">
        <span className="streak-cell" />
        <span>Less</span>
        <span className="streak-cell" data-active="true" />
        <span>Solved</span>
      </div>
    </div>
  )
}
