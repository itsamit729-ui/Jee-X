import { lazy, Suspense, useEffect } from 'react'
import { IITianFactToast, Loader } from './components/Brand.jsx'
import { Routes, Route, Navigate, useLocation, useNavigationType } from 'react-router-dom'
const PYQs = lazy(() => import('./pages/PYQs.jsx'))
import { useAuth } from './auth/AuthContext.jsx'
import { isTeacherAccount, teacherRouteRedirect } from './lib/workspaceRoutes.js'
const TeacherProfile = lazy(() => import('./pages/TeacherProfile.jsx'))
const Learning = lazy(() => import('./pages/Learning.jsx'))
const Teacher = lazy(() => import('./pages/Teacher.jsx'))
const Classrooms = lazy(() => import('./pages/Classrooms.jsx'))
const Assignment = lazy(() => import('./pages/Assignment.jsx'))
const Notifications = lazy(() => import('./pages/Notifications.jsx'))
const Advanced = lazy(() => import('./pages/Advanced.jsx'))
const Roadmap = lazy(() => import('./pages/Roadmap.jsx'))
const PublicProfile = lazy(() => import('./pages/PublicProfile.jsx'))
const Syllabus = lazy(() => import('./pages/Syllabus.jsx'))
const Ranking = lazy(() => import('./pages/Ranking.jsx'))
const RankedTest = lazy(() => import('./pages/RankedTest.jsx'))
const Pricing = lazy(() => import('./pages/Pricing.jsx'))
const Home = lazy(() => import('./pages/Home.jsx'))
const MockTest = lazy(() => import('./pages/MockTest.jsx'))
const Analysis = lazy(() => import('./pages/Analysis.jsx'))
const AttemptAnalysis = lazy(() => import('./pages/AttemptAnalysis.jsx'))
const Buddy = lazy(() => import('./pages/Buddy.jsx'))
const FreeTest = lazy(() => import('./pages/FreeTest.jsx'))
const Onboarding = lazy(() => import('./pages/Onboarding.jsx'))
const Dashboard = lazy(() => import('./pages/Dashboard.jsx'))
const Profile = lazy(() => import('./pages/Profile.jsx'))
const SubjectTest = lazy(() => import('./pages/SubjectTest.jsx'))
const DailyQuestion = lazy(() => import('./pages/DailyQuestion.jsx'))
const Rewards = lazy(() => import('./pages/Rewards.jsx'))
const AuthPage = lazy(() => import('./auth/AuthPage.jsx'))
const TermsPage = lazy(() => import('./auth/TermsPage.jsx'))
const Legal = lazy(() => import('./pages/Legal.jsx'))
const Admin = lazy(() => import('./pages/Admin.jsx'))
const ImageQuestions = lazy(() => import('./pages/ImageQuestions.jsx'))
const Scenarios = lazy(() => import('./pages/Scenarios.jsx'))
const Duels = lazy(() => import('./pages/Duels.jsx'))
import ProtectedRoute from './components/ProtectedRoute.jsx'
const MHTCETLanding = lazy(() => import('./pages/MHTCETLanding.jsx'))

import SEO_PAGES from './data/seoPages.json'

function updateSeo(pathname) {
  pathname = pathname.replace(/\/+$/, '') || '/'
  const page = SEO_PAGES[pathname]
  const privateRoute = !page
  const title = page?.[0] || 'Your exam preparation'
  const description = page?.[1] || ''
  document.title = `${title} · Jee Edge`
  const setMeta = (selector, attribute, value) => {
    let element = document.head.querySelector(selector)
    if (!element) {
      element = document.createElement('meta')
      const [key, name] = attribute
      element.setAttribute(key, name)
      document.head.appendChild(element)
    }
    element.content = value
  }
  setMeta('meta[name="description"]', ['name', 'description'], description)
  setMeta('meta[name="robots"]', ['name', 'robots'], privateRoute ? 'noindex, nofollow' : 'index, follow')
  setMeta('meta[property="og:title"]', ['property', 'og:title'], `${title} · Jee Edge`)
  setMeta('meta[property="og:description"]', ['property', 'og:description'], description)
  setMeta('meta[property="og:type"]', ['property', 'og:type'], 'website')
  setMeta('meta[property="og:url"]', ['property', 'og:url'], `https://jeeedge.in${pathname === '/' ? '/' : pathname}`)
  setMeta('meta[name="twitter:title"]', ['name', 'twitter:title'], `${title} · Jee Edge`)
  setMeta('meta[name="twitter:description"]', ['name', 'twitter:description'], description)
  let canonical = document.head.querySelector('link[rel="canonical"]')
  if (!canonical) { canonical = document.createElement('link'); canonical.rel = 'canonical'; document.head.appendChild(canonical) }
  canonical.href = `https://jeeedge.in${pathname === '/' ? '/' : pathname}`
}

