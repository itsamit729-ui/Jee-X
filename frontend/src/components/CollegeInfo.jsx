import { useEffect, useId, useLayoutEffect, useRef, useState } from 'react'
import { createPortal } from 'react-dom'
import { Info, X } from 'lucide-react'
import { request } from '../lib/api.js'
import './college-info.css'

function Sources({ items }) {
  return <div className="college-info-sources">{items?.map((s, i) => <a key={`${s.url}-${i}`} href={s.url} target="_blank" rel="noopener noreferrer">{s.label || 'Source'} ↗</a>)}</div>
}
function Packages({ value }) {
  const metrics = [['Highest CTC', value?.highest_lpa], ['Average CTC', value?.average_lpa]]
    .filter(([, amount]) => typeof amount === 'number' && Number.isFinite(amount) && amount > 0)
  if (!metrics.length) return null
  return <div className="college-info-section">
    <h4>{value.scope === 'branch' ? 'Branch packages' : 'Overall B.Tech packages'}{value.year ? ` · ${value.year}` : ''}</h4>
    {value.scope === 'branch' ? <p className="college-info-note">{value.program}</p> : <p className="college-info-note">Across the college’s B.Tech programs.</p>}
    <div className="college-info-metrics">{metrics.map(([label, amount]) => <div key={label}><span>{label}</span><strong>₹{amount.toLocaleString('en-IN')} LPA</strong></div>)}</div>
    {value.note && <p className="college-info-note">{value.note}</p>}
    <Sources items={value.sources}/>
    <p className="college-info-note">CTC in lakh per year, not take-home pay. Past outcomes don’t guarantee future offers.</p>
  </div>
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
        <Packages value={data.placement}/>
        <Packages value={data.overall_placement}/>
        {data.alumni?.length > 0 && <div className="college-info-section"><h4>Notable alumni</h4><ul>{data.alumni.map(person => <li key={person.name}><strong>{person.name}</strong><p>{person.description}</p><Sources items={person.sources}/></li>)}</ul></div>}
        {data.verified_on && <footer>Sources checked {data.verified_on}</footer>}
      </>}
    </section>, document.body)}
  </>
}
