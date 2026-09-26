import { useEffect, useId, useLayoutEffect, useRef, useState } from 'react'
import { createPortal } from 'react-dom'
import { Info, X } from 'lucide-react'
import { request } from '../lib/api.js'
import './college-info.css'

function Sources({ items }) {
  return <div className="college-info-sources">{items?.map((s, i) => <a key={`${s.url}-${i}`} href={s.url} target="_blank" rel="noopener noreferrer">{s.label || 'Source'} ↗</a>)}</div>
}
function Placement({ value }) {
  const amount = v => v == null ? 'Not verified' : `₹${Number(v).toLocaleString('en-IN')} LPA`
  return <><div className="college-info-metrics"><div><span>Highest CTC</span><strong>{amount(value?.highest_lpa)}</strong></div><div><span>Average CTC</span><strong>{amount(value?.average_lpa)}</strong></div></div>{value?.note && <p className="college-info-note">{value.note}</p>}<Sources items={value?.sources}/></>
}

export default function CollegeInfo({ institute, program }) {
  const id = useId()
  const trigger = useRef(null), panel = useRef(null), timer = useRef(null)
  const [open, setOpen] = useState(false)
  const [data, setData] = useState(null), [error, setError] = useState(''), [retry, setRetry] = useState(0)
  const [position, setPosition] = useState({ left: 12, top: 12, visibility: 'hidden' })
  const cancel = () => clearTimeout(timer.current)
  const show = () => { cancel(); setOpen(true) }
  const close = () => { cancel(); setOpen(false) }
  const leave = () => {
    cancel()
    timer.current = setTimeout(() => {
      if (!trigger.current?.contains(document.activeElement) && !panel.current?.contains(document.activeElement)) setOpen(false)
    }, 180)
  }
  useEffect(() => () => clearTimeout(timer.current), [])
  useEffect(() => {
    if (!open) return
    let active = true
    setData(null); setError('')
    request(`/api/colleges/insight?institute=${encodeURIComponent(institute)}&program=${encodeURIComponent(program)}`)
      .then(value => { if (active) setData(value) })
      .catch(e => { if (active) setError(e.message) })
    return () => { active = false }
  }, [open, institute, program, retry])
  useLayoutEffect(() => {
    if (!open) return
    const place = () => {
      if (!trigger.current || !panel.current) return
      const r = trigger.current.getBoundingClientRect(), box = panel.current.getBoundingClientRect()
      const height = window.innerHeight, width = window.innerWidth
      const below = height - r.bottom - 12, above = r.top - 12
      const top = below >= Math.min(box.height, 300) || below >= above ? r.bottom + 8 : r.top - box.height - 8
      setPosition({ left: Math.max(12, Math.min(r.left, width - box.width - 12)), top: Math.max(12, Math.min(top, height - box.height - 12)), visibility: 'visible' })
    }
    place()
    const observer = new ResizeObserver(place)
    observer.observe(panel.current)
    window.addEventListener('resize', place)
    window.addEventListener('scroll', place, true)
    return () => { observer.disconnect(); window.removeEventListener('resize', place); window.removeEventListener('scroll', place, true) }
  }, [open])
  useEffect(() => {
    if (!open) return
    const outside = e => { if (!trigger.current?.contains(e.target) && !panel.current?.contains(e.target)) close() }
    const escape = e => { if (e.key === 'Escape') { const restore = panel.current?.contains(document.activeElement); if (restore) trigger.current?.focus(); close() } }
    document.addEventListener('pointerdown', outside)
    document.addEventListener('keydown', escape)
    return () => { document.removeEventListener('pointerdown', outside); document.removeEventListener('keydown', escape) }
  }, [open])
  return <>
    <button ref={trigger} type="button" className="college-info-trigger" aria-label={`About ${institute}, ${program}`} aria-expanded={open} aria-controls={open ? id : undefined} aria-haspopup="dialog"
      onPointerEnter={e => { if (e.pointerType === 'mouse') { cancel(); timer.current = setTimeout(show, 140) } }} onPointerLeave={leave}
      onFocus={show} onBlur={leave} onClick={show}
      onKeyDown={e => { if (e.key === 'ArrowDown' || e.key === 'Enter' || e.key === ' ') { e.preventDefault(); show(); setTimeout(() => panel.current?.focus(), 0) } }}><Info size={15} aria-hidden="true"/></button>
    {open && createPortal(<section ref={panel} id={id} role="dialog" aria-label={`College details: ${institute}`} tabIndex={-1} className="college-info-panel" style={position} onPointerEnter={cancel} onPointerLeave={leave} onFocus={cancel} onBlur={leave}>
      <div className="college-info-heading"><div><span className="college-info-eyebrow">COLLEGE SNAPSHOT</span><h3>{institute}</h3></div><button type="button" className="college-info-close" aria-label="Close college details" onClick={() => { trigger.current?.focus(); close() }}><X size={18}/></button></div>
      {!data && !error && <p role="status">Loading college details…</p>}
      {error && <div role="alert"><p>{error}</p><button type="button" className="btn btn-quiet" onClick={() => setRetry(v => v + 1)}>Try again</button></div>}
      {data && <>
        <p>{data.summary}</p><Sources items={data.sources}/>
        <div className="college-info-section"><h4>Your branch{data.placement ? ` · ${data.placement.year}` : ''}</h4><p className="college-info-program">{program}</p><Placement value={data.placement}/>{data.missing_note && <p className="college-info-note">{data.missing_note}</p>}</div>
        {data.overall_placement && <details className="college-info-overall"><summary>Overall B.Tech context · {data.overall_placement.year}</summary><p className="college-info-note">Institute-wide figures across B.Tech programs. These are not this branch’s results.</p><Placement value={data.overall_placement}/></details>}
        <p className="college-info-note">{data.placement_note}</p>
        <div className="college-info-section"><h4>Notable alumni · institute-wide</h4>{data.alumni.length ? <ul>{data.alumni.map(person => <li key={person.name}><strong>{person.name}</strong><p>{person.description}</p><Sources items={person.sources}/></li>)}</ul> : <p className="college-info-note">No verified alumni profiles in our records yet.</p>}</div>
        <footer>{data.verified_on ? `Sources checked ${data.verified_on}${data.review_due ? ' · Review due; check the linked reports for updates.' : ''}` : 'Catalog profile · placement and alumni details pending verification.'}</footer>
      </>}
    </section>, document.body)}
  </>
}
