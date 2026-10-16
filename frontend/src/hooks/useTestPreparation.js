import { useEffect, useRef, useState } from 'react'
import { canEnterTest } from '../lib/testPreparation.js'

export default function useTestPreparation(initial = null) {
  const [session, setSession] = useState(() => initial ? { startedAt: Date.now(), details: initial.details, paper: initial.paper, loading: false, error: '' } : null)
  const generation = useRef(0), alive = useRef(true), retry = useRef(null)
  useEffect(() => { alive.current = true; return () => { alive.current = false; generation.current++ } }, [])
  useEffect(() => {
    if (!session?.paper) return
    // Warm diagrams during reading time, without mounting the exam or its timer.
    const urls = new Set(session.paper.questions.flatMap(q => (q.assets || []).map(a => a.url)))
    for (const url of urls) { const image = new Image(); image.decoding = 'async'; image.src = url }
  }, [session?.paper])
  async function open(loader, details, startedAt = Date.now()) {
    const id = ++generation.current
    retry.current = () => open(loader, details, startedAt)
    setSession({ startedAt, details, paper: null, loading: true, error: '' })
    // Give the instructions a paint before starting request/response processing.
    await new Promise(resolve => setTimeout(resolve, 20))
    if (!alive.current || id !== generation.current) return null
    try {
      const paper = await loader()
      if (!alive.current || id !== generation.current) return null
      if (!paper?.questions?.length) throw new Error('No questions were returned. Please try again.')
      setSession({ startedAt, details, paper, loading: false, error: '' })
      return paper
    } catch (error) {
      if (alive.current && id === generation.current) setSession({ startedAt, details, paper: null, loading: false, error: error.message || 'Could not prepare this test.' })
      return null
    }
  }
  function cancel() { generation.current++; setSession(null) }
  function enter() {
    if (!canEnterTest(session)) return null
    const paper = session.paper
    cancel()
    return paper
  }
  return { session, open, cancel, enter, retry: () => retry.current?.() }
}
