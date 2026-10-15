export const PYQ_EXAMS = [
  ['jee_main', 'JEE Main', 'Year & shift mocks · MCQs + numerical questions'],
  ['mht_cet', 'MHT-CET', 'Year & shift mocks · Subject practice'],
  ['bitsat', 'BITSAT', 'Memory-based question practice'],
]
export const pyqExam = value => PYQ_EXAMS.some(([code]) => code === value) ? value : 'mht_cet'
export const pyqLabel = exam => PYQ_EXAMS.find(([code]) => code === exam)?.[1] || 'PYQs'
export function practiceOffset(value) {
  const n = Number(value)
  return Number.isInteger(n) && n >= 0 && n <= 2_000_000 ? n : 0
}
export function paperMarks(exam, subjects) {
  return subjects.reduce((total, s) => total + s.available * (exam === 'jee_main' ? 4 : exam === 'bitsat' ? 3 : s.code === 'MATH' ? 2 : 1), 0)
}
export function archiveReturn(params) {
  const target = new URLSearchParams({ exam: pyqExam(params.get('pyq')) })
  for (const key of ['year', 'shift', 'subject', 'offset', 'count', 'view']) {
    if (params.has(key)) target.set(key, params.get(key))
  }
  return `/pyq?${target}`
}
export function resultAnswer(question, result) {
  if (question?.type === 'numerical') {
    if (result.answer_min == null || result.answer_max == null) return 'See solution'
    return result.answer_min === result.answer_max ? String(result.answer_min) : `${result.answer_min} to ${result.answer_max}`
  }
  return question?.options.filter(o => result.correct_option_ids.includes(o.id)).map(o => o.label).join(', ') || 'See solution'
}