export default function App() {
  const {user,isLoading}=useAuth()
  const teacher=isTeacherAccount(user)
  const location = useLocation()
  const navigationType = useNavigationType()
  useEffect(() => {
    updateSeo(location.pathname)
    if(teacher) document.title='Teacher Studio · Jee Edge'
    // Search/filter changes should keep their position; new pages start at the top.
    if (navigationType !== 'POP' && !location.hash) window.scrollTo({ top: 0, left: 0, behavior: 'instant' })
  }, [location.pathname,teacher])
  const isAdmin = location.pathname === '/admin'
  const examRoute = /^\/(scenarios\/|duels\/|subject-test|practice|ranked-test\/|test(?:\/|$))/.test(location.pathname)
  const isAuthPage = /^\/(login|signup|signup\/terms|terms|privacy|forgot-password|reset-password|verify-email|account\/security)$/.test(location.pathname)

  if(isLoading) return <Loader fullScreen label="Opening Jee Edge"/>
  const redirect=teacher?teacherRouteRedirect(location.pathname):null
  if(redirect) return <Navigate replace to={redirect}/>
  return (
    <>{!teacher && !isAdmin && !isAuthPage && !examRoute && <IITianFactToast />}<Suspense fallback={<Loader fullScreen label={isAdmin ? "Opening admin console" : teacher ? "Opening your teaching workspace" : "Opening your study space"} />}><Routes>
      <Route path="/login" element={<AuthPage key="login" mode="login" />} />
      <Route path="/signup" element={<AuthPage key="signup" mode="signup" />} />
      <Route path="/signup/terms" element={<TermsPage />} />
      <Route path="/terms" element={<Legal />} />
      <Route path="/privacy" element={<Legal privacy />} />
      <Route path="/forgot-password" element={<AuthPage key="forgot" mode="forgot" />} />
      <Route path="/reset-password" element={<AuthPage key="reset" mode="reset" />} />
      <Route path="/verify-email" element={<AuthPage key="verify" mode="verify" />} />
      <Route path="/account/security" element={<ProtectedRoute><AuthPage mode="change" /></ProtectedRoute>} />
      <Route path="/pyq" element={<ProtectedRoute><PYQs /></ProtectedRoute>} />
      <Route path="/teacher/profile" element={<ProtectedRoute><TeacherProfile /></ProtectedRoute>} />
      <Route path="/teacher/account" element={<ProtectedRoute><TeacherProfile /></ProtectedRoute>} />
      <Route path="/teacher" element={<ProtectedRoute><Teacher /></ProtectedRoute>} />
      <Route path="/learning" element={<ProtectedRoute><Learning /></ProtectedRoute>} />
      <Route path="/classes" element={<ProtectedRoute><Classrooms /></ProtectedRoute>} />
      <Route path="/assignments/:id" element={<ProtectedRoute><Assignment /></ProtectedRoute>} />
      <Route path="/notifications" element={<ProtectedRoute><Notifications /></ProtectedRoute>} />
      <Route path="/admin" element={<Admin />} />
      <Route path="/u/:username" element={<PublicProfile />} />
      <Route path="/students" element={<PublicProfile />} />
      <Route path="/syllabus" element={<Syllabus />} />
      <Route path="/ranking" element={<ProtectedRoute><Ranking /></ProtectedRoute>} />
      <Route path="/ranked-test/:id" element={<ProtectedRoute><RankedTest /></ProtectedRoute>} />
      <Route path="/" element={<Home />} />
      <Route path="/pricing" element={<Pricing />} />
      <Route path="/free-test" element={<FreeTest />} />
      <Route path="/image-questions" element={<ImageQuestions />} />
      <Route path="/mhtcet-mock-tests" element={<MHTCETLanding />} />
      <Route path="/advanced" element={<ProtectedRoute><Advanced /></ProtectedRoute>} />
      <Route path="/plan" element={<ProtectedRoute><Roadmap /></ProtectedRoute>} />
      <Route path="/roadmap" element={<ProtectedRoute><Navigate replace to={'/plan' + location.search + location.hash} /></ProtectedRoute>} />
      <Route path="/practice" element={<ProtectedRoute><SubjectTest key={`practice-${location.search}`} initialMode="recommended" /></ProtectedRoute>} />
      <Route path="/recommendations" element={<ProtectedRoute><Navigate replace to={(location.state?.missionTest || new URLSearchParams(location.search).get('assessment') === '1' ? '/practice' : '/plan') + location.search + location.hash} state={location.state} /></ProtectedRoute>} />
      <Route path="/scenarios" element={<ProtectedRoute><Scenarios /></ProtectedRoute>} />
      <Route path="/scenarios/:runId" element={<ProtectedRoute><Scenarios /></ProtectedRoute>} />
      <Route path="/duels" element={<ProtectedRoute><Duels /></ProtectedRoute>} />
      <Route path="/duels/:matchId" element={<ProtectedRoute><Duels /></ProtectedRoute>} />
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
      <Route path="/results/:attemptId" element={<ProtectedRoute><AttemptAnalysis /></ProtectedRoute>} />
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
            <SubjectTest key={`topic-${location.search}`} initialMode="topic" />
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

