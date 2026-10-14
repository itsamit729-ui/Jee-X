import { useEffect, useRef, useState } from 'react'
import { Link, NavLink, useLocation } from 'react-router-dom'
import { useAuth } from '../auth/AuthContext.jsx'
import { LayoutDashboard, BookOpen, Target, Trophy, Users, CalendarCheck, GraduationCap, Shapes, Library, MessageCircle, Coins, UserRound, LogOut, Grid2X2, X, Search, ArrowUpRight, ChevronRight, Menu } from 'lucide-react'
import { Logo } from './Brand.jsx'
import InboxBell from './classroom/InboxBell.jsx'
import { preloadRoute } from '../lib/preloadRoute.js'
import './studio-navigation.css'
import TeacherWorkspaceNav from './classroom/TeacherWorkspaceNav.jsx'
import './classroom/teacher-workspace.css'

const main = [
  ['/dashboard', 'My space', LayoutDashboard], ['/plan', 'My plan', CalendarCheck],
  ['/subject-test', 'Practice', Target], ['/pyq', 'PYQs & papers', BookOpen],
]
const groups = [
  { title: 'PRACTISE & PREPARE', items: [
    ['/subject-test', 'Subject practice', Target, 'Choose a chapter and focus'],
    ['/pyq', 'PYQs & shift papers', BookOpen, 'MHT-CET and BITSAT questions'],
    ['/test', 'JEE full mock', Shapes, 'Rehearse a complete paper'],
    ['/daily', 'Daily question', CalendarCheck, 'Make practice a habit'],
    ['/scenarios', 'Exam situations', Shapes, 'Work through exam pressure'],
    ['/image-questions', 'Diagram practice', BookOpen, 'Questions with visual concepts'],
  ] },
  { title: 'PLAN & DISCOVER', items: [
    ['/dashboard', 'My progress', LayoutDashboard, 'Results and your next session'],
    ['/plan', 'Study plan & college goals', Target, 'Practice priorities and college outlook'],
    ['/advanced', 'IIT & Advanced', GraduationCap, 'Explore IIT choices and cutoffs'],
    ['/syllabus', 'Syllabus', Library, 'See the subjects and chapters'],
    ['/buddy', 'Study assistant', MessageCircle, 'Talk through your preparation'],
    ['/pricing', 'Plans & pricing', Coins, 'Explore what is available'],
  ] },
  { title: 'LEARN TOGETHER', items: [
    ['/ranking', 'Rankings & contests', Trophy, 'Compete and track your rating'],
    ['/learning', 'Mistakes & revision', BookOpen, 'Review mistakes and ask your teacher'],
    ['/classes', 'My classroom', Users, 'Your classes and assignments'],
    ['/rewards', 'Rewards', Coins, 'Your practice milestones'],
    ['/profile', 'My profile', UserRound, 'Your details and public profile'],
    ['/account/security', 'Account security', UserRound, 'Password and Google sign-in'],
  ] },
]
function NavigationLink({ item, close, detail = false }) {
  const [to, label, Icon, description] = item
  return <NavLink to={to} onClick={close} className={({ isActive }) => `studio-link${isActive ? ' active' : ''}`}><Icon size={18} strokeWidth={1.6}/><span>{label}{detail && description && <small>{description}</small>}</span>{detail && <ChevronRight className="studio-link-arrow" size={13}/>}</NavLink>
}
function StudentHeader() {
  const { pathname, search } = useLocation()
  const { isAuthenticated, user, openLogin, logout } = useAuth()
  const [open, setOpen] = useState(false)
  const [query, setQuery] = useState('')
  const [teacher, setTeacher] = useState(false)
  const ref = useRef(null), trigger = useRef(null), searchInput = useRef(null)
  const close = () => setOpen(false)
  useEffect(() => { setOpen(false); setQuery('') }, [pathname, search])
  useEffect(() => {
    if (!isAuthenticated) return
    const shortcut = event => {
      if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === 'k') {
        event.preventDefault(); setOpen(value => !value)
      }
    }
    document.addEventListener('keydown', shortcut)
    return () => document.removeEventListener('keydown', shortcut)
  }, [isAuthenticated])
  useEffect(() => {
    if (!open) return
    searchInput.current?.focus({ preventScroll: true })
    const dismiss = event => { if (!ref.current?.contains(event.target)) close() }
    const escape = event => { if (event.key === 'Escape') { close(); trigger.current?.focus() } }
    document.addEventListener('pointerdown', dismiss); document.addEventListener('keydown', escape)
    return () => { document.removeEventListener('pointerdown', dismiss); document.removeEventListener('keydown', escape) }
  }, [open])
  const links = teacher ? [['/teacher', 'Teacher studio', GraduationCap], ...main.slice(1)] : main
  const activeIndex = links.findIndex(([path]) => pathname === path || pathname.startsWith(`${path}/`))
  const filtered = groups.map(group => ({ ...group, items: group.items.filter(item => `${item[1]} ${item[3]}`.toLowerCase().includes(query.toLowerCase().trim())) })).filter(group => group.items.length)

  return <div ref={ref} className={`studio-navigation${isAuthenticated ? ' is-member' : ''}`} onPointerOver={preloadRoute} onFocus={preloadRoute} onBlur={event => { if (event.relatedTarget && !event.currentTarget.contains(event.relatedTarget)) close() }}>
    <a className="skip-link" href="#studio-main">Skip to workspace</a>
    <header className="studio-topbar"><div className="studio-mobile-logo"><Logo to={isAuthenticated ? '/dashboard' : '/'}/></div>{isAuthenticated && <nav className={`studio-top-links${activeIndex >= 0 ? ' has-active' : ''}`} style={{ '--nav-index': Math.max(0, activeIndex) }} aria-label="Main navigation">{links.map(item => <NavigationLink key={item[0]} item={item} close={close}/>)}</nav>}<div className="studio-top-actions">{isAuthenticated ? <><button ref={trigger} className={`studio-more${open ? ' is-open' : ''}`} onClick={() => setOpen(value => !value)} aria-label={open ? 'Close explore menu' : 'Explore all features'} aria-expanded={open} aria-controls="studio-menu">{open ? <X size={17}/> : <Grid2X2 size={17}/>}<span>Explore</span><kbd title="Control or Command + K">K</kbd></button><InboxBell onTeacher={setTeacher}/><Link className="studio-avatar" to="/profile" aria-label="My profile">{user?.name?.trim()?.[0]?.toUpperCase() || <UserRound size={16}/>}</Link></> : <><Link className="studio-public-home" to="/">Explore Jee Edge<ArrowUpRight size={14}/></Link><button className="btn btn-primary btn-sm" onClick={() => openLogin()}>Log in</button></>}</div></header>
    {isAuthenticated && open && <div id="studio-menu" className="studio-menu"><div className="studio-search"><Search size={18}/><input ref={searchInput} type="search" value={query} onChange={event => setQuery(event.target.value)} placeholder="What would you like to work on?" aria-label="Search features"/><button onClick={() => { close(); trigger.current?.focus() }} aria-label="Close explore menu"><X size={17}/></button></div><nav className="studio-menu-groups" aria-label="All workspace features">{filtered.map(group => <div key={group.title}><h2>{group.title}</h2>{group.items.map(item => <NavigationLink key={item[0]} item={item} close={close} detail/>)}</div>)}{!filtered.length && <p className="studio-search-empty" role="status">No matches for “{query}”. Try “mock”, “college” or “class”.</p>}</nav><div className="studio-menu-footer"><span>One place for every part of your preparation.</span><button onClick={logout}><LogOut size={14}/>Sign out</button></div></div>}
    {isAuthenticated && <nav className="studio-dock" aria-label="Quick navigation">{links.map(item => <NavigationLink key={item[0]} item={item} close={close}/>)}<button className={`studio-link${open ? ' active' : ''}`} onClick={() => setOpen(value => !value)} aria-label="Explore all features" aria-expanded={open} aria-controls="studio-menu"><Grid2X2 size={19}/><span>Explore</span></button></nav>}
    <span id="studio-main" tabIndex={-1}/>
  </div>
}

