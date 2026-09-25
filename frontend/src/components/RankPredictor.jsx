import { useEffect, useState } from 'react'
import { predictorService } from '../lib/predictor.js'
import { GOOD, PEN } from '../crackjee/ui.js'

const CONFIDENCE = {
  full_length_mock: { label: 'Full-length mock', tone: 'is-good' },
  partial_practice: { label: 'Partial practice', tone: 'is-warn' },
  insufficient_data: { label: 'Not enough data yet', tone: '' },
}

const COLLEGE_PAGE_SIZE = 8

const fmtRank = (n) => (n == null ? '—' : n.toLocaleString('en-IN'))
const fmtPercentile = (n) => (n == null ? '—' : `${n.toFixed(2)}%`)

// After any submitted test attempt, shows an estimated JEE Main percentile/CRL
// rank (scaled proportionally to a 300-mark paper) and historical JoSAA
// college matches. See backend/app/services/predictor.py for the pipeline
// and its cautions — this is historical reference data, not an official
// NTA percentile or an admission promise.
export default function RankPredictor({ attemptId }) {

  const [state, setState] = useState('loading') // loading | ready | error
  const [prediction, setPrediction] = useState(null)
  const [error, setError] = useState('')
  const [showAllColleges, setShowAllColleges] = useState(false)

  useEffect(() => {
    if (!attemptId) return
    let cancelled = false
    setState('loading')
    setShowAllColleges(false)
    ;(async () => {
      try {
        const data = await predictorService.getPrediction(attemptId)
        if (!cancelled) {
          setPrediction(data)
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
  }, [attemptId])

  if (!attemptId) return null

  if (state === 'loading') {
    return (
      <div className="panel predictor-panel">
        <h2 className="panel-title">Rank &amp; college predictor</h2>
        <p className="muted" style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <span className="spin" aria-hidden="true" />Estimating your national rank
        </p>
      </div>
    )
  }

  if (state === 'error') {
    return (
      <div className="panel predictor-panel">
        <h2 className="panel-title">Rank &amp; college predictor</h2>
        <p className="alert" role="alert">{error || "Couldn't load your prediction."}</p>
      </div>
    )
  }

  const { percentile, rank, colleges, confidence, disclaimer, scaled_marks_300: scaledMarks, reference_year: referenceYear } = prediction
  const badge = CONFIDENCE[confidence] || { label: confidence, tone: '' }
  const visibleColleges = showAllColleges ? colleges : colleges.slice(0, COLLEGE_PAGE_SIZE)

  return (
    <div className="panel predictor-panel">
      <div className="panel-head">
        <h2 className="panel-title">Rank &amp; college predictor</h2>
        <span className={`tag ${badge.tone}`}>{badge.label}</span>
      </div>

      {confidence === 'insufficient_data' ? (
        <>
          <p className="muted">
            Scaled to a JEE Main 300-mark paper, this attempt is worth about <strong>{Math.round(scaledMarks)}</strong> marks
            {referenceYear ? ` — below the range our ${referenceYear} reference data covers.` : '.'}
          </p>
          <p className="hint" style={{ marginTop: 8 }}>{disclaimer}</p>
        </>
      ) : (
        <>
          <div className="stats" style={{ marginTop: 4 }}>
            <div className="stat">
              <div className="stat-value">{Math.round(scaledMarks)}<span style={{ fontSize: 14, fontWeight: 600, color: 'var(--ink-3)' }}> /300</span></div>
              <div className="stat-label">Scaled marks (JEE Main)</div>
            </div>
            <div className="stat">
              <div className="stat-value">{fmtPercentile(percentile.high)}</div>
              <div className="stat-label">Est. percentile ({fmtPercentile(percentile.low)}+)</div>
            </div>
            <div className="stat">
              <div className="stat-value">{fmtRank(rank.low)}</div>
              <div className="stat-label">Est. CRL rank (up to {fmtRank(rank.high)})</div>
            </div>
          </div>

          <p className="hint" style={{ marginTop: 14 }}>{disclaimer}</p>

          {colleges.length > 0 ? (
            <>
              <div className="panel-head" style={{ marginTop: 22, marginBottom: 4 }}>
                <h3 className="panel-title" style={{ fontSize: 14.5, marginBottom: 0 }}>Historical college matches</h3>
                <span className="tag">{referenceYear} JoSAA</span>
              </div>
              <div className="rows">
                {visibleColleges.map((c, i) => (
                  <div key={i} className="row is-top-aligned">
                    <span
                      className="dot"
                      style={{ marginTop: 7, background: c.meets_conservative_estimate ? GOOD : PEN }}
                      title={c.meets_conservative_estimate ? 'Within your conservative estimate' : 'Within your optimistic estimate only'}
                    />
                    <div className="row-main">
                      <div style={{ fontWeight: 600 }}>{c.institute}</div>
                      <div className="faint" style={{ fontSize: 13 }}>
                        {c.program}
                        {c.nirf_rank ? <span style={{ whiteSpace: 'nowrap' }}> · NIRF #{c.nirf_rank}</span> : ''}
                      </div>
                    </div>
                    <div style={{ textAlign: 'right' }}>
                      <div className="row-value">{fmtRank(c.closing_rank)}</div>
                      <div className="faint" style={{ fontSize: 11, fontWeight: 600, textTransform: 'uppercase', letterSpacing: '.02em' }}>
                        {c.quota} quota
                      </div>
                    </div>
                  </div>
                ))}
              </div>
              {colleges.length > COLLEGE_PAGE_SIZE && (
                <button
                  type="button"
                  className="btn btn-quiet btn-sm"
                  style={{ marginTop: 8 }}
                  onClick={() => setShowAllColleges((v) => !v)}
                >
                  {showAllColleges ? 'Show fewer' : `Show all ${colleges.length} matches`}
                </button>
              )}
              <p className="hint" style={{ marginTop: 10 }}>
                Historical closing rank, general category only — not an admission promise. AI (all-India) applies to
                everyone; OS (other-state) is shown as the safe default for NITs since we don't know your home
                state — your home state's own NIT is usually easier to get into than this via its HS quota.
              </p>
              <div className="faint" style={{ display: 'flex', flexWrap: 'wrap', gap: 16, marginTop: 6, fontSize: 12.5 }}>
                <span><span className="dot" style={{ background: GOOD, marginRight: 5, verticalAlign: 'middle' }} />within conservative estimate</span>
                <span><span className="dot" style={{ background: PEN, marginRight: 5, verticalAlign: 'middle' }} />optimistic only</span>
              </div>
            </>
          ) : (
            <p className="muted" style={{ marginTop: 16 }}>
              No historical matches in our current reference data for this rank range yet.
            </p>
          )}
        </>
      )}
    </div>
  )
}
