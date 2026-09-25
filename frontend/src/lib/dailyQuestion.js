// Service 6: personalized daily question + streak calendar. Submission reuses
// subjectTestGraderService.submit (lib/subjectTests.js) — same grading endpoint.
import { request } from './api.js'

export const dailyQuestionService = {
  getToday: () => request('/api/daily-question', {}),
  getCalendar: () => request('/api/daily-question/calendar', {}),
}
