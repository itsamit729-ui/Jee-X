import { Navigate, useLocation } from 'react-router-dom'
import { useAuth } from '../auth/AuthContext.jsx'
import { Loader } from './Brand.jsx'

export default function ProtectedRoute({ children }) {
  const location = useLocation()
  const { isAuthenticated, isLoading, error } = useAuth()
  if (isLoading) return <Loader fullScreen label="Checking your session" />
  if (error && !isAuthenticated) return <main className="wrap page"><p>Session check unavailable. Use Retry above to reconnect.</p></main>
  if (!isAuthenticated) return <Navigate replace to={`/login?returnTo=${encodeURIComponent(location.pathname + location.search)}`} />
  return children
}
