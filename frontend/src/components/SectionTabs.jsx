import { Children, useId, useState } from 'react'

export default function SectionTabs({ labels, children, title = 'Explore your plan' }) {
  const id = useId()
  const [selected, setSelected] = useState(0)
  const panels = Children.toArray(children)
  function move(event, index) {
    const next = event.key === 'ArrowRight' ? (index + 1) % labels.length : event.key === 'ArrowLeft' ? (index + labels.length - 1) % labels.length : event.key === 'Home' ? 0 : event.key === 'End' ? labels.length - 1 : null
    if (next == null) return
    event.preventDefault()
    setSelected(next)
    document.getElementById(`${id}-tab-${next}`)?.focus()
  }
  return <section className="section-browser" aria-label={title}>
    <div className="section-browser-heading"><h2>{title}</h2><span>Choose what you want to explore</span></div>
    <div className="section-browser-tabs" role="tablist" aria-label={title}>{labels.map((label, index) => <button key={label} type="button" role="tab" id={`${id}-tab-${index}`} aria-controls={`${id}-panel-${index}`} aria-selected={selected === index} tabIndex={selected === index ? 0 : -1} onKeyDown={event => move(event, index)} onClick={() => setSelected(index)}>{label}</button>)}</div>
    {panels.map((panel, index) => <div key={index} role="tabpanel" id={`${id}-panel-${index}`} aria-labelledby={`${id}-tab-${index}`} hidden={selected !== index} tabIndex={0} className="section-browser-panel">{panel}</div>)}
  </section>
}
