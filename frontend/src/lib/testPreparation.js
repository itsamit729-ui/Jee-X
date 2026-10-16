export const INSTRUCTION_SECONDS = 90
export function instructionSeconds(startedAt, now = Date.now()) {
  return Math.max(0, Math.ceil((startedAt + INSTRUCTION_SECONDS * 1000 - now) / 1000))
}
export function canEnterTest(session, now = Date.now()) {
  return Boolean(session?.paper && !session.loading && !session.error && instructionSeconds(session.startedAt, now) === 0)
}
export function testInstructions({ exam = 'jee_main', mock = false, pyq = false, durationMinutes = null } = {}, paper = null) {
  const isMock = mock || Boolean(paper?.is_mock)
  const types = new Set(paper?.questions?.map(q => q.type) || [])
  const numericPenalty = paper?.questions?.find(q => q.type === 'numerical')?.marks_wrong ?? (isMock || pyq ? 1 : 0)
  const rules = exam === 'mht_cet'
    ? ['Physics and Chemistry: +1 per correct answer. Mathematics: +2.', 'No negative marking. Choose one correct option per question.']
    : exam === 'bitsat'
      ? ['Correct answer: +3. Incorrect answer: −1. Unanswered: 0.', 'Choose one correct option per question.']
      : [isMock || numericPenalty === 1 ? 'Correct answer: +4. Incorrect answer: −1, including numerical questions. Unanswered: 0.' : 'Correct answer: +4. Incorrect MCQ: −1. Incorrect numerical answer: 0. Unanswered: 0.', 'Choose one option for MCQs. For numerical questions, enter a number; decimals and negative values are supported.']
  if (types.has('multi_correct')) rules.push('For multiple-correct questions, select every option you believe is correct. Follow the marking shown with the question.')
  if (exam === 'mht_cet' && isMock) rules.push('First 90 minutes: Physics and Chemistry. Next 90 minutes: Mathematics. You cannot return to the first section once it closes.')
  rules.push(isMock ? 'The exam timer starts when you press Enter test. It submits automatically when time runs out.' : 'Your solving time starts when you press Enter test. Submit when you finish to see your score.')
  rules.push('Use the question navigator to move between questions. You can change or clear an answer before submitting.')
  rules.push('Keep this page open. Refreshing or leaving can lose this local session. Answers and available solutions appear after submission.')
  return { title: paper?.title || (isMock ? 'Your mock test' : 'Your practice set'),
    exam: ({ jee_main: 'JEE Main', mht_cet: 'MHT-CET', bitsat: 'BITSAT' })[exam] || 'Test',
    count: paper?.questions?.length ?? null,
    minutes: paper?.duration_sec ? Math.round(paper.duration_sec / 60) : isMock ? 180 : durationMinutes,
    timed: isMock, rules }
}
