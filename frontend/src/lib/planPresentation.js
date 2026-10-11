export const planSubjects = { PHY: 'Physics', CHEM: 'Chemistry', MATH: 'Mathematics' }

export function planTopics(plan, subject, chapter) {
  return (plan?.topics || []).filter(topic => (!subject || topic.subject === subject) && (!chapter || String(topic.chapter_id) === String(chapter)))
}

// Keep both the full plan and post-test recommendation on the exact same topic.
export function topicPracticeOptions(topic) {
  return { mission: true, assessment: false, subjectCode: topic.subject, chapterId: topic.chapter_id, topicId: topic.topic_id, durationMinutes: 15, mode: 'recommended' }
}

export function planGoal(settings, saved) {
  const count = settings.choices?.length || 0
  return {
    label: saved ? 'Your goal' : 'Suggested goal',
    value: settings.goal_type === 'colleges' ? `${count} college ${count === 1 ? 'choice' : 'choices'}` : `${settings.target_marks} / 300`,
    detail: settings.goal_type === 'colleges' ? 'College & branch combinations' : 'JEE Main marks',
  }
}

export function goalPayload(draft) {
  return {
    available_hours: draft.available_hours == null || draft.available_hours === '' ? null : Number(draft.available_hours),
    admission: draft.admission,
    goal_type: draft.goal_type,
    target_marks: draft.goal_type === 'marks' ? Number(draft.target_marks) : null,
    college_choices: draft.goal_type === 'colleges' ? draft.college_choices : [],
  }
}

export function evidenceLabel(topic) {
  return topic.accuracy == null ? 'No fresh answers yet. This session helps us understand your level.' : `${topic.accuracy}% correct · ${topic.fresh_answers} fresh answers · ${topic.study_days} study days`
}
