// Three services mirroring the three backend routers under /api/subjects and
// /api/subject-tests: catalog, test creation, and submit/grade.
import { request } from './api.js'

// Service 1 — catalog: subjects and their chapters, with published question counts.
export const catalogService = {
  listSubjects: () => request('/api/subjects'),
  listChapters: (subjectCode) => request(`/api/subjects/${encodeURIComponent(subjectCode)}/chapters`),
}

// Service 2 — build a subject-wise test (optionally scoped to one chapter) and
// get back the question paper with no answers in it.
export const subjectTestBuilderService = {
  start: ({ subjectCode, chapterId = null, count = 10, mode = 'topic', durationMinutes }) =>
    request('/api/subject-tests', {
      method: 'POST',
      body: { subject_code: subjectCode || null, chapter_id: chapterId, count, mode, duration_minutes: durationMinutes },
    }),
}

// Service 3 — submit answers for grading; returns score, per-subtopic mastery
// updates (server-side), and per-question solutions.
export const subjectTestGraderService = {
  submit: (attemptId, answers) =>
    request(`/api/subject-tests/attempts/${attemptId}/submit`, {
      method: 'POST',
      body: { answers },
    }),
}
