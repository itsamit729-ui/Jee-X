// Service 4: rank/percentile/college prediction for a submitted test attempt.
// Mirrors backend/app/routers/predictions.py — one endpoint, works for both
// subject-test and legacy (free diagnostic / full mock) attempts.
import { request } from './api.js'

export const predictorService = {
  getPrediction: (attemptId) => request(`/api/test-attempts/${attemptId}/prediction`, {}),
}
