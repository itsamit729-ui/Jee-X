import { request } from './api.js'

export const scenarioService = {
  list: () => request('/api/scenarios'),
  start: (token, key) => request(`/api/scenarios/${encodeURIComponent(key)}/start`, { token, method: 'POST' }),
  get: (token, id) => request(`/api/scenarios/runs/${encodeURIComponent(id)}`, { token }),
  save: (token, id, questionId, answer) => request(`/api/scenarios/runs/${encodeURIComponent(id)}/answers/${encodeURIComponent(questionId)}`, {
    token, method: 'PUT', body: answer,
  }),
  finish: (token, id) => request(`/api/scenarios/runs/${encodeURIComponent(id)}/finish`, { token, method: 'POST' }),
}
