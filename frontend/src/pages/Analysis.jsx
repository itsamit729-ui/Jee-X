import { useEffect, useRef, useState } from 'react'
import { useNavigate, useLocation } from 'react-router-dom'
import { useAuth } from '../auth/AuthContext.jsx'
import { AnalysisDashboard } from '../crackjee/screens.jsx'
import AppHeader from '../components/AppHeader.jsx'
import RankPredictor from '../components/RankPredictor.jsx'
import { api } from '../lib/api.js'
import { savePendingFreeTest } from '../lib/pendingFreeTest.js'

const SUBJECTS = ['Physics', 'Chemistry', 'Mathematics']

// Maps the rich in-memory mock result to the backend's TestAttemptIn shape.
// We store `score` as the count of correct answers (so it's consistent with
// `total_questions` and the dashboard's "X / Y" cards); the +4/-1 marks total
// stays a display-only figure inside AnalysisDashboard.
function toAttemptPayload(result) {
  const attempted = result.correct + result.incorrect
  const subject_breakdown = {}
  SUBJECTS.forEach((s) => {
    const d = result.subjectScores?.[s]
    if (d) subject_breakdown[s] = { correct: d.correct, total: d.total }
  })
  return {
    test_type: 'full_mock',
    score: result.correct,
    total_questions: result.total,
    accuracy: attempted > 0 ? Math.round((result.correct / attempted) * 100) : 0,
    avg_time_seconds: result.total > 0 ? result.totalTime / result.total : 0,
    subject_breakdown,
  }
}

export default function Analysis() {
  const navigate = useNavigate()
  const { state } = useLocation()
  const { isAuthenticated } = useAuth()
  const result = state?.result
  const submittedRef = useRef(false)
  const [attemptId, setAttemptId] = useState(null)

  // Save the attempt exactly once, when we have a fresh result in hand.
  useEffect(() => {
    if (!result || submittedRef.current) return
    submittedRef.current = true
    const payload = toAttemptPayload(result)
    ;(async () => {
      try {
        if (!isAuthenticated) throw new Error('not-authenticated')
        const saved = await api.submitTestAttempt(payload)
        setAttemptId(saved.id)
      } catch {
        // Not signed in / not onboarded yet — bridge it through localStorage
        // so the Dashboard picks it up once the profile exists.
        savePendingFreeTest(payload)
      }
    })()
  }, [result, isAuthenticated])

  return (
    <div className="crackjee-root">
      <AppHeader />
      <AnalysisDashboard
        result={result}
        onHome={() => navigate('/dashboard')}
        onBuddy={() => navigate('/buddy', { state: { result } })}
      />
      {attemptId && (
        <main className="wrap page" style={{ paddingTop: 0 }}>
          <RankPredictor attemptId={attemptId} />
        </main>
      )}
    </div>
  )
}
