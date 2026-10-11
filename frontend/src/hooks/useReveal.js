import { useEffect, useRef } from 'react'

// Progressive enhancement: content stays visible without motion/observer support.
export default function useReveal() {
  const ref = useRef(null)
  useEffect(() => {
    const root = ref.current
    if (!root || !('IntersectionObserver' in window) || window.matchMedia('(prefers-reduced-motion: reduce)').matches) return
    const observer = new IntersectionObserver(entries => {
      entries.forEach(entry => {
        if (entry.isIntersecting) {
          entry.target.classList.add('is-revealed')
          observer.unobserve(entry.target)
        }
      })
    }, { threshold: 0.08 })
    root.querySelectorAll('[data-reveal]').forEach(node => { node.classList.add('reveal-ready'); observer.observe(node) })
    return () => { observer.disconnect(); root.querySelectorAll('.reveal-ready').forEach(node => node.classList.remove('reveal-ready')) }
  }, [])
  return ref
}
