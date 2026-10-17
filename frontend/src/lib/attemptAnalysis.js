// Pure helpers for the reopenable attempt analysis (/results/:attemptId).

export const OUTCOME_SQUARE = { correct: 'correct', wrong: 'wrong' }
export const OUTCOME_WORD = { correct: 'Correct', wrong: 'Wrong', skipped: 'Skipped' }

// A question is "slow" when it took more than 1.5x its expected time.
export const isSlow = (q) => q.expected_time_sec > 0 && q.time_taken_sec > 1.5 * q.expected_time_sec

// A wrong answer given in under half the expected time is likely a careless slip rather than a gap in the concept.
export const isRushed = (q) => q.outcome === 'wrong' && q.expected_time_sec > 0 && q.time_taken_sec > 0 &&
  q.time_taken_sec < 0.5 * q.expected_time_sec

export const QUESTION_FILTERS = [
  ['all', 'All', () => true],
  ['wrong', 'Wrong', (q) => q.outcome === 'wrong'],
  ['rushed', 'Rushed', isRushed],
  ['skipped', 'Skipped', (q) => q.outcome === 'skipped'],
  ['slow', 'Slow', isSlow],
]

export function filterQuestions(questions, key) {
  const match = QUESTION_FILTERS.find(([k]) => k === key)?.[2] || (() => true)
  return questions.filter(match)
}

const fmt = (n) => (Number.isInteger(n) ? String(n) : String(Math.round(n * 100) / 100))

export function yourAnswer(q) {
  if (q.type === 'numerical') return q.numeric_answer === null || q.numeric_answer === undefined ? '–' : fmt(q.numeric_answer)
  const labels = q.options.filter((o) => q.selected_option_ids.includes(o.id)).map((o) => o.label)
  return labels.length ? labels.join(', ') : '–'
}

export function correctAnswer(q) {
  if (q.type === 'numerical') {
    if (q.answer_min === null || q.answer_min === undefined) return 'See solution'
    return q.answer_min === q.answer_max ? fmt(q.answer_min) : `${fmt(q.answer_min)} to ${fmt(q.answer_max)}`
  }
  const labels = q.options.filter((o) => q.correct_option_ids.includes(o.id)).map((o) => o.label)
  return labels.length ? labels.join(', ') : 'See solution'
}

// Share of a chapter's questions answered correctly (skipped ones count against it).
export const correctRate = (c) => (c.total ? c.correct / c.total : 0)

// A chapter needs at least this many questions in the paper before it is called weak or strong.
export const MIN_CHAPTER_QUESTIONS = 2

// Chapters below 50% of questions correct need work; the rest are strong. Chapters with too few
// questions to judge are returned separately.
export function splitChapters(chapters) {
  const judged = chapters.filter((c) => c.total >= MIN_CHAPTER_QUESTIONS)
  return {
    weak: judged.filter((c) => correctRate(c) < 0.5).sort((a, b) => correctRate(a) - correctRate(b)),
    strong: judged.filter((c) => correctRate(c) >= 0.5).sort((a, b) => correctRate(b) - correctRate(a)),
    tooFew: chapters.filter((c) => c.total > 0 && c.total < MIN_CHAPTER_QUESTIONS),
  }
}

// The chapters worth charting: the ones with the most questions in this paper (up to `limit`).
export function chartChapters(chapters, limit = 8) {
  return [...chapters].sort((a, b) => b.total - a.total || correctRate(a) - correctRate(b)).slice(0, limit)
}

// Practice page deep link for one chapter (the practice builder reads ?subject= and ?chapter=).
export const practiceChapterPath = (chapter) =>
  `/practice?subject=${encodeURIComponent(chapter.subject_code)}&chapter=${encodeURIComponent(chapter.chapter_id)}`

// The result shape the AI Buddy (/buddy) answers "how did I do?" and "weak chapters" from.
export function buddyResult(data) {
  const { summary, chapters } = data
  return {
    score: summary.score, maxScore: summary.max_score,
    correct: summary.correct, incorrect: summary.wrong, unattempted: summary.skipped,
    chapterScores: Object.fromEntries(chapters.map((c) => [c.name, { correct: c.correct, total: c.total }])),
  }
}

// Change since the previous attempt of the same paper, or null when there is none to compare with.
export function changeSincePrevious(meta, summary) {
  const prev = meta.previous
  if (!prev || prev.score === null || prev.score === undefined) return null
  return { score: summary.score - prev.score, accuracy: Math.round((summary.accuracy - (prev.accuracy || 0)) * 10) / 10 }
}

export function attemptKind(row) {
  if (row.kind === 'daily') return 'Daily question'
  if (['bitsat', 'mht_cet'].includes(row.pattern)) return row.is_mock ? 'Shift mock' : 'PYQ practice'
  if (row.title === 'Roadmap baseline assessment') return 'Baseline'
  if (row.is_mock) return 'Full mock'
  if (row.kind === 'free_diagnostic') return 'Free test'
  return 'Practice'
}

// Where "Start another" leads from a result.
export function nextTestPath(meta) {
  if (['bitsat', 'mht_cet'].includes(meta.pattern)) return `/pyq?exam=${meta.pattern}`
  if (meta.kind === 'daily') return '/daily'
  if (meta.is_mock && meta.title === 'JEE Main full mock') return '/practice?mock=1'
  return '/practice'
}

export const minutes = (seconds) => Math.round((seconds || 0) / 60)
