export function cetPhase(remaining) { return remaining > 5400 ? 'PC' : remaining > 0 ? 'MATH' : 'DONE' }
export function cetCanAnswer(subject, remaining) {
  const phase = cetPhase(remaining)
  return phase === 'PC' ? ['PHY', 'CHEM'].includes(subject) : phase === 'MATH' && subject === 'MATH'
}
export function cetStatus(id, answers, visited, review) {
  const answered = Boolean(answers[id]?.option_ids?.length)
  if (review[id]) return answered ? 'answered-review' : 'review'
  return answered ? 'answered' : visited[id] ? 'unanswered' : 'unvisited'
}
