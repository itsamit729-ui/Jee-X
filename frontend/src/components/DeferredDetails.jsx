import { useState } from 'react'

// Closed report rows should not typeset hundreds of questions or mount diagrams.
// Native details/summary keeps keyboard and screen-reader interaction intact.
export default function DeferredDetails({ summary, children, className = '', initialOpen = false }) {
  const [open, setOpen] = useState(initialOpen)
  return <details className={className} open={open} onToggle={event => {
    if (event.target === event.currentTarget) setOpen(event.currentTarget.open)
  }}>
    <summary>{summary}</summary>
    {open && <div className="disclosure-content">{children}</div>}
  </details>
}
