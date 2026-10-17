import { useEffect, useRef, useState } from 'react'

export const MAX_FULLSCREEN_EXITS = 3
function fsElement() {
  return document.fullscreenElement || document.webkitFullscreenElement || null
}

// Request synchronously from the start/resume click. Denial is not an exit.
export function requestFullscreen(el = document.documentElement) {
  const fn = el.requestFullscreen || el.webkitRequestFullscreen
  if (!fn) return Promise.resolve(false)
  try { return Promise.resolve(fn.call(el)).then(() => Boolean(fsElement()), () => false) }
  catch { return Promise.resolve(false) }
}
export function exitFullscreen() {
  if (!fsElement()) return Promise.resolve()
  const fn = document.exitFullscreen || document.webkitExitFullscreen
  try { return fn ? Promise.resolve(fn.call(document)).catch(() => {}) : Promise.resolve() }
  catch { return Promise.resolve() }
}

// Observe real transitions, including browsers emitting both event names.
// The count belongs to this subscription, which is recreated for each attempt.
export function observeFullscreen(onState, doc = document) {
  const current = () => Boolean(doc.fullscreenElement || doc.webkitFullscreenElement)
  let wasFullscreen = current(), exitCount = 0
  const onChange = () => {
    const fullscreen = current()
    if (wasFullscreen && !fullscreen) {
      exitCount++
      onState({ exited: true, exitCount })
    } else if (!wasFullscreen && fullscreen) onState({ exited: false, exitCount })
    wasFullscreen = fullscreen
  }
  doc.addEventListener('fullscreenchange', onChange)
  doc.addEventListener('webkitfullscreenchange', onChange)
  return () => {
    doc.removeEventListener('fullscreenchange', onChange)
    doc.removeEventListener('webkitfullscreenchange', onChange)
  }
}

export function useFullscreenLock(active, onLimit) {
  const [exited, setExited] = useState(false)
  const [exitCount, setExitCount] = useState(0)
  const callback = useRef(onLimit)
  callback.current = onLimit
  const triggered = useRef(false)
  useEffect(() => {
    if (!active) {
      setExited(false); setExitCount(0); triggered.current = false
      exitFullscreen()
      return
    }
    return observeFullscreen(state => {
      setExited(state.exited)
      setExitCount(state.exitCount)
    })
  }, [active])
  const limitReached = exitCount > MAX_FULLSCREEN_EXITS
  useEffect(() => {
    if (active && limitReached && !triggered.current) {
      triggered.current = true
      callback.current?.()
    }
  }, [active, limitReached])
  return { exited, exitCount, limitReached, resume: async () => {
    const entered = await requestFullscreen()
    if (entered) setExited(false)
    return entered
  } }
}
