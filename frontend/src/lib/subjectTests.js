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
  start: ({ subjectCode, chapterId = null, topicId = null, count = 10, mode = 'topic', durationMinutes, assessment = false, fullMock = false }) =>
    request('/api/subject-tests', {
      method: 'POST',
      body: { assessment, full_mock: fullMock, subject_code: subjectCode || null, chapter_id: chapterId, topic_id: topicId, count, mode, duration_minutes: durationMinutes },
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

// Reopen a submitted attempt: full analysis, and the list of past attempts.
export const attemptAnalysisService = {
  get: (attemptId) => request(`/api/test-attempts/${encodeURIComponent(attemptId)}/analysis`),
  history: ({ limit = 20, before } = {}) =>
    request(`/api/test-attempts/history?limit=${limit}${before ? `&before=${before}` : ''}`),
}
