import { Navigate, useLocation } from 'react-router-dom'
import { useAuth } from '../auth/AuthContext.jsx'
import { Loader } from './Brand.jsx'

export default function ProtectedRoute({ children }) {
  const location = useLocation()
  const { isAuthenticated, isLoading, error, user } = useAuth()
  if (isLoading) return <Loader fullScreen label="Checking your session" />
  if (error && !isAuthenticated) return <main className="wrap page"><p>Session check unavailable. Use Retry above to reconnect.</p></main>
  if (!isAuthenticated) return <Navigate replace to={`/login?returnTo=${encodeURIComponent(location.pathname + location.search)}`} />
  if (user?.terms_required) return <Navigate replace to={`/signup/terms?returnTo=${encodeURIComponent(location.pathname + location.search)}`} />
  const teacher = user?.account_type === 'teacher' || user?.teacher
  if (teacher && !location.pathname.startsWith('/teacher') && !['/account/security','/notifications'].includes(location.pathname)) return <Navigate replace to="/teacher" />
  if (!teacher && location.pathname.startsWith('/teacher') && user?.onboarded) return <Navigate replace to="/dashboard" />
  return children
}
