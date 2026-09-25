// Empty base uses the same origin in the combined Render deployment.
export const API_URL = (import.meta.env.VITE_API_URL || '').replace(/\/$/, '')
let csrfToken = null
export function setCsrfToken(value) { csrfToken = value || null }

export async function request(path, { token, method = 'GET', body, raw = false } = {}) {
  const headers = { 'X-Jee-Request': '1' }
  if (raw) headers['Content-Type'] = body.type
  else if (body !== undefined) headers['Content-Type'] = 'application/json'
  // Bearer authentication is used only by the existing admin console.
  if (token) headers.Authorization = `Bearer ${token}`
  if (csrfToken && !['GET', 'HEAD'].includes(method)) headers['X-CSRF-Token'] = csrfToken
  const res = await fetch(`${API_URL}${path}`, {
    method, headers, credentials: 'include',
    body: body === undefined ? undefined : raw ? body : JSON.stringify(body),
  })
  const data = await res.json().catch(() => null)
  if (!res.ok) {
    if (res.status === 401 && !path.startsWith('/api/auth/') && !path.startsWith('/api/admin/')) {
      window.dispatchEvent(new Event('jee-session-expired'))
    }
    const message = data?.detail
      ? Array.isArray(data.detail) ? data.detail.map(d => d.msg).join(' ') : data.detail
      : 'Something went wrong. Please try again.'
    const error = new Error(message)
    error.status = res.status
    throw error
  }
  if (path.startsWith('/api/auth/') && data && 'csrf_token' in data) setCsrfToken(data.csrf_token)
  return data
}

export const api = {
  me: () => request('/api/me'),
  checkUsername: username => request(`/api/username-check/${encodeURIComponent(username)}`),
  onboard: payload => request('/api/onboarding', { method: 'POST', body: payload }),
  updateProfile: payload => request('/api/profile', { method: 'PATCH', body: payload }),
  uploadAvatar: file => request('/api/profile/avatar', { method: 'PUT', body: file, raw: true }),
  removeAvatar: () => request('/api/profile/avatar', { method: 'DELETE' }),
  submitTestAttempt: payload => request('/api/test-attempts', { method: 'POST', body: payload }),
  listTestAttempts: () => request('/api/test-attempts'),
}
