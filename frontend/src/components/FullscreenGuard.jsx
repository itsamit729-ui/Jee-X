import { useEffect, useRef } from 'react'
import { MAX_FULLSCREEN_EXITS } from '../lib/fullscreen.js'

export default function FullscreenGuard({ exited, onResume, exitCount = 0, limitReached = false, onSubmit, submitting = false, error = '' }) {
  const modal = useRef(null)
  const visible = exited || limitReached
  useEffect(() => {
    if (!visible) return
    const previous = document.activeElement
    ;(modal.current?.querySelector('button:not(:disabled)') || modal.current)?.focus()
    return () => { if (previous?.isConnected) previous.focus() }
  }, [visible, limitReached, submitting])
  function keepFocus(event) {
    if (event.key !== 'Tab') return
    const buttons = [...modal.current.querySelectorAll('button:not(:disabled)')]
    const first = buttons[0], last = buttons.at(-1)
    if (!first) { event.preventDefault(); modal.current.focus(); return }
    if (event.shiftKey && (document.activeElement === first || document.activeElement === modal.current)) { event.preventDefault(); last.focus() }
    else if (!event.shiftKey && (document.activeElement === last || document.activeElement === modal.current)) { event.preventDefault(); first.focus() }
  }
  if (!visible) return null
  return (
    <div className="modal-backdrop" role="alertdialog" aria-modal="true" aria-labelledby="fs-guard-title">
      <div className="modal" ref={modal} tabIndex={-1} onKeyDown={keepFocus}>
        <h2 id="fs-guard-title">{limitReached ? 'Fullscreen exit limit reached' : exitCount ? "You've left full-screen" : 'Enter full-screen to continue'}</h2>
        <p>{limitReached ? (error ? 'Your test has ended, but submission failed. Retry to submit your saved answers.' : 'You left full-screen more than three times. Your saved answers are being submitted. Keep this page open until your result appears.') : exitCount ? `Fullscreen exit ${exitCount} of ${MAX_FULLSCREEN_EXITS}. Your timer keeps running. The fourth exit automatically submits your saved answers.` : 'Your browser has not entered full-screen. Press Resume test and allow full-screen when prompted. Your timer keeps running.'}</p>
        {error && <p role="alert" className="alert">{error}</p>}
        <div className="modal-actions">
          {!limitReached && <button type="button" className="btn btn-primary" disabled={submitting} onClick={onResume}>Resume test</button>}
          {onSubmit && <button type="button" className="btn btn-secondary" disabled={submitting} onClick={onSubmit}>{submitting ? 'Submitting…' : limitReached ? 'Retry submission' : 'Submit & exit test'}</button>}
        </div>
      </div>
    </div>
  )
}
