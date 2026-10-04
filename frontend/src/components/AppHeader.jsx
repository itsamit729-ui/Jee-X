import { useEffect, useRef, useState } from 'react'
import { NavLink, useLocation } from 'react-router-dom'
import { useAuth } from '../auth/AuthContext.jsx'
import { LayoutDashboard, BookOpen, Target, Trophy, Users, CalendarCheck, GraduationCap, Shapes, Library, MessageCircle, Coins, UserRound, LogOut, Menu, X, ArrowUpRight } from 'lucide-react'
import { Logo } from './Brand.jsx'
import InboxBell from './classroom/InboxBell.jsx'
import { preloadRoute } from '../lib/preloadRoute.js'
import './studio-navigation.css'

const main = [
  ['/dashboard', 'Overview', LayoutDashboard], ['/plan', 'My plan', Target],
  ['/subject-test', 'Practice', BookOpen], ['/ranking', 'Rankings', Trophy],
]
const more = [
  ['/daily', 'Daily question', CalendarCheck], ['/test', 'Full mock', Shapes],
  ['/scenarios', 'Exam situations', Shapes], ['/classes', 'My classroom', Users],
  ['/teacher', 'Teacher studio', GraduationCap], ['/advanced', 'IIT & Advanced', GraduationCap],
  ['/syllabus', 'Syllabus', Library], ['/image-questions', 'Diagram practice', BookOpen],
  ['/buddy', 'Study assistant', MessageCircle], ['/rewards', 'Rewards', Coins],
  ['/pricing', 'Plans & pricing', Target], ['/profile', 'My profile', UserRound],
]
function NavigationLink({ item, close }) {
  const [to, label, Icon] = item
  return <NavLink to={to} onClick={close} className={({ isActive }) => `studio-link${isActive ? ' active' : ''}`}><Icon size={18} strokeWidth={1.7}/><span>{label}</span></NavLink>
}
export default function AppHeader() {
  const { pathname } = useLocation()
  const { isAuthenticated, openLogin, logout } = useAuth()
  const [open, setOpen] = useState(false)
  const [teacher, setTeacher] = useState(false)
  const ref = useRef(null), trigger = useRef(null)
  const close = () => setOpen(false)
  useEffect(close, [pathname])
  useEffect(() => {
    if (!open) return
    const dismiss = event => { if (!ref.current?.contains(event.target)) close() }
    const escape = event => { if (event.key === 'Escape') { close(); trigger.current?.focus() } }
    document.addEventListener('pointerdown', dismiss); document.addEventListener('keydown', escape)
    return () => { document.removeEventListener('pointerdown', dismiss); document.removeEventListener('keydown', escape) }
  }, [open])
  const links = teacher ? [['/teacher', 'Teacher studio', GraduationCap], ...main.slice(1)] : main

  return <div ref={ref} className={`studio-navigation${isAuthenticated ? ' is-member' : ''}`} onPointerOver={preloadRoute} onFocus={preloadRoute}>
    <a className="skip-link" href="#studio-main">Skip to workspace</a>
    <header className="studio-topbar"><div className="studio-mobile-logo"><Logo to={isAuthenticated ? '/dashboard' : '/'}/></div>{isAuthenticated && <nav className="studio-top-links" aria-label="Main navigation">{links.map(item => <NavigationLink key={item[0]} item={item} close={close}/>)}</nav>}<div className="studio-top-actions">{isAuthenticated ? <><InboxBell onTeacher={setTeacher}/><button ref={trigger} className="studio-more" onClick={() => setOpen(v => !v)} aria-label={open ? 'Close workspace menu' : 'Open workspace menu'} aria-expanded={open} aria-controls="studio-menu">{open ? <X size={20}/> : <Menu size={20}/>}</button></> : <button className="btn btn-primary btn-sm" onClick={() => openLogin()}>Log in</button>}</div></header>
    {isAuthenticated && open && <nav id="studio-menu" className="studio-menu" aria-label="All workspace pages">{[...links, ...more].filter((item, index, items) => items.findIndex(other => other[0] === item[0]) === index).map(item => <NavigationLink key={item[0]} item={item} close={close}/>)}<button className="studio-link" onClick={logout}><LogOut size={18}/>Sign out</button></nav>}
    {isAuthenticated && <nav className="studio-dock" aria-label="Quick navigation">{links.slice(0, 3).map(item => <NavigationLink key={item[0]} item={item} close={close}/>)}<button className={`studio-link${open ? ' active' : ''}`} onClick={() => { setOpen(v => !v); trigger.current?.focus() }} aria-expanded={open} aria-controls="studio-menu"><Menu size={19}/><span>More</span></button></nav>}
    <span id="studio-main" tabIndex={-1}/>
  </div>
}
