import { request } from './api.js'

export const scenarioService = {
  list: () => request('/api/scenarios'),
  start: (key) => request(`/api/scenarios/${encodeURIComponent(key)}/start`, { method: 'POST' }),
  get: (id) => request(`/api/scenarios/runs/${encodeURIComponent(id)}`, {}),
  save: (id, questionId, answer) => request(`/api/scenarios/runs/${encodeURIComponent(id)}/answers/${encodeURIComponent(questionId)}`, {
    method: 'PUT', body: answer,
  }),
  finish: (id) => request(`/api/scenarios/runs/${encodeURIComponent(id)}/finish`, { method: 'POST' }),
}
