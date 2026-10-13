import { API_URL } from './api.js'

export function omrReadiness(questions = []) {
  const issues = []
  questions.forEach((q, i) => {
    const options = q.options || []
    let reason = ''
    if (q.type !== 'single_correct') reason = q.type === 'numerical' ? 'Numerical answer' : 'Multiple-correct answer'
    else if (options.length !== 4 || new Set(options.map(o => o.label)).size !== 4 || options.some(o => !['A', 'B', 'C', 'D'].includes(o.label))) reason = 'Needs four options labelled A, B, C and D'
    else if (options.filter(o => o.is_correct).length !== 1) reason = 'Needs exactly one correct option'
    if (reason) issues.push({ number: i + 1, question_id: q.question_id, reason })
  })
  return { eligible: questions.length > 0 && questions.length <= 200 && !issues.length, issues, total: questions.length, eligible_count: questions.length - issues.length }
}

export function scheduleError(schedule, now = Date.now()) {
  const values = ['opens_at', 'due_at', 'solutions_at'].map(k => new Date(schedule[k]).getTime())
  if (values.some(v => !Number.isFinite(v))) return 'Choose all three dates.'
  const [opens, due, solutions] = values
  if (due <= Math.max(opens, now)) return 'The deadline must be in the future and after the opening time.'
  if (solutions < due) return 'Release solutions at or after the deadline.'
  return ''
}

// Keep PDF errors in the studio instead of navigating to a raw JSON response.
export async function downloadTeacherFile(path, filename) {
  const controller = new AbortController()
  const timer = setTimeout(() => controller.abort(), 30000)
  let url
  try {
    const response = await fetch(`${API_URL}${path}`, { credentials: 'include', headers: { 'X-Jee-Request': '1' }, signal: controller.signal })
    if (!response.ok) {
      const data = await response.json().catch(() => null)
      if (response.status === 401) window.dispatchEvent(new Event('jee-session-expired'))
      throw Error(typeof data?.detail === 'string' ? data.detail : 'Download unavailable. Refresh the paper and try again.')
    }
    const type = response.headers.get('content-type') || ''
    if (!/application\/pdf|text\/csv/.test(type)) throw Error('The server did not return a download. Please sign in again and retry.')
    const blob = await response.blob()
    url = URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url; link.download = filename; document.body.appendChild(link); link.click(); link.remove()
  } catch (error) {
    if (error.name === 'AbortError') throw Error('Download timed out. Try again; your paper is still saved.')
    throw error
  } finally {
    clearTimeout(timer)
    if (url) setTimeout(() => URL.revokeObjectURL(url), 60000)
  }
}
