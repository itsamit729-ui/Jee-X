import { useEffect, useRef, useState } from 'react'
import { NavLink, useLocation } from 'react-router-dom'
import { useAuth } from '../auth/AuthContext.jsx'
import { BookOpen, ChevronDown, Coins, Flame, Library, LogOut, Menu, MessageCircle, MonitorPlay, Timer, Target, Trophy, UserRound, X } from 'lucide-react'
import { Logo } from './Brand.jsx'
import './app-header.css'
import InboxBell from './classroom/InboxBell.jsx'

const PRACTICE = [
  { to: '/subject-test', title: 'Topic practice', hint: 'Practise a topic or subject', Icon: BookOpen },
  { to: '/scenarios', title: 'Exam situations', hint: 'Play the crucial 15–45 minutes', Icon: Timer },
  { to: '/daily', title: 'Daily question', hint: 'Keep your streak going', Icon: Flame },
  { to: '/test', title: 'Full mock', hint: 'Sit the complete paper', Icon: MonitorPlay },
  { to: '/image-questions', title: 'Diagram practice', hint: 'Try visual questions', Icon: BookOpen },
]
const EXPLORE = [
  { to: '/advanced', title: 'IIT & JEE Advanced', hint: 'Advanced ranks, colleges and score references', Icon: Target },
  { to: '/teacher', title: 'Teacher studio', hint: 'Create classes and assign tests', Icon: BookOpen },
  { to: '/classes', title: 'Your classroom', hint: 'Tests from your teacher', Icon: BookOpen },
  { to: '/syllabus', title: 'Syllabus', hint: 'Track what to study', Icon: Library },
  { to: '/buddy', title: 'Study assistant', hint: 'Work through a doubt', Icon: MessageCircle },
  { to: '/rewards', title: 'Rewards', hint: 'See your progress', Icon: Coins },
]
const matchPath = (pathname, href) => pathname === href || pathname.startsWith(`${href}/`)

function MenuLink({ item, close, compact = false }) {
  const { to, title, hint, Icon } = item
  return <NavLink to={to} onClick={close} className={({ isActive }) => `jee-nav__item${isActive ? ' selected' : ''}`}>
    <span className="jee-nav__item-icon"><Icon size={18} strokeWidth={1.8} aria-hidden="true" /></span>
    <span><strong>{title}</strong>{!compact && <small>{hint}</small>}</span>
  </NavLink>
}

