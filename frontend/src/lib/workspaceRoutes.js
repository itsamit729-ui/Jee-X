export const isTeacherAccount = user => Boolean(user?.account_type === 'teacher' || user?.teacher)

// Resolve before mounting a page so student API calls never run for teachers.
export function teacherRouteRedirect(path) {
  if (path === '/profile') return '/teacher/profile'
  if (path === '/pricing') return '/teacher/account'
  if (path === '/teacher' || path.startsWith('/teacher/') ||
      ['/notifications','/account/security','/terms','/privacy','/admin','/login','/signup','/signup/terms','/forgot-password','/reset-password','/verify-email'].includes(path)) return null
  return '/teacher'
}
