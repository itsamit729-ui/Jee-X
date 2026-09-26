// Empty base uses the same origin in the combined Render deployment.
import { cachePolicy, cachedRead, invalidateCache } from './requestCache.js'

export const API_URL = (import.meta.env?.VITE_API_URL || '').replace(/\/$/, '')
let csrfToken = null
export function setCsrfToken(value) { csrfToken = value || null }

const pause = ms => new Promise(resolve => setTimeout(resolve, ms))

export function request(path, options = {}) {
  const method = (options.method || 'GET').toUpperCase()
  // A mutation invalidates both before and after: older reads cannot repopulate it.
  if (method !== 'GET') {
    invalidateCache()
    return networkRequest(path, { ...options, method }).finally(invalidateCache)
  }
  if (options.cache === false || options.token || path.startsWith('/api/admin/')) {
    return networkRequest(path, { ...options, method })
  }
  return cachedRead(`${API_URL}${path}`, cachePolicy(path), () => networkRequest(path, { ...options, method }))
}

async function networkRequest(path, { token, method, body, raw = false, timeoutMs = 30_000 } = {}) {
  const headers = { 'X-Jee-Request': '1' }
  if (raw) headers['Content-Type'] = body.type
  else if (body !== undefined) headers['Content-Type'] = 'application/json'
  if (token) headers.Authorization = `Bearer ${token}`
  if (csrfToken && !['GET', 'HEAD'].includes(method)) headers['X-CSRF-Token'] = csrfToken
  const attempts = method === 'GET' ? 2 : 1
  for (let attempt = 0; attempt < attempts; attempt++) {
    const controller = new AbortController()
    const timer = setTimeout(() => controller.abort(), timeoutMs)
    try {
      const res = await fetch(`${API_URL}${path}`, {
        method, headers, credentials: 'include', signal: controller.signal,
        body: body === undefined ? undefined : raw ? body : JSON.stringify(body),
      })
      const data = await res.json().catch(error => {
        if (controller.signal.aborted) throw error
        return null
      })
      if (!res.ok) {
        if (res.status === 401 && !path.startsWith('/api/auth/') && !path.startsWith('/api/admin/')) {
          invalidateCache()
          window.dispatchEvent(new Event('jee-session-expired'))
        }
        const detail = data?.detail
        const message = typeof detail === 'string' ? detail : Array.isArray(detail)
          ? detail.map(d => d.msg).join(' ') : 'Something went wrong. Please try again.'
        const error = new Error(message)
        error.status = res.status
        throw error
      }
      if (data === null && res.status !== 204) throw new Error('The server returned an invalid response. Please try again.')
      if (path.startsWith('/api/auth/') && data && 'csrf_token' in data) setCsrfToken(data.csrf_token)
      return data
    } catch (error) {
      const transient = error.name === 'AbortError' || error instanceof TypeError || [502, 503, 504].includes(error.status)
      if (attempt + 1 < attempts && transient) { clearTimeout(timer); await pause(600); continue }
      if (error.name === 'AbortError') throw new Error('The server is taking too long. Please try again.')
      if (error instanceof TypeError) throw new Error('Connection interrupted. Please check your connection and try again.')
      throw error
    } finally { clearTimeout(timer) }
  }
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
