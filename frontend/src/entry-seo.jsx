// Render the same public components for every visitor, without session data.
import React from 'react'
import { renderToString } from 'react-dom/server'
import { StaticRouter } from 'react-router-dom/server'
import { AuthProvider } from './auth/AuthContext.jsx'
import Home from './pages/Home.jsx'
import Syllabus from './pages/Syllabus.jsx'
import Pricing from './pages/Pricing.jsx'
import FreeTest from './pages/FreeTest.jsx'
import ImageQuestions from './pages/ImageQuestions.jsx'
import MHTCETLanding from './pages/MHTCETLanding.jsx'

const pages = { '/': Home, '/syllabus': Syllabus, '/pricing': Pricing, '/free-test': FreeTest,
  '/image-questions': ImageQuestions, '/mhtcet-mock-tests': MHTCETLanding }
export function render(path) {
  const Page = pages[path]
  if (!Page) throw new Error(`Unknown public page: ${path}`)
  return renderToString(<StaticRouter location={path}><AuthProvider><Page /></AuthProvider></StaticRouter>)
}
