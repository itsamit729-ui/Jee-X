export const teacherSections = [
  { key: 'overview', label: 'Overview', description: 'Your workspace at a glance' },
  { key: 'classes', label: 'Classes', description: 'Batches, invites and rosters' },
  { key: 'papers', label: 'Papers & answer sheets', description: 'Create, print and assign tests' },
  { key: 'students', label: 'Students', description: 'Class results and exports' },
  { key: 'tests', label: 'Tests & reports', description: 'Submissions and topic insights' },
  { key: 'learning', label: 'Syllabus & follow-up', description: 'Coverage and focused practice' },
  { key: 'doubts', label: 'Student questions', description: 'Explain and reply to doubts' },
]

export function teacherSection(params) {
  if (params.get('report')) return 'tests'
  const key = params.get('tab')
  if (key === 'build') return 'papers'
  return teacherSections.some(section => section.key === key) ? key : 'overview'
}

export function teacherHref(key) {
  return key === 'overview' ? '/teacher' : `/teacher?tab=${key}`
}

export function paperBuildProblem(form, questions) {
  if (form.title.trim().length < 3) return 'Give your paper a title of at least 3 characters.'
  if (!Number.isInteger(form.duration_minutes) || form.duration_minutes < 1 || form.duration_minutes > 240) return 'Choose a duration between 1 and 240 minutes.'
  if (!Number.isInteger(form.marks_correct) || form.marks_correct < 1 || form.marks_correct > 10) return 'Correct-answer marks must be between 1 and 10.'
  if (!Number.isInteger(form.marks_wrong) || form.marks_wrong < 0 || form.marks_wrong > 10) return 'Wrong-answer deduction must be between 0 and 10.'
  if (!questions.length) return 'Add at least one question before reviewing your paper.'
  return ''
}
