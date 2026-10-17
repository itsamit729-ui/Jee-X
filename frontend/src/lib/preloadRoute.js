// Fetch the route code on intent, before the click. No student data is fetched.
const routes = {
  '/free-test': () => import('../pages/FreeTest.jsx'),
  '/login': () => import('../auth/AuthPage.jsx'),
  '/signup': () => import('../auth/AuthPage.jsx'),
  '/test': () => import('../pages/MockTest.jsx'),
  '/results': () => import('../pages/AttemptAnalysis.jsx'),
  '/scenarios': () => import('../pages/Scenarios.jsx'),
  '/daily': () => import('../pages/DailyQuestion.jsx'),
  '/pyq': () => import('../pages/PYQs.jsx'),
  '/pricing': () => import('../pages/Pricing.jsx'),
  '/dashboard': () => import('../pages/Dashboard.jsx'),
  '/plan': () => import('../pages/Roadmap.jsx'),
  '/practice': () => import('../pages/SubjectTest.jsx'),
  '/teacher/profile': () => import('../pages/TeacherProfile.jsx'),
  '/teacher/account': () => import('../pages/TeacherProfile.jsx'),
  '/notifications': () => import('../pages/Notifications.jsx'),
  '/learning': () => import('../pages/Learning.jsx'),
  '/profile': () => import('../pages/Profile.jsx'),
  '/subject-test': () => import('../pages/SubjectTest.jsx'),
  '/teacher': () => import('../pages/Teacher.jsx'),
  '/classes': () => import('../pages/Classrooms.jsx'),
  '/advanced': () => import('../pages/Advanced.jsx'),
  '/ranking': () => import('../pages/Ranking.jsx'),
  '/syllabus': () => import('../pages/Syllabus.jsx'),
}
const pending = new Map()
export function preloadRoute(event) {
  if (event.pointerType === 'touch') return
  if (navigator.connection?.saveData || /(^|-)2g$/.test(navigator.connection?.effectiveType || '')) return
  const link = event.target.closest?.('a[href]')
  if (!link) return
  const url = new URL(link.href, location.href)
  const key = url.pathname.startsWith('/results/') ? '/results' : url.pathname
  const load = url.origin === location.origin && routes[key]
  if (!load || pending.has(key)) return
  pending.set(key, load().catch(() => pending.delete(key)))
}
