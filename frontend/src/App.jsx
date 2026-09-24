import { lazy, Suspense } from 'react'
import { IITianFactToast, Loader } from './components/Brand.jsx'
import { Routes, Route, useLocation } from 'react-router-dom'
const PublicProfile = lazy(() => import('./pages/PublicProfile.jsx'))
const Syllabus = lazy(() => import('./pages/Syllabus.jsx'))
const Ranking = lazy(() => import('./pages/Ranking.jsx'))
const RankedTest = lazy(() => import('./pages/RankedTest.jsx'))
const Home = lazy(() => import('./pages/Home.jsx'))
const MockTest = lazy(() => import('./pages/MockTest.jsx'))
const Analysis = lazy(() => import('./pages/Analysis.jsx'))
const Buddy = lazy(() => import('./pages/Buddy.jsx'))
const FreeTest = lazy(() => import('./pages/FreeTest.jsx'))
const Onboarding = lazy(() => import('./pages/Onboarding.jsx'))
const Dashboard = lazy(() => import('./pages/Dashboard.jsx'))
const Profile = lazy(() => import('./pages/Profile.jsx'))
const SubjectTest = lazy(() => import('./pages/SubjectTest.jsx'))
const DailyQuestion = lazy(() => import('./pages/DailyQuestion.jsx'))
const Rewards = lazy(() => import('./pages/Rewards.jsx'))
const Admin = lazy(() => import('./pages/Admin.jsx'))
const ImageQuestions = lazy(() => import('./pages/ImageQuestions.jsx'))
import ProtectedRoute from './components/ProtectedRoute.jsx'

export default function App() {
  const location = useLocation()
  const isAdmin = location.pathname === '/admin'

  return (
    <>{!isAdmin && <IITianFactToast />}<Suspense fallback={<Loader fullScreen label={isAdmin ? "Opening admin console" : "Opening your study space"} />}><Routes>
      <Route path="/admin" element={<Admin />} />
      <Route path="/u/:username" element={<PublicProfile />} />
      <Route path="/students" element={<PublicProfile />} />
      <Route path="/syllabus" element={<Syllabus />} />
      <Route path="/ranking" element={<ProtectedRoute><Ranking /></ProtectedRoute>} />
      <Route path="/ranked-test/:id" element={<ProtectedRoute><RankedTest /></ProtectedRoute>} />
      <Route path="/" element={<Home />} />
      <Route path="/free-test" element={<FreeTest />} />
      <Route path="/image-questions" element={<ImageQuestions />} />
      <Route
        path="/test"
        element={
          <ProtectedRoute>
            <MockTest />
          </ProtectedRoute>
        }
      />
      <Route
        path="/analysis"
        element={
          <ProtectedRoute>
            <Analysis />
          </ProtectedRoute>
        }
      />
      <Route
        path="/buddy"
        element={
          <ProtectedRoute>
            <Buddy />
          </ProtectedRoute>
        }
      />
      <Route
        path="/onboarding"
        element={
          <ProtectedRoute>
            <Onboarding />
          </ProtectedRoute>
        }
      />
      <Route
        path="/dashboard"
        element={
          <ProtectedRoute>
            <Dashboard />
          </ProtectedRoute>
        }
      />
      <Route
        path="/profile"
        element={
          <ProtectedRoute>
            <Profile />
          </ProtectedRoute>
        }
      />
      <Route
        path="/subject-test"
        element={
          <ProtectedRoute>
            <SubjectTest />
          </ProtectedRoute>
        }
      />
      <Route
        path="/daily"
        element={
          <ProtectedRoute>
            <DailyQuestion />
          </ProtectedRoute>
        }
      />
      <Route
        path="/rewards"
        element={
          <ProtectedRoute>
            <Rewards />
          </ProtectedRoute>
        }
      />
    </Routes></Suspense></>
  )
}

