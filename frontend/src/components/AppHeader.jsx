import { useEffect, useRef, useState } from 'react'
import { NavLink, useLocation } from 'react-router-dom'
import { useAuth0 } from '@auth0/auth0-react'
import { BookOpen, ChevronDown, Coins, Flame, Library, LogOut, Menu, MessageCircle, MonitorPlay, Timer, Trophy, UserRound, X } from 'lucide-react'
import { Logo } from './Brand.jsx'
import './app-header.css'

const PRACTICE = [
  { to: '/subject-test', title: 'Subject tests', hint: 'Practise a topic or subject', Icon: BookOpen },
  { to: '/scenarios', title: 'Exam situations', hint: 'Play the crucial 15–45 minutes', Icon: Timer },
  { to: '/daily', title: 'Daily question', hint: 'Keep your streak going', Icon: Flame },
  { to: '/test', title: 'Full mock', hint: 'Sit the complete paper', Icon: MonitorPlay },
  { to: '/image-questions', title: 'Diagram practice', hint: 'Try visual questions', Icon: BookOpen },
]
const EXPLORE = [
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
  const { isAuthenticated, loginWithRedirect, logout } = useAuth0()
  const ref = useRef(null)
  const [open, setOpen] = useState(null)
  const close = () => setOpen(null)
  const toggle = name => setOpen(current => current === name ? null : name)
  const signOut = () => logout({ logoutParams: { returnTo: window.location.origin } })

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
      <Logo to={isAuthenticated ? '/dashboard' : '/'} />
      {isAuthenticated && <nav className="jee-nav__desktop" aria-label="Main navigation">
        <NavLink to="/dashboard" end onClick={close} className={({ isActive }) => `jee-nav__top${isActive ? ' selected' : ''}`}>Overview</NavLink>
        {dropdown('practice', 'Practice', PRACTICE)}
        <NavLink to="/ranking" onClick={close} className={({ isActive }) => `jee-nav__top${isActive ? ' selected' : ''}`}>Rankings</NavLink>
        {dropdown('explore', 'Explore', EXPLORE)}
      </nav>}
      {isAuthenticated ? <div className="jee-nav__account">
        <button type="button" className="jee-nav__account-button" data-trigger="account" aria-label="Account menu"
          aria-expanded={open === 'account'} aria-controls="jee-nav-account" onClick={() => toggle('account')}>
          <UserRound size={18} aria-hidden="true" /><ChevronDown size={14} aria-hidden="true" /></button>
        {open === 'account' && <div className="jee-nav__panel jee-nav__account-panel" id="jee-nav-account" aria-label="Account pages">
          <MenuLink item={{ to: '/profile', title: 'Your profile', hint: 'Account and public profile', Icon: UserRound }} close={close} />
          <button type="button" className="jee-nav__item" onClick={signOut}><span className="jee-nav__item-icon"><LogOut size={18} /></span><strong>Log out</strong></button>
        </div>}
      </div> : <button type="button" className="btn btn-primary btn-sm jee-nav__login" onClick={() => loginWithRedirect()}>Log in</button>}
      {isAuthenticated && <button type="button" className="jee-nav__mobile-button" data-trigger="mobile"
        aria-label={open === 'mobile' ? 'Close navigation' : 'Open navigation'} aria-expanded={open === 'mobile'}
        aria-controls="jee-nav-mobile" onClick={() => toggle('mobile')}>
        {open === 'mobile' ? <X size={21} aria-hidden="true" /> : <Menu size={21} aria-hidden="true" />}<span>Menu</span>
      </button>}
    </div>
    {isAuthenticated && open === 'mobile' && <nav className="jee-nav__mobile" id="jee-nav-mobile" aria-label="Mobile navigation">
      <NavLink to="/dashboard" onClick={close} className={({ isActive }) => `jee-nav__mobile-overview${isActive ? ' selected' : ''}`}>Overview</NavLink>
      <span className="jee-nav__heading">Practice</span>
      {PRACTICE.map(item => <MenuLink key={item.to} item={item} close={close} compact />)}
      <span className="jee-nav__heading">Explore</span>
      <MenuLink item={{ to: '/ranking', title: 'Rankings', Icon: Trophy }} close={close} compact />
      {EXPLORE.map(item => <MenuLink key={item.to} item={item} close={close} compact />)}
      <span className="jee-nav__heading">Account</span>
      <MenuLink item={{ to: '/profile', title: 'Your profile', Icon: UserRound }} close={close} compact />
      <button type="button" className="jee-nav__item" onClick={signOut}><span className="jee-nav__item-icon"><LogOut size={18} aria-hidden="true" /></span><strong>Log out</strong></button>
    </nav>}
  </header>
}