export default function AppHeader() {
  const { pathname } = useLocation()
  const { isAuthenticated, openLogin, logout } = useAuth()
  const ref = useRef(null)
  const [teacher, setTeacher] = useState(false)
  const [open, setOpen] = useState(null)
  const close = () => setOpen(null)
  const toggle = name => setOpen(current => current === name ? null : name)
  const signOut = () => logout()

  useEffect(close, [pathname])
  useEffect(() => {
    if (!open) return undefined
    const outside = event => { if (!ref.current?.contains(event.target)) close() }
    const escape = event => {
      if (event.key === 'Escape') {
        close()
        ref.current?.querySelector(`[data-trigger="${open}"]`)?.focus()
      }
    }
    document.addEventListener('pointerdown', outside)
    document.addEventListener('keydown', escape)
    return () => { document.removeEventListener('pointerdown', outside); document.removeEventListener('keydown', escape) }
  }, [open])

  const dropdown = (name, title, items) => <div className="jee-nav__group">
    <button type="button" data-trigger={name} aria-expanded={open === name} aria-controls={`jee-nav-${name}`}
      className={`jee-nav__top${items.some(item => matchPath(pathname, item.to)) ? ' selected' : ''}`}
      onClick={() => toggle(name)}>{title}<ChevronDown size={14} className={open === name ? 'rotated' : ''} aria-hidden="true" /></button>
    {open === name && <div className="jee-nav__panel" id={`jee-nav-${name}`} aria-label={`${title} pages`}>
      {items.map(item => <MenuLink key={item.to} item={item} close={close} />)}
    </div>}
  </div>

  return <header className="jee-nav" ref={ref}>
    <div className="jee-nav__bar">
      <Logo to={isAuthenticated ? teacher ? '/teacher' : '/dashboard' : '/'} />
      {isAuthenticated && <nav className="jee-nav__desktop" aria-label="Main navigation">
        <NavLink to={teacher ? '/teacher' : '/dashboard'} end onClick={close} className={({ isActive }) => `jee-nav__top${isActive ? ' selected' : ''}`}>{teacher ? 'Teacher studio' : 'Overview'}</NavLink>
        <NavLink to="/plan" onClick={close} className={({ isActive }) => `jee-nav__top jee-nav__recommend${isActive ? ' selected' : ''}`}><Target size={15} aria-hidden="true"/>My JEE Plan</NavLink>
        {dropdown('practice', 'Practice', PRACTICE)}
        <NavLink to="/ranking" onClick={close} className={({ isActive }) => `jee-nav__top${isActive ? ' selected' : ''}`}>Rankings</NavLink>
        {dropdown('explore', 'Explore', EXPLORE)}
      </nav>}
      {isAuthenticated && <InboxBell onTeacher={setTeacher}/>}
      {isAuthenticated ? <div className="jee-nav__account">
        <button type="button" className="jee-nav__account-button" data-trigger="account" aria-label="Account menu"
          aria-expanded={open === 'account'} aria-controls="jee-nav-account" onClick={() => toggle('account')}>
          <UserRound size={18} aria-hidden="true" /><ChevronDown size={14} aria-hidden="true" /></button>
        {open === 'account' && <div className="jee-nav__panel jee-nav__account-panel" id="jee-nav-account" aria-label="Account pages">
          {teacher && <MenuLink item={{ to: '/teacher', title: 'Teacher studio', hint: 'Classes, tests and insights', Icon: BookOpen }} close={close} />}
          <MenuLink item={{ to: '/profile', title: 'Your profile', hint: 'Account and public profile', Icon: UserRound }} close={close} />
          <button type="button" className="jee-nav__item" onClick={signOut}><span className="jee-nav__item-icon"><LogOut size={18} /></span><strong>Log out</strong></button>
        </div>}
      </div> : <button type="button" className="btn btn-primary btn-sm jee-nav__login" onClick={() => openLogin()}>Log in</button>}
      {isAuthenticated && <NavLink to="/plan" aria-label="My JEE Plan" onClick={close} className={({isActive}) => `jee-nav__quick-recommend${isActive ? ' selected' : ''}`}><Target size={16} aria-hidden="true"/>My plan</NavLink>}
      {isAuthenticated && <button type="button" className="jee-nav__mobile-button" data-trigger="mobile"
        aria-label={open === 'mobile' ? 'Close navigation' : 'Open navigation'} aria-expanded={open === 'mobile'}
        aria-controls="jee-nav-mobile" onClick={() => toggle('mobile')}>
        {open === 'mobile' ? <X size={21} aria-hidden="true" /> : <Menu size={21} aria-hidden="true" />}<span>Menu</span>
      </button>}
    </div>
    {isAuthenticated && open === 'mobile' && <nav className="jee-nav__mobile" id="jee-nav-mobile" aria-label="Mobile navigation">
      <NavLink to={teacher ? '/teacher' : '/dashboard'} onClick={close} className={({ isActive }) => `jee-nav__mobile-overview${isActive ? ' selected' : ''}`}>{teacher ? 'Teacher studio' : 'Overview'}</NavLink>
      <MenuLink item={{ to: '/plan', title: 'My JEE Plan', hint: 'Your path, topics and next practice', Icon: Target }} close={close} />
      <span className="jee-nav__heading">Practice</span>
      {PRACTICE.map(item => <MenuLink key={item.to} item={item} close={close} compact />)}
      <span className="jee-nav__heading">Explore</span>
      <MenuLink item={{ to: '/ranking', title: 'Rankings', Icon: Trophy }} close={close} compact />
      {EXPLORE.map(item => <MenuLink key={item.to} item={item} close={close} compact />)}
      <span className="jee-nav__heading">Account</span>
      {teacher && <MenuLink item={{ to: '/teacher', title: 'Teacher studio', hint: 'Classes, tests and insights', Icon: BookOpen }} close={close} />}
          <MenuLink item={{ to: '/profile', title: 'Your profile', Icon: UserRound }} close={close} compact />
      <button type="button" className="jee-nav__item" onClick={signOut}><span className="jee-nav__item-icon"><LogOut size={18} aria-hidden="true" /></span><strong>Log out</strong></button>
    </nav>}
  </header>
}