function TeacherHeader() {
  const { logout, user } = useAuth()
  const { pathname, search } = useLocation()
  const [open, setOpen] = useState(false)
  const trigger = useRef(null), menu = useRef(null)
  useEffect(() => { setOpen(false) }, [pathname, search])
  useEffect(() => {
    if (!open) return
    menu.current?.querySelector('a')?.focus()
    const escape = event => { if (event.key === 'Escape') { setOpen(false); trigger.current?.focus() } }
    const outside = event => { if (!menu.current?.contains(event.target) && !trigger.current?.contains(event.target)) setOpen(false) }
    document.addEventListener('keydown', escape); document.addEventListener('pointerdown', outside)
    return () => { document.removeEventListener('keydown', escape); document.removeEventListener('pointerdown', outside) }
  }, [open])
  return <div className="studio-navigation teacher-navigation tw-header" onPointerOver={preloadRoute} onFocus={preloadRoute}>
    <a className="skip-link" href="#teacher-content">Skip to workspace</a>
    <header className="studio-topbar">
      <div className="tw-brand"><div className="studio-mobile-logo"><Logo to="/teacher"/></div><span className="tw-brand-label">For teachers</span></div>
      <TeacherWorkspaceNav compact/>
      <div className="studio-top-actions">
        <InboxBell/>
        <Link className="tw-account-link" to="/teacher/profile" aria-label="Your teacher profile"><span className="studio-avatar">{user?.name?.trim()?.[0]?.toUpperCase() || <UserRound size={16}/>}</span><span className="tw-account-name">{user?.name || 'Teacher'}<small>Teacher account</small></span></Link>
        <button className="btn btn-quiet btn-sm tw-sign-out" onClick={logout}>Sign out</button>
        <button ref={trigger} className="tw-menu-toggle" aria-expanded={open} aria-controls="teacher-mobile-menu" aria-label={open ? 'Close teacher navigation' : 'Open teacher navigation'} onClick={() => setOpen(v => !v)}>{open ? <X size={19}/> : <Menu size={19}/>}<span>More</span></button>
      </div>
    </header>
    {open && <div ref={menu} id="teacher-mobile-menu" className="tw-mobile-menu"><TeacherWorkspaceNav close={() => setOpen(false)}/><button className="btn btn-quiet" onClick={logout}><LogOut size={16}/>Sign out</button></div>}
    <span id="studio-main" tabIndex={-1}/>
  </div>
}
export default function AppHeader() {
  const { user } = useAuth()
  return user?.account_type === 'teacher' || user?.teacher ? <TeacherHeader/> : <StudentHeader/>
}
