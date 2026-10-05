// Fetch the route code on intent, before the click. No student data is fetched.
const routes = {
  '/pyq': () => import('../pages/PYQs.jsx'),
  '/pricing': () => import('../pages/Pricing.jsx'),
  '/dashboard': () => import('../pages/Dashboard.jsx'),
  '/plan': () => import('../pages/Roadmap.jsx'),
  '/subject-test': () => import('../pages/SubjectTest.jsx'),
  '/teacher': () => import('../pages/Teacher.jsx'),
  '/classes': () => import('../pages/Classrooms.jsx'),
  '/advanced': () => import('../pages/Advanced.jsx'),
  '/ranking': () => import('../pages/Ranking.jsx'),
  '/syllabus': () => import('../pages/Syllabus.jsx'),
}
const pending = new Map()
export function preloadRoute(event) {
  if (navigator.connection?.saveData || /(^|-)2g$/.test(navigator.connection?.effectiveType || '')) return
  const link = event.target.closest?.('a[href]')
  if (!link) return
  const url = new URL(link.href, location.href)
  const load = url.origin === location.origin && routes[url.pathname]
  if (!load || pending.has(url.pathname)) return
  pending.set(url.pathname, load().catch(() => pending.delete(url.pathname)))
}
